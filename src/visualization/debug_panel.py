"""Debug panel for displaying system metrics."""
import pygame
from ..types import VehicleState, PerceptionResult, Trajectory, BehaviorDecision, ControlCommand
from ..utils.config import config


class DebugPanel:
    """Debug information panel."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.surface = pygame.Surface((width, height))
        self.font = pygame.font.Font(None, 18)
        self.font_bold = pygame.font.Font(None, 20)

    def render(self, vehicle_state: VehicleState,
               perception: PerceptionResult,
               trajectory: Trajectory,
               behavior: BehaviorDecision,
               control: ControlCommand,
               fps: float) -> pygame.Surface:
        """Render debug panel."""
        self.surface.fill((20, 20, 30, 200))

        y = 10
        line_h = 20

        sections = [
            ("VEHICLE STATE", [
                f"Position: ({vehicle_state.x:.1f}, {vehicle_state.y:.1f})",
                f"Yaw: {vehicle_state.yaw:.3f} rad ({np.degrees(vehicle_state.yaw):.1f} deg)",
                f"Speed: {vehicle_state.speed:.2f} m/s ({vehicle_state.speed*3.6:.1f} km/h)",
                f"Accel: {vehicle_state.acceleration:.2f} m/s^2",
                f"Steer: {vehicle_state.steer_angle:.3f} rad",
            ]),
            ("PERCEPTION", [
                f"Objects: {len(perception.objects)}",
                f"Lanes: {len(perception.lanes)}",
                *[f"  ID:{o.track_id} {o.bbox_3d.class_name} ({o.bbox_3d.x:.1f},{o.bbox_3d.y:.1f})"
                  for o in perception.objects[:5] if o.bbox_3d],
            ]),
            ("PLANNING", [
                f"Behavior: {behavior.state.value}",
                f"Target Speed: {behavior.target_speed:.1f} m/s",
                f"Trajectory: {len(trajectory.waypoints)} wps" if trajectory.valid else "Trajectory: INVALID",
                f"Plan Time: {trajectory.planning_time*1000:.1f} ms",
            ]),
            ("CONTROL", [
                f"Steer: {control.steer:.3f}",
                f"Throttle: {control.throttle:.2f}",
                f"Brake: {control.brake:.2f}",
            ]),
            ("PERFORMANCE", [
                f"FPS: {fps:.1f}",
            ]),
        ]

        for title, lines in sections:
            title_surf = self.font_bold.render(title, True, (100, 200, 255))
            self.surface.blit(title_surf, (10, y))
            y += line_h + 2

            for line in lines:
                text = self.font.render(line, True, (200, 200, 200))
                self.surface.blit(text, (15, y))
                y += line_h

            y += 5

        return self.surface

import numpy as np