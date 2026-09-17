"""High-level behavior planner (FSM)."""
from typing import List, Optional
from ..types import VehicleState, PerceptionResult, BehaviorDecision, BehaviorState, DetectedObject, Trajectory
from ..utils.config import config


class BehaviorPlanner:
    """Finite state machine for high-level driving behavior."""

    def __init__(self):
        self.state = BehaviorState.LANE_FOLLOW
        self.target_lane = 0
        self.lane_change_timer = 0.0
        self.lane_change_duration = config.get('planning.behavior.lane_change_time', 3.0)
        self.min_gap = config.get('planning.behavior.min_gap', 3.0)
        self.follow_distance = config.get('planning.behavior.follow_distance', 2.0)
        self.emergency_brake_dist = config.get('planning.behavior.emergency_brake_dist', 5.0)

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
        """Update FSM state based on perception."""
        front_vehicle = self._get_front_vehicle(perception, vehicle_state)
        emergency = self._check_emergency(front_vehicle, vehicle_state)

        if emergency:
            self.state = BehaviorState.EMERGENCY_STOP
            return

        if self.state == BehaviorState.EMERGENCY_STOP:
            if not emergency:
                self.state = BehaviorState.LANE_FOLLOW

        elif self.state == BehaviorState.LANE_FOLLOW:
            if front_vehicle and self._should_change_lane(front_vehicle, vehicle_state):
                if self._can_change_left(perception, vehicle_state):
                    self.state = BehaviorState.LANE_CHANGE_LEFT
                    self.target_lane -= 1
                    self.lane_change_timer = 0
                elif self._can_change_right(perception, vehicle_state):
                    self.state = BehaviorState.LANE_CHANGE_RIGHT
                    self.target_lane += 1
                    self.lane_change_timer = 0

        elif self.state in [BehaviorState.LANE_CHANGE_LEFT, BehaviorState.LANE_CHANGE_RIGHT]:
            self.lane_change_timer += 0.1
            if self.lane_change_timer >= self.lane_change_duration:
                self.state = BehaviorState.LANE_FOLLOW

    def _get_front_vehicle(self, perception: PerceptionResult,
                           vehicle_state: VehicleState) -> Optional[DetectedObject]:
        """Find closest vehicle ahead in same lane."""
        front_vehicles = []
        for obj in perception.objects:
            cls_name = obj.bbox_3d.class_name if obj.bbox_3d else None
            if cls_name not in ["car", "truck", "bus"]:
                continue

            if obj.bbox_3d:
                rel_x = obj.bbox_3d.x - vehicle_state.x
                rel_y = obj.bbox_3d.y - vehicle_state.y

                yaw = vehicle_state.yaw
                local_x = np.cos(yaw) * rel_x + np.sin(yaw) * rel_y
                local_y = -np.sin(yaw) * rel_x + np.cos(yaw) * rel_y

                if local_x > 0 and abs(local_y) < 2.0:
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

        return local_x < self.emergency_brake_dist and local_x > 0

    def _should_change_lane(self, front_vehicle: DetectedObject,
                            vehicle_state: VehicleState) -> bool:
        """Determine if lane change is needed."""
        if not front_vehicle.bbox_3d:
            return False

        rel_x = front_vehicle.bbox_3d.x - vehicle_state.x
        rel_y = front_vehicle.bbox_3d.y - vehicle_state.y

        yaw = vehicle_state.yaw
        local_x = np.cos(yaw) * rel_x + np.sin(yaw) * rel_y

        target_speed = front_vehicle.bbox_3d.velocity[0] if front_vehicle.bbox_3d.velocity else 0
        speed_diff = vehicle_state.speed - target_speed

        return local_x < self.follow_distance * vehicle_state.speed and speed_diff > 1.0

    def _can_change_left(self, perception: PerceptionResult,
                         vehicle_state: VehicleState) -> bool:
        """Check if left lane is clear for lane change."""
        return self._is_lane_clear(perception, vehicle_state, -1)

    def _can_change_right(self, perception: PerceptionResult,
                          vehicle_state: VehicleState) -> bool:
        """Check if right lane is clear for lane change."""
        return self._is_lane_clear(perception, vehicle_state, 1)

    def _is_lane_clear(self, perception: PerceptionResult,
                       vehicle_state: VehicleState, direction: int) -> bool:
        """Check if target lane is clear."""
        lane_width = 3.5
        for obj in perception.objects:
            if not obj.bbox_3d:
                continue

            rel_x = obj.bbox_3d.x - vehicle_state.x
            rel_y = obj.bbox_3d.y - vehicle_state.y

            yaw = vehicle_state.yaw
            local_x = np.cos(yaw) * rel_x + np.sin(yaw) * rel_y
            local_y = -np.sin(yaw) * rel_x + np.cos(yaw) * rel_y

            target_y = direction * lane_width
            if abs(local_y - target_y) < lane_width * 0.5 and 0 < local_x < 30:
                return False
        return True

    def _compute_target_speed(self, vehicle_state: VehicleState,
                              perception: PerceptionResult) -> float:
        """Compute target speed based on traffic."""
        max_speed = config.get('vehicle.max_speed', 30.0)
        front_vehicle = self._get_front_vehicle(perception, vehicle_state)

        if front_vehicle and front_vehicle.bbox_3d:
            target_speed = front_vehicle.bbox_3d.velocity[0] if front_vehicle.bbox_3d.velocity else 0
            return min(max_speed, max(0, target_speed))

        return max_speed

    def _compute_stop_distance(self, perception: PerceptionResult) -> float:
        """Compute distance to stop line/obstacle."""
        return 0.0

    def _get_reason(self, vehicle_state: VehicleState,
                    perception: PerceptionResult) -> str:
        """Get human-readable reason for current behavior."""
        reasons = {
            BehaviorState.LANE_FOLLOW: "Following lane",
            BehaviorState.LANE_CHANGE_LEFT: "Changing lane left",
            BehaviorState.LANE_CHANGE_RIGHT: "Changing lane right",
            BehaviorState.STOP: "Stopping at intersection",
            BehaviorState.EMERGENCY_STOP: "Emergency braking",
        }
        return reasons.get(self.state, "Unknown")

import numpy as np