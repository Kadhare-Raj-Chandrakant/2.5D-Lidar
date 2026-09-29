"""Local trajectory planner using Frenet frame and polynomial optimization."""
import numpy as np
from typing import List, Optional
from ..types import Waypoint, Trajectory, VehicleState, PerceptionResult, DetectedObject, BehaviorDecision
from ..utils.config import config


class LocalPlanner:
    """Local trajectory planner in Frenet frame."""

    def __init__(self):
        self.horizon = config.get('planning.local.horizon', 50.0)
        self.dt = config.get('planning.local.dt', 0.5)
        self.num_paths = config.get('planning.local.num_paths', 7)
        self.weights = config.get('planning.local.weights', {
            'jerk': 1.0, 'curvature': 10.0, 'deviation': 50.0, 'collision': 1000.0
        })

    def plan(self, vehicle_state: VehicleState,
             global_waypoints: List[Waypoint],
             perception: PerceptionResult,
             behavior: BehaviorDecision) -> Trajectory:
        """Plan local trajectory."""
        if not global_waypoints:
            return Trajectory(valid=False)

        ref_path = self._create_reference_path(global_waypoints, vehicle_state)
        if len(ref_path) < 2:
            return Trajectory(valid=False)

        frenet_state = self._cartesian_to_frenet(vehicle_state, ref_path)

        target_d = self._get_target_lateral_offset(behavior, frenet_state)
        target_s = frenet_state[0] + self.horizon

        candidates = self._generate_candidate_trajectories(
            frenet_state, target_d, target_s, behavior
        )

        best_traj = self._select_best_trajectory(candidates, perception, ref_path)

        return self._frenet_to_cartesian(best_traj, ref_path, vehicle_state.timestamp)

    def _create_reference_path(self, waypoints: List[Waypoint],
                               vehicle_state: VehicleState) -> np.ndarray:
        """Create dense reference path from waypoints for local horizon."""
        if len(waypoints) < 2:
            return np.array([[vehicle_state.x, vehicle_state.y, vehicle_state.yaw, 0.0]])

        # Local horizon window to avoid interpolating thousands of distant waypoints
        min_s = vehicle_state.x - 25.0
        max_s = vehicle_state.x + self.horizon + 35.0
        local_wps = [wp for wp in waypoints if min_s <= wp.s <= max_s]
        if len(local_wps) < 2:
            local_wps = waypoints[:40]

        xs = [wp.x for wp in local_wps]
        ys = [wp.y for wp in local_wps]
        yaws = [wp.yaw for wp in local_wps]
        ss = [wp.s for wp in local_wps]

        num_pts = max(30, int((ss[-1] - ss[0]) / 0.5))
        s_dense = np.linspace(ss[0], ss[-1], num_pts)

        from scipy.interpolate import interp1d
        fx = interp1d(ss, xs, kind='linear', fill_value='extrapolate')
        fy = interp1d(ss, ys, kind='linear', fill_value='extrapolate')
        fyaw = interp1d(ss, yaws, kind='linear', fill_value='extrapolate')

        return np.column_stack([fx(s_dense), fy(s_dense), fyaw(s_dense), s_dense])

    def _cartesian_to_frenet(self, vehicle_state: VehicleState,
                             ref_path: np.ndarray) -> np.ndarray:
        """Convert vehicle state to Frenet coordinates."""
        dists = (ref_path[:, 0] - vehicle_state.x)**2 + (ref_path[:, 1] - vehicle_state.y)**2
        nearest_idx = int(np.argmin(dists))

        s = float(ref_path[nearest_idx, 3]) if ref_path.shape[1] > 3 else nearest_idx * 0.5
        ref_yaw = ref_path[nearest_idx, 2]
        dx = vehicle_state.x - ref_path[nearest_idx, 0]
        dy = vehicle_state.y - ref_path[nearest_idx, 1]
        d = -np.sin(ref_yaw) * dx + np.cos(ref_yaw) * dy

        return np.array([s, d, vehicle_state.speed, 0])

    def _get_target_lateral_offset(self, behavior: BehaviorDecision,
                                   frenet_state: np.ndarray) -> float:
        """Get target lateral offset based on behavior."""
        lane_width = 3.5
        current_d = frenet_state[1]

        if behavior.state.name == "LANE_CHANGE_LEFT":
            target_d = -lane_width
        elif behavior.state.name == "LANE_CHANGE_RIGHT":
            target_d = 0.0
        else:
            # Snap to cruising lane (0.0) or passing lane (-3.5)
            if current_d < -1.75:
                target_d = -lane_width
            else:
                target_d = 0.0

        return float(target_d)

    def _generate_candidate_trajectories(self, frenet_state: np.ndarray,
                                         target_d: float, target_s: float,
                                         behavior: BehaviorDecision) -> List[dict]:
        """Generate candidate trajectories in Frenet frame."""
        candidates = []
        s0, d0, v0, _ = frenet_state

        effective_target_speed = max(behavior.target_speed, 15.0) if behavior.state.name != "EMERGENCY_STOP" else 0.0

        is_changing_lane = behavior.state.name in ["LANE_CHANGE_LEFT", "LANE_CHANGE_RIGHT"]
        T_long = max(2.0, min(self.horizon / max(v0, 6.0), 6.0))
        T_lat = 2.0 if is_changing_lane else T_long

        for i in range(self.num_paths):
            d_target = target_d + (i - self.num_paths // 2) * 0.35

            coeffs_d = self._quartic_poly(d0, 0, 0, d_target, 0, 0, T_lat)
            coeffs_s = self._quartic_poly(s0, v0, 0, target_s, effective_target_speed, 0, T_long)

            traj = {
                'coeffs_s': coeffs_s, 'coeffs_d': coeffs_d,
                'd0': d0,
                'T': T_long, 'T_lat': T_lat,
                'target_d': d_target, 'target_d_goal': target_d
            }
            candidates.append(traj)

        return candidates

    def _quartic_poly(self, x0, v0, a0, x1, v1, a1, T):
        """Solve for quartic polynomial coefficients."""
        A = np.array([
            [1, 0, 0, 0, 0],
            [0, 1, 0, 0, 0],
            [0, 0, 2, 0, 0],
            [1, T, T**2, T**3, T**4],
            [0, 1, 2*T, 3*T**2, 4*T**3]
        ])
        b = np.array([x0, v0, a0, x1, v1])
        return np.linalg.solve(A, b)

    def _select_best_trajectory(self, candidates: List[dict],
                                perception: PerceptionResult,
                                ref_path: np.ndarray) -> dict:
        """Select best trajectory based on cost function."""
        if not candidates:
            return None

        # Precompute Frenet coordinates of detected objects ONCE per frame
        frenet_objs = []
        for obj in perception.objects:
            if obj.bbox_3d:
                dists = (ref_path[:, 0] - obj.bbox_3d.x)**2 + (ref_path[:, 1] - obj.bbox_3d.y)**2
                nearest_idx = int(np.argmin(dists))
                obj_s = float(ref_path[nearest_idx, 3]) if ref_path.shape[1] > 3 else nearest_idx * 0.5
                ref_yaw = ref_path[nearest_idx, 2]
                dx = obj.bbox_3d.x - ref_path[nearest_idx, 0]
                dy = obj.bbox_3d.y - ref_path[nearest_idx, 1]
                obj_d = -np.sin(ref_yaw) * dx + np.cos(ref_yaw) * dy
                frenet_objs.append((obj_s, obj_d))

        best_cost = float('inf')
        best_traj = candidates[0]

        for traj in candidates:
            cost = self._compute_trajectory_cost(traj, frenet_objs)
            if cost < best_cost:
                best_cost = cost
                best_traj = traj

        return best_traj

    def _compute_trajectory_cost(self, traj: dict, frenet_objs: List) -> float:
        """Compute trajectory cost in Frenet frame."""
        coeffs_s = traj['coeffs_s']
        d0 = traj.get('d0', 0.0)
        T = traj['T']
        target_d = traj['target_d']
        target_d_goal = traj['target_d_goal']

        num_samples = 15
        t_samples = np.linspace(0, T, num_samples)

        s_vals = np.polyval(coeffs_s[::-1], t_samples)
        v_vals = np.polyval(np.polyder(coeffs_s[::-1]), t_samples)
        s0 = s_vals[0]
        L_lat = max(24.0, min(35.0, 1.3 * max(v_vals[0], 5.0)))

        d_vals = []
        for s in s_vals:
            progress = np.clip((s - s0) / L_lat, 0.0, 1.0)
            smooth_p = progress * progress * (3.0 - 2.0 * progress)
            d_vals.append(d0 + (target_d - d0) * smooth_p)
        d_vals = np.array(d_vals)

        s_jerk = np.polyder(coeffs_s[::-1], 3)
        jerk = np.polyval(s_jerk, t_samples)

        cost = 0.0
        # Penalize deviation of candidate target offset from behavior goal
        cost += 350.0 * float((target_d - target_d_goal)**2)
        cost += self.weights['jerk'] * float(np.sum(jerk**2)) * 0.01

        if frenet_objs:
            for obj_s, obj_d in frenet_objs:
                for s, d in zip(s_vals, d_vals):
                    dist_s = abs(obj_s - s)
                    dist_d = abs(obj_d - d)
                    if dist_s < 14.0 and dist_d < 2.5:
                        cost += self.weights['collision'] / (dist_s + dist_d + 0.1)

        return float(cost)

    def _frenet_to_cartesian(self, traj: dict, ref_path: np.ndarray,
                             timestamp: float) -> Trajectory:
        """Convert Frenet trajectory to Cartesian waypoints."""
        coeffs_s = traj['coeffs_s']
        d0 = traj.get('d0', 0.0)
        T = traj['T']
        target_d = traj['target_d']

        trajectory = Trajectory(timestamp=timestamp)
        num_points = 30
        t_samples = np.linspace(0, T, num_points)

        s_vals = np.polyval(coeffs_s[::-1], t_samples)
        v_vals = np.polyval(np.polyder(coeffs_s[::-1]), t_samples)
        s0 = s_vals[0]
        L_lat = max(24.0, min(35.0, 1.3 * max(v_vals[0], 5.0)))

        d_vals = []
        d_prime_vals = []
        for s, v in zip(s_vals, v_vals):
            progress = np.clip((s - s0) / L_lat, 0.0, 1.0)
            smooth_p = progress * progress * (3.0 - 2.0 * progress)
            d = d0 + (target_d - d0) * smooth_p
            d_ds = (target_d - d0) * 6.0 * progress * (1.0 - progress) / L_lat
            d_prime = d_ds * v
            d_vals.append(float(d))
            d_prime_vals.append(float(d_prime))

        s_coords = ref_path[:, 3] if ref_path.shape[1] > 3 else ref_path[:, 0]

        for s, d, v, d_prime in zip(s_vals, d_vals, v_vals, d_prime_vals):
            dists = np.abs(s_coords - s)
            idx = int(np.argmin(dists))

            ref_x, ref_y, ref_yaw = ref_path[idx, :3]
            x = ref_x - np.sin(ref_yaw) * d
            y = ref_y + np.cos(ref_yaw) * d
            yaw = ref_yaw + np.arctan2(d_prime, max(v, 1.0))

            trajectory.waypoints.append(Waypoint(
                x=float(x), y=float(y), yaw=float(yaw), speed=float(max(0.0, v)), s=float(s)
            ))

        trajectory.valid = True
        return trajectory