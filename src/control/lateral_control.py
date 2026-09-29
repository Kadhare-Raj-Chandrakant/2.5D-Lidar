"""Lateral control: Pure Pursuit and Stanley controllers."""
import numpy as np
from typing import List
from ..types import Waypoint, VehicleState, ControlCommand
from ..utils.config import config


class PurePursuitController:
    """Pure Pursuit lateral controller."""

    def __init__(self):
        self.lookahead_base = config.get('control.lateral.lookahead_distance', 5.0)
        self.lookahead_gain = config.get('control.lateral.lookahead_gain', 0.3)
        self.max_steer = config.get('vehicle.max_steer', 0.7)
        self.wheelbase = config.get('vehicle.wheelbase', 2.875)

    def compute(self, vehicle_state: VehicleState,
                trajectory: List[Waypoint]) -> float:
        """Compute steering angle using Pure Pursuit."""
        if not trajectory or len(trajectory) < 2:
            return 0.0

        speed = max(vehicle_state.speed, 0.1)
        lookahead = self.lookahead_base + self.lookahead_gain * speed

        target = self._get_target_point(vehicle_state, trajectory, lookahead)
        if target is None:
            return 0.0

        dx = target.x - vehicle_state.x
        dy = target.y - vehicle_state.y

        cos_yaw = np.cos(vehicle_state.yaw)
        sin_yaw = np.sin(vehicle_state.yaw)

        local_x = cos_yaw * dx + sin_yaw * dy
        local_y = -sin_yaw * dx + cos_yaw * dy

        if local_x <= 0:
            return 0.0

        alpha = np.arctan2(local_y, local_x)
        steer = np.arctan2(2 * self.wheelbase * np.sin(alpha), lookahead)

        return np.clip(steer, -self.max_steer, self.max_steer)

    def _get_target_point(self, vehicle_state: VehicleState,
                          trajectory: List[Waypoint],
                          lookahead: float) -> Waypoint:
        """Find target point at lookahead distance strictly ahead of vehicle."""
        cos_yaw = np.cos(vehicle_state.yaw)
        sin_yaw = np.sin(vehicle_state.yaw)

        for wp in trajectory:
            dx = wp.x - vehicle_state.x
            dy = wp.y - vehicle_state.y
            local_x = cos_yaw * dx + sin_yaw * dy
            if local_x > 0.5:
                dist = np.hypot(dx, dy)
                if dist >= lookahead:
                    return wp

        forward_wps = [
            wp for wp in trajectory 
            if (cos_yaw * (wp.x - vehicle_state.x) + sin_yaw * (wp.y - vehicle_state.y)) > 0.2
        ]
        return forward_wps[-1] if forward_wps else trajectory[-1]


class StanleyController:
    """Stanley lateral controller."""

    def __init__(self):
        self.k = 0.5
        self.max_steer = config.get('vehicle.max_steer', 0.7)
        self.wheelbase = config.get('vehicle.wheelbase', 2.875)

    def compute(self, vehicle_state: VehicleState,
                trajectory: List[Waypoint]) -> float:
        """Compute steering angle using Stanley controller."""
        if not trajectory or len(trajectory) < 2:
            return 0.0

        front_x = vehicle_state.x + self.wheelbase * np.cos(vehicle_state.yaw)
        front_y = vehicle_state.y + self.wheelbase * np.sin(vehicle_state.yaw)

        min_dist = float('inf')
        target_idx = 0
        for i, wp in enumerate(trajectory):
            dist = (wp.x - front_x)**2 + (wp.y - front_y)**2
            if dist < min_dist:
                min_dist = dist
                target_idx = i

        target = trajectory[target_idx]

        path_yaw = target.yaw
        heading_error = self._normalize_angle(path_yaw - vehicle_state.yaw)

        dx = target.x - front_x
        dy = target.y - front_y
        cross_track = -np.sin(vehicle_state.yaw) * dx + np.cos(vehicle_state.yaw) * dy

        speed = max(vehicle_state.speed, 0.1)
        steer = heading_error + np.arctan2(self.k * cross_track, speed)

        return np.clip(steer, -self.max_steer, self.max_steer)

    def _normalize_angle(self, angle: float) -> float:
        while angle > np.pi:
            angle -= 2 * np.pi
        while angle < -np.pi:
            angle += 2 * np.pi
        return angle