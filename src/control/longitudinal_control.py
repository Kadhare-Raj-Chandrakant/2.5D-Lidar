"""Longitudinal control: PID controller for speed tracking."""
import numpy as np
from ..types import VehicleState, ControlCommand
from ..utils.config import config


class PIDController:
    """PID controller for longitudinal speed control."""

    def __init__(self):
        self.kp = config.get('control.longitudinal.kp', 1.0)
        self.ki = config.get('control.longitudinal.ki', 0.1)
        self.kd = config.get('control.longitudinal.kd', 0.05)
        self.max_accel = config.get('control.longitudinal.max_accel', 3.0)
        self.max_decel = config.get('control.longitudinal.max_decel', 5.0)

        self.integral = 0.0
        self.prev_error = 0.0
        self.dt = 0.033

    def compute(self, vehicle_state: VehicleState,
                target_speed: float,
                dt: float = None) -> tuple:
        """Compute throttle and brake commands."""
        if dt is not None:
            self.dt = dt

        current_speed = vehicle_state.speed
        error = target_speed - current_speed

        self.integral += error * self.dt
        self.integral = np.clip(self.integral, -10, 10)

        derivative = (error - self.prev_error) / self.dt if self.dt > 0 else 0
        self.prev_error = error

        accel = self.kp * error + self.ki * self.integral + self.kd * derivative

        if accel >= 0:
            throttle = np.clip(accel / self.max_accel, 0, 1)
            brake = 0.0
        else:
            throttle = 0.0
            brake = np.clip(-accel / self.max_decel, 0, 1)

        return throttle, brake

    def reset(self):
        """Reset PID state."""
        self.integral = 0.0
        self.prev_error = 0.0