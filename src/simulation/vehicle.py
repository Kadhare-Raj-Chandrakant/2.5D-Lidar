"""Vehicle dynamics and control application."""
import numpy as np
from ..types import VehicleState, ControlCommand
from ..utils.config import config


class VehicleManager:
    """Manages vehicle dynamics."""

    def __init__(self):
        self.wheelbase = config.get('vehicle.wheelbase', 2.875)
        self.max_speed = config.get('vehicle.max_speed', 30.0)
        self.max_steer = config.get('vehicle.max_steer', 0.7)
        self.mass = config.get('vehicle.mass', 1500.0)
        self.drag_coeff = 0.3
        self.rolling_resistance = 0.015

    def step(self, vehicle_state: VehicleState,
             control: ControlCommand,
             dt: float) -> VehicleState:
        """Apply control and update vehicle state (kinematic bicycle model)."""
        new_state = VehicleState()
        new_state.x = vehicle_state.x
        new_state.y = vehicle_state.y
        new_state.yaw = vehicle_state.yaw
        new_state.speed = vehicle_state.speed
        new_state.steer_angle = np.clip(control.steer, -self.max_steer, self.max_steer)
        new_state.timestamp = vehicle_state.timestamp + dt

        throttle = control.throttle
        brake = control.brake

        engine_force = throttle * 4000
        brake_force = brake * 8000
        drag_force = 0.5 * 1.225 * self.drag_coeff * 2.2 * vehicle_state.speed**2
        if vehicle_state.speed > 0.05:
            rolling_force = self.rolling_resistance * self.mass * 9.81
        else:
            rolling_force = min(engine_force, self.rolling_resistance * self.mass * 9.81) if engine_force > 0 else 0.0

        net_force = engine_force - brake_force - drag_force - rolling_force
        acceleration = net_force / self.mass

        new_state.speed = max(0, min(self.max_speed, vehicle_state.speed + acceleration * dt))
        new_state.acceleration = acceleration

        if abs(new_state.speed) > 0.01 and abs(new_state.steer_angle) > 0.001:
            yaw_rate = new_state.speed * np.tan(new_state.steer_angle) / self.wheelbase
        else:
            yaw_rate = 0.0

        new_state.yaw = vehicle_state.yaw + yaw_rate * dt
        new_state.yaw = self._normalize_angle(new_state.yaw)

        new_state.x += new_state.speed * np.cos(new_state.yaw) * dt
        new_state.y += new_state.speed * np.sin(new_state.yaw) * dt

        return new_state

    def _normalize_angle(self, angle: float) -> float:
        while angle > np.pi:
            angle -= 2 * np.pi
        while angle < -np.pi:
            angle += 2 * np.pi
        return angle