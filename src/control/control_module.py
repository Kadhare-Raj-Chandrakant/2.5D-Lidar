"""Main control module combining lateral and longitudinal control."""
from ..types import VehicleState, Trajectory, BehaviorDecision, ControlCommand
from .lateral_control import PurePursuitController, StanleyController
from .longitudinal_control import PIDController
from ..utils.config import config


class ControlModule:
    """Main vehicle control module."""

    def __init__(self):
        method = config.get('control.lateral.method', 'pure_pursuit')
        if method == 'stanley':
            self.lateral = StanleyController()
        else:
            self.lateral = PurePursuitController()

        self.longitudinal = PIDController()

    def compute(self, vehicle_state: VehicleState,
                trajectory: Trajectory,
                behavior: BehaviorDecision,
                dt: float) -> ControlCommand:
        """Compute control commands."""
        steer = 0.0
        if trajectory and trajectory.valid and trajectory.waypoints:
            steer = self.lateral.compute(vehicle_state, trajectory.waypoints)

        target_speed = behavior.target_speed
        if behavior.state.name == "EMERGENCY_STOP":
            target_speed = 0.0
        elif behavior.state.name == "STOP":
            target_speed = 0.0

        throttle, brake = self.longitudinal.compute(vehicle_state, target_speed, dt)

        if behavior.state.name == "EMERGENCY_STOP":
            throttle = 0.0
            brake = 1.0

        cmd = ControlCommand(
            steer=steer,
            throttle=throttle,
            brake=brake,
            timestamp=vehicle_state.timestamp
        )

        return cmd