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
            # Check if we were in the passing lane (y ≈ -1.75) and have overtaken our target
            if vehicle_state.y < 0.0:
                should_return = False
                if self.overtaking_target_id is not None:
                    target_obj = next((o for o in perception.objects if o.id == self.overtaking_target_id), None)
                    if target_obj and target_obj.bbox_3d:
                        rel_x = vehicle_state.x - target_obj.bbox_3d.x
                        if rel_x >= 16.0:  # Safely ahead of overtaken vehicle by >= 16m
                            should_return = True
                    else:
                        should_return = True
                else:
                    should_return = True

                if should_return and self._can_change_right(perception, vehicle_state):
                    self.state = BehaviorState.LANE_CHANGE_RIGHT
                    self.target_lane = 0
                    self.lane_change_timer = 0.0
                    self.overtaking_target_id = None
                    return

            # Check if there is a slower vehicle ahead in our lane to overtake
            if front_vehicle and self._should_change_lane(front_vehicle, vehicle_state):
                if self._can_change_left(perception, vehicle_state):
                    self.state = BehaviorState.LANE_CHANGE_LEFT
                    self.target_lane = -1
                    self.overtaking_target_id = front_vehicle.id
                    self.lane_change_timer = 0.0
                elif self._can_change_right(perception, vehicle_state):
                    self.state = BehaviorState.LANE_CHANGE_RIGHT
                    self.target_lane = 1
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
        """Find closest vehicle ahead in same lane within detection range."""
        front_vehicles = []
        for obj in perception.objects:
            if not obj.bbox_3d:
                continue
            cls_name = getattr(obj.bbox_3d, 'class_name', '')
            if cls_name in ['pedestrian', 'person']:
                continue

            rel_x = obj.bbox_3d.x - vehicle_state.x
            rel_y = obj.bbox_3d.y - vehicle_state.y

            yaw = vehicle_state.yaw
            local_x = np.cos(yaw) * rel_x + np.sin(yaw) * rel_y
            local_y = -np.sin(yaw) * rel_x + np.cos(yaw) * rel_y

            # In front within 50m and within same lane (1.75m lateral)
            if 0.0 < local_x < 50.0 and abs(local_y) < 1.75:
                front_vehicles.append((local_x, obj))

        if front_vehicles:
            return min(front_vehicles, key=lambda x: x[0])[1]
        return None

    def _check_emergency(self, front_vehicle: Optional[DetectedObject],
                         vehicle_state: VehicleState) -> bool:
        """Check if emergency braking is needed."""
        if not front_vehicle or not front_vehicle.bbox_3d:
            return False

        rel_x = front_vehicle.bbox_3d.x - vehicle_state.x
        rel_y = front_vehicle.bbox_3d.y - vehicle_state.y

        yaw = vehicle_state.yaw
        local_x = np.cos(yaw) * rel_x + np.sin(yaw) * rel_y

        return 0.0 < local_x < self.emergency_brake_dist

    def _should_change_lane(self, front_vehicle: DetectedObject,
                            vehicle_state: VehicleState) -> bool:
        """Determine if lane change is needed based on lead vehicle speed and distance."""
        if not front_vehicle or not front_vehicle.bbox_3d:
            return False

        rel_x = front_vehicle.bbox_3d.x - vehicle_state.x
        rel_y = front_vehicle.bbox_3d.y - vehicle_state.y

        yaw = vehicle_state.yaw
        local_x = np.cos(yaw) * rel_x + np.sin(yaw) * rel_y

        # If obstacle vehicle is closer than 38 meters ahead in lane and slower than cruise
        lead_speed = 8.0
        if front_vehicle.bbox_3d.velocity:
            lead_speed = front_vehicle.bbox_3d.velocity[0]

        return 0.0 < local_x < 38.0 and lead_speed < self.cruising_speed * 0.85

    def _can_change_left(self, perception: PerceptionResult,
                         vehicle_state: VehicleState) -> bool:
        """Check if left lane is clear and within road bounds."""
        if vehicle_state.y <= -3.5:
            return False
        return self._is_lane_clear(perception, vehicle_state, -1)

    def _can_change_right(self, perception: PerceptionResult,
                          vehicle_state: VehicleState) -> bool:
        """Check if right lane is clear and within road bounds."""
        if vehicle_state.y >= 3.5:
            return False
        return self._is_lane_clear(perception, vehicle_state, 1)

    def _is_lane_clear(self, perception: PerceptionResult,
                       vehicle_state: VehicleState, direction: int) -> bool:
        """Check if target lane is clear of traffic."""
        lane_width = 3.5
        target_offset = direction * lane_width

        for obj in perception.objects:
            if not obj.bbox_3d:
                continue

            rel_x = obj.bbox_3d.x - vehicle_state.x
            rel_y = obj.bbox_3d.y - vehicle_state.y

            yaw = vehicle_state.yaw
            local_x = np.cos(yaw) * rel_x + np.sin(yaw) * rel_y
            local_y = -np.sin(yaw) * rel_x + np.cos(yaw) * rel_y

            # Reject if adjacent lane has vehicle between -16m and +28m
            if abs(local_y - target_offset) < lane_width * 0.55 and -16.0 < local_x < 28.0:
                return False
        return True

    def _compute_target_speed(self, vehicle_state: VehicleState,
                              perception: PerceptionResult) -> float:
        """Compute target speed based on traffic, signals, and overtaking."""
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

        if local_x > 38.0:
            return cruising_speed

        if local_x <= self.emergency_brake_dist:
            return 0.0

        # Safe following distance
        lead_speed = 8.0
        if front_vehicle.bbox_3d.velocity and abs(front_vehicle.bbox_3d.velocity[0]) > 0.5:
            lead_speed = front_vehicle.bbox_3d.velocity[0]

        gap = max(0.0, local_x - self.emergency_brake_dist)
        safe_speed = min(cruising_speed, max(lead_speed, cruising_speed * min(1.0, gap / 25.0)))
        return float(safe_speed)

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