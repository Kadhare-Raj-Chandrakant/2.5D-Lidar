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
        """Create dense reference path from waypoints."""
        if len(waypoints) < 2:
            return np.array([[vehicle_state.x, vehicle_state.y, vehicle_state.yaw]])

        xs = [wp.x for wp in waypoints]
        ys = [wp.y for wp in waypoints]
        yaws = [wp.yaw for wp in waypoints]
        ss = [wp.s for wp in waypoints]

        s_dense = np.linspace(ss[0], ss[-1], max(100, int((ss[-1] - ss[0]) / 0.5)))

        from scipy.interpolate import interp1d
        fx = interp1d(ss, xs, kind='linear', fill_value='extrapolate')
        fy = interp1d(ss, ys, kind='linear', fill_value='extrapolate')
        fyaw = interp1d(ss, yaws, kind='linear', fill_value='extrapolate')

        return np.column_stack([fx(s_dense), fy(s_dense), fyaw(s_dense)])

    def _cartesian_to_frenet(self, vehicle_state: VehicleState,
                             ref_path: np.ndarray) -> np.ndarray:
        """Convert vehicle state to Frenet coordinates."""
        min_dist = float('inf')
        nearest_idx = 0
        for i, pt in enumerate(ref_path):
            dist = (pt[0] - vehicle_state.x)**2 + (pt[1] - vehicle_state.y)**2
            if dist < min_dist:
                min_dist = dist
                nearest_idx = i

        if nearest_idx == 0:
            s = 0
        elif nearest_idx >= len(ref_path) - 1:
            s = np.sum(np.sqrt(np.diff(ref_path[:nearest_idx, 0])**2 +
                            np.diff(ref_path[:nearest_idx, 1])**2))
        else:
            s = np.sum(np.sqrt(np.diff(ref_path[:nearest_idx, 0])**2 +
                            np.diff(ref_path[:nearest_idx, 1])**2))

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
            # Snap to nearest valid lane center
            target_d = round(current_d / lane_width) * lane_width

        return float(target_d)

    def _generate_candidate_trajectories(self, frenet_state: np.ndarray,
                                         target_d: float, target_s: float,
                                         behavior: BehaviorDecision) -> List[dict]:
        """Generate candidate trajectories in Frenet frame."""
        candidates = []
        s0, d0, v0, _ = frenet_state

        for i in range(self.num_paths):
            d_target = target_d + (i - self.num_paths // 2) * 1.0

            T = self.horizon / max(v0, 1.0)
            T = max(T, 2.0)

            coeffs_d = self._quartic_poly(d0, 0, 0, d_target, 0, 0, T)
            coeffs_s = self._quartic_poly(s0, v0, 0, target_s, behavior.target_speed, 0, T)

            traj = {'coeffs_s': coeffs_s, 'coeffs_d': coeffs_d, 'T': T}
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
        best_cost = float('inf')
        best_traj = candidates[0] if candidates else None

        for traj in candidates:
            cost = self._compute_trajectory_cost(traj, perception, ref_path)
            if cost < best_cost:
                best_cost = cost
                best_traj = traj

        return best_traj

    def _compute_trajectory_cost(self, traj: dict, perception: PerceptionResult,
                                 ref_path: np.ndarray) -> float:
        """Compute trajectory cost."""
        coeffs_s, coeffs_d, T = traj['coeffs_s'], traj['coeffs_d'], traj['T']

        cost = 0
        num_samples = 20
        for i in range(num_samples):
            t = i * T / num_samples

            s = np.polyval(coeffs_s[::-1], t)
            d = np.polyval(coeffs_d[::-1], t)
            v = np.polyval(np.polyder(coeffs_s[::-1]), t)
            a = np.polyval(np.polyder(coeffs_s[::-1], 2), t)
            jerk = np.polyval(np.polyder(coeffs_s[::-1], 3), t)

            d_prime = np.polyval(np.polyder(coeffs_d[::-1]), t)
            d_double_prime = np.polyval(np.polyder(coeffs_d[::-1], 2), t)
            curvature = abs(d_double_prime) / (1 + d_prime**2)**1.5

            cost += self.weights['jerk'] * jerk**2
            cost += self.weights['curvature'] * curvature**2
            cost += self.weights['deviation'] * d**2

            for obj in perception.objects:
                if obj.bbox_3d:
                    obj_s, obj_d = self._cartesian_to_frenet_obj(obj.bbox_3d, ref_path)
                    dist_s = abs(obj_s - s)
                    dist_d = abs(obj_d - d)
                    if dist_s < 10 and dist_d < 5:
                        cost += self.weights['collision'] / (dist_s + dist_d + 0.1)

        return cost

    def _cartesian_to_frenet_obj(self, bbox, ref_path):
        """Convert object bbox to Frenet (simplified)."""
        min_dist = float('inf')
        nearest_idx = 0
        for i, pt in enumerate(ref_path):
            dist = (pt[0] - bbox.x)**2 + (pt[1] - bbox.y)**2
            if dist < min_dist:
                min_dist = dist
                nearest_idx = i

        s = np.sum(np.sqrt(np.diff(ref_path[:nearest_idx+1, 0])**2 +
                        np.diff(ref_path[:nearest_idx+1, 1])**2))
        ref_yaw = ref_path[nearest_idx, 2]
        dx = bbox.x - ref_path[nearest_idx, 0]
        dy = bbox.y - ref_path[nearest_idx, 1]
        d = -np.sin(ref_yaw) * dx + np.cos(ref_yaw) * dy
        return s, d

    def _frenet_to_cartesian(self, traj: dict, ref_path: np.ndarray,
                             timestamp: float) -> Trajectory:
        """Convert Frenet trajectory to Cartesian waypoints."""
        coeffs_s, coeffs_d, T = traj['coeffs_s'], traj['coeffs_d'], traj['T']

        trajectory = Trajectory(timestamp=timestamp)
        num_points = 50

        for i in range(num_points):
            t = i * T / num_points
            s = np.polyval(coeffs_s[::-1], t)
            d = np.polyval(coeffs_d[::-1], t)

            idx = min(int(s / 0.5), len(ref_path) - 2)
            if idx < 0:
                idx = 0

            ref_x, ref_y, ref_yaw = ref_path[idx]
            x = ref_x - np.sin(ref_yaw) * d
            y = ref_y + np.cos(ref_yaw) * d

            v = np.polyval(np.polyder(coeffs_s[::-1]), t)
            yaw = ref_yaw + np.arctan2(
                np.polyval(np.polyder(coeffs_d[::-1]), t), 1
            )

            trajectory.waypoints.append(Waypoint(
                x=x, y=y, yaw=yaw, speed=max(0, v), s=s
            ))

        trajectory.valid = True
        return trajectory