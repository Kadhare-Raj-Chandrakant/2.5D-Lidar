"""High-level behavior planner (FSM) with complete overtaking and pedestrian/signal safety."""
import numpy as np
from typing import List, Optional, Tuple
from ..types import VehicleState, PerceptionResult, BehaviorDecision, BehaviorState, DetectedObject, Trajectory
from ..utils.config import config


class BehaviorPlanner:
    """Finite state machine for high-level driving behavior, overtaking, and traffic signal obedience."""

    def __init__(self):
        self.state = BehaviorState.LANE_FOLLOW
        self.target_lane = 0  # 0: cruising lane (y=1.75), -1: passing lane (y=-1.75)
        self.lane_change_timer = 0.0
        self.lane_change_duration = config.get('planning.behavior.lane_change_time', 2.8)
        self.min_gap = config.get('planning.behavior.min_gap', 3.0)
        self.follow_distance = config.get('planning.behavior.follow_distance', 2.0)
        self.emergency_brake_dist = config.get('planning.behavior.emergency_brake_dist', 6.0)
        self.cruising_speed = 14.5  # m/s (~52 km/h) realistic autonomous cruising speed
        self.overtaking_target_id: Optional[int] = None
        self.dt = config.get('simulation.dt', 0.033)

    def plan(self, vehicle_state: VehicleState,
             perception: PerceptionResult,
             global_trajectory: Trajectory) -> BehaviorDecision:
        """Run behavior planning FSM."""
        self._update_state(vehicle_state, perception)

        decision = BehaviorDecision(state=self.state)
        decision.target_lane = self.target_lane
        decision.target_speed = self._compute_target_speed(vehicle_state, perception)
        decision.stop_distance = self._compute_stop_distance(perception)
        decision.reason = self._get_reason(vehicle_state, perception)

        return decision

    def _update_state(self, vehicle_state: VehicleState, perception: PerceptionResult):
        """Update FSM state based on perception, signals, and overtaking lifecycle."""
        front_vehicle = self._get_front_vehicle(perception, vehicle_state)
        emergency = self._check_emergency(front_vehicle, vehicle_state)

        # 1. Emergency stop check
        ped_in_path = self._check_pedestrian_in_path(perception, vehicle_state)
        if ped_in_path and ped_in_path[0] < self.emergency_brake_dist + 2.0:
            emergency = True

        if emergency:
            self.state = BehaviorState.EMERGENCY_STOP
            return

        if self.state == BehaviorState.EMERGENCY_STOP:
            if not emergency:
                self.state = BehaviorState.LANE_FOLLOW
            return

        # 2. Traffic Signal & Crosswalk Stop obedience
        traffic_signal = perception.sensor_data.get('traffic_signal', 'green')
        active_station = perception.sensor_data.get('active_signal_station', 55.0)
        dist_to_signal = active_station - vehicle_state.x
        is_signal_stop = traffic_signal in ['red', 'yellow'] and (0.0 < dist_to_signal < 50.0)

        if is_signal_stop or (ped_in_path and ped_in_path[0] < 30.0):
            self.state = BehaviorState.STOP
            return

        if self.state == BehaviorState.STOP:
            if not is_signal_stop and (not ped_in_path or ped_in_path[0] >= 30.0):
                self.state = BehaviorState.LANE_FOLLOW
            else:
                return

        # 3. Standard Lane Following & Overtaking
        if self.state == BehaviorState.LANE_FOLLOW:
            # Case A: We are in passing lane (y < 0.0) -> check if ready to merge back into cruising lane (y = 1.75)
            if vehicle_state.y < 0.0:
                # Merge back right if cruising lane has safe clearance
                if self._can_change_right(perception, vehicle_state):
                    self.state = BehaviorState.LANE_CHANGE_RIGHT
                    self.target_lane = 0
                    self.lane_change_timer = 0.0
                    self.overtaking_target_id = None
                    return

            # Case B: We are in cruising lane (y >= 0.0) -> check if we should overtake slower vehicle ahead
            else:
                if front_vehicle and self._should_change_lane(front_vehicle, vehicle_state):
                    if self._can_change_left(perception, vehicle_state):
                        self.state = BehaviorState.LANE_CHANGE_LEFT
                        self.target_lane = -1
                        self.overtaking_target_id = front_vehicle.id
                        self.lane_change_timer = 0.0

        # 4. Lane Change Maneuvers in progress
        elif self.state in [BehaviorState.LANE_CHANGE_LEFT, BehaviorState.LANE_CHANGE_RIGHT]:
            self.lane_change_timer += self.dt
            if self.lane_change_timer >= self.lane_change_duration:
                self.state = BehaviorState.LANE_FOLLOW

    def _check_pedestrian_in_path(self, perception: PerceptionResult,
                                  vehicle_state: VehicleState) -> Optional[Tuple[float, DetectedObject]]:
        """Check if any crossing pedestrian is directly in front of vehicle path."""
        for obj in perception.objects:
            if not obj.bbox_3d:
                continue
            cls_name = getattr(obj.bbox_3d, 'class_name', '')
            if cls_name in ['pedestrian', 'person']:
                rel_x = obj.bbox_3d.x - vehicle_state.x
                rel_y = obj.bbox_3d.y - vehicle_state.y
                yaw = vehicle_state.yaw
                local_x = np.cos(yaw) * rel_x + np.sin(yaw) * rel_y
                local_y = -np.sin(yaw) * rel_x + np.cos(yaw) * rel_y

                # Within 35m ahead and inside roadway lateral bounds (within 3.0m of vehicle center)
                if 0.0 < local_x < 35.0 and abs(local_y) < 3.0:
                    return (local_x, obj)
        return None

    def _get_front_vehicle(self, perception: PerceptionResult,
                           vehicle_state: VehicleState) -> Optional[DetectedObject]:
        """Find closest vehicle ahead in our active target lane corridor."""
        front_vehicles = []
        target_y = -1.75 if (self.state == BehaviorState.LANE_CHANGE_LEFT or vehicle_state.y < 0.0) else 1.75

        for obj in perception.objects:
            if not obj.bbox_3d:
                continue
            cls_name = getattr(obj.bbox_3d, 'class_name', '')
            if cls_name in ['pedestrian', 'person']:
                continue

            rel_x = obj.bbox_3d.x - vehicle_state.x
            # Ahead along road within 55m and in our road lane corridor (within 1.5m of target lane center)
            if 0.0 < rel_x < 55.0 and abs(obj.bbox_3d.y - target_y) < 1.5:
                front_vehicles.append((rel_x, obj))

        if front_vehicles:
            return min(front_vehicles, key=lambda x: x[0])[1]
        return None

    def _check_emergency(self, front_vehicle: Optional[DetectedObject],
                         vehicle_state: VehicleState) -> bool:
        """Check if emergency braking is needed with lead vehicle in our lane."""
        if not front_vehicle or not front_vehicle.bbox_3d:
            return False

        target_y = -1.75 if (self.state == BehaviorState.LANE_CHANGE_LEFT or vehicle_state.y < 0.0) else 1.75
        if abs(front_vehicle.bbox_3d.y - target_y) > 1.5:
            return False

        rel_x = front_vehicle.bbox_3d.x - vehicle_state.x

        # Hysteresis: trigger emergency at < 5.0m, release only when > 8.0m
        if self.state == BehaviorState.EMERGENCY_STOP:
            return 0.0 < rel_x < 8.0
        else:
            return 0.0 < rel_x < 5.0

    def _should_change_lane(self, front_vehicle: DetectedObject,
                            vehicle_state: VehicleState) -> bool:
        """Determine if lane change is needed based on lead vehicle speed and distance."""
        if not front_vehicle or not front_vehicle.bbox_3d:
            return False

        rel_x = front_vehicle.bbox_3d.x - vehicle_state.x
        lead_speed = 8.0
        if front_vehicle.bbox_3d.velocity:
            lead_speed = front_vehicle.bbox_3d.velocity[0]

        return 0.0 < rel_x < 45.0 and lead_speed < self.cruising_speed * 0.90

    def _can_change_left(self, perception: PerceptionResult,
                         vehicle_state: VehicleState) -> bool:
        """Check if left passing lane (y = -1.75) is clear of traffic."""
        for obj in perception.objects:
            if not obj.bbox_3d:
                continue
            # Object in passing lane corridor (-3.2 < y < -0.3)
            if -3.2 < obj.bbox_3d.y < -0.3:
                rel_x = obj.bbox_3d.x - vehicle_state.x
                # Reject if vehicle is alongside or near (-12m to +25m)
                if -12.0 < rel_x < 25.0:
                    return False
        return True

    def _can_change_right(self, perception: PerceptionResult,
                          vehicle_state: VehicleState) -> bool:
        """Check if right cruising lane (y = 1.75) is clear of traffic."""
        for obj in perception.objects:
            if not obj.bbox_3d:
                continue
            # Object in cruising lane corridor (0.3 < y < 3.2)
            if 0.3 < obj.bbox_3d.y < 3.2:
                rel_x = obj.bbox_3d.x - vehicle_state.x
                # Reject if vehicle is alongside or ahead (-14m to +35m)
                if -14.0 < rel_x < 35.0:
                    return False
        return True

    def _compute_target_speed(self, vehicle_state: VehicleState,
                              perception: PerceptionResult) -> float:
        """Compute target speed based on traffic, signals, and ACC following law."""
        cruising_speed = self.cruising_speed

        # 1. Stop for traffic signal or pedestrian
        if self.state == BehaviorState.STOP:
            active_station = perception.sensor_data.get('active_signal_station', 55.0)
            stop_target = active_station - 9.0
            dist_to_stop = stop_target - vehicle_state.x

            if dist_to_stop > 0.4:
                return float(min(cruising_speed, max(0.0, np.sqrt(2 * 2.2 * dist_to_stop))))
            return 0.0

        # 2. While actively changing lane or overtaking -> maintain steady cruise speed
        if self.state in [BehaviorState.LANE_CHANGE_LEFT, BehaviorState.LANE_CHANGE_RIGHT]:
            return cruising_speed

        front_vehicle = self._get_front_vehicle(perception, vehicle_state)
        if not front_vehicle or not front_vehicle.bbox_3d:
            return cruising_speed

        rel_x = front_vehicle.bbox_3d.x - vehicle_state.x
        rel_y = front_vehicle.bbox_3d.y - vehicle_state.y
        yaw = vehicle_state.yaw
        local_x = np.cos(yaw) * rel_x + np.sin(yaw) * rel_y

        # Lead vehicle speed tracking (Adaptive Cruise Control)
        lead_speed = 8.0
        if front_vehicle.bbox_3d.velocity and abs(front_vehicle.bbox_3d.velocity[0]) > 0.5:
            lead_speed = max(0.0, float(front_vehicle.bbox_3d.velocity[0]))

        # Dynamic desired following distance: d_desired = d_min + T_gap * v_ego
        d_min = 10.0  # Standstill buffer (meters)
        t_gap = 1.6   # Time headway (seconds)
        d_desired = d_min + t_gap * max(vehicle_state.speed, 0.0)

        if local_x >= d_desired + 12.0:
            return cruising_speed

        # Linear ACC speed regulation based on distance error
        dist_error = local_x - d_desired
        k_acc = 0.5
        acc_speed = lead_speed + k_acc * dist_error

        # Decelerate smoothly towards 0 if closing inside d_min buffer
        if local_x < d_min:
            fraction = max(0.0, (local_x - 5.0) / max(0.1, d_min - 5.0))
            acc_speed = min(acc_speed, lead_speed * fraction)

        return float(np.clip(acc_speed, 0.0, cruising_speed))

    def _compute_stop_distance(self, perception: PerceptionResult) -> float:
        """Compute distance to stop line/obstacle."""
        return 0.0

    def _get_reason(self, vehicle_state: VehicleState,
                    perception: PerceptionResult) -> str:
        """Get human-readable reason for current behavior."""
        reasons = {
            BehaviorState.LANE_FOLLOW: "Cruising along lane center" if vehicle_state.y > 0 else "Passing slower traffic",
            BehaviorState.LANE_CHANGE_LEFT: "Overtaking slower vehicle ahead",
            BehaviorState.LANE_CHANGE_RIGHT: "Merging back to cruising lane",
            BehaviorState.STOP: "Yielding safely at crosswalk / red light",
            BehaviorState.EMERGENCY_STOP: "Emergency braking",
        }
        return reasons.get(self.state, "Cruising")