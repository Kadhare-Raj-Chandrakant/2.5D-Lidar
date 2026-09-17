"""Main visualizer combining all views."""
import pygame
import numpy as np
from ..types import VehicleState, PerceptionResult, Trajectory, BehaviorDecision, ControlCommand, SensorData
from .bird_eye_view import BirdEyeView
from .sensor_views import SensorViews
from .debug_panel import DebugPanel
from ..utils.config import config


class Visualizer:
    """Main visualization dashboard."""

    def __init__(self):
        self.width = config.get('visualization.window_width', 1600)
        self.height = config.get('visualization.window_height', 900)

        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Autonomous Vehicle Simulation")
        self.clock = pygame.time.Clock()

        be_width = self.width // 2
        be_height = self.height

        self.bird_eye = BirdEyeView(be_width, be_height)
        self.sensor_views = SensorViews(self.width // 2, self.height // 2)
        self.debug_panel = DebugPanel(self.width // 2, self.height // 2)

        self.show_sensor = config.get('visualization.show_sensor_views', True)
        self.show_debug = config.get('visualization.show_debug', True)

        self.fps = 0
        self.frame_count = 0
        self.last_fps_time = pygame.time.get_ticks()

    def render(self, vehicle_state: VehicleState,
               perception: PerceptionResult,
               trajectory: Trajectory,
               behavior: BehaviorDecision,
               control: ControlCommand,
               sensor_data: SensorData = None):
        """Render complete dashboard."""
        self.screen.fill((10, 10, 20))

        be_surf = self.bird_eye.render(vehicle_state, perception, trajectory, behavior)
        self.screen.blit(be_surf, (0, 0))

        if self.show_sensor and sensor_data:
            cam_surf = self.sensor_views.render_camera(sensor_data, perception)
            self.screen.blit(cam_surf, (self.width // 2, 0))

            lidar_surf = self.sensor_views.render_lidar(sensor_data, vehicle_state)
            self.screen.blit(lidar_surf, (self.width // 2, self.height // 2))

        if self.show_debug:
            debug_surf = self.debug_panel.render(
                vehicle_state, perception, trajectory, behavior, control, self.fps
            )
            debug_x = self.width // 2 if not self.show_sensor else 0
            debug_y = self.height // 2 if not self.show_sensor else 0
            self.screen.blit(debug_surf, (debug_x, debug_y))

        self._update_fps()
        pygame.display.flip()

    def _update_fps(self):
        """Update FPS counter."""
        self.frame_count += 1
        now = pygame.time.get_ticks()
        if now - self.last_fps_time >= 1000:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_fps_time = now

    def handle_events(self) -> bool:
        """Handle pygame events. Returns False if should quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_s:
                    self.show_sensor = not self.show_sensor
                elif event.key == pygame.K_d:
                    self.show_debug = not self.show_debug
        return True

    def close(self):
        """Close visualization."""
        pygame.quit()