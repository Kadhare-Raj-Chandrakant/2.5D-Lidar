"""Sensor view visualization (camera, LiDAR)."""
import pygame
import numpy as np
import cv2
from ..types import SensorData, PerceptionResult, VehicleState
from ..utils.config import config


class SensorViews:
    """Renders sensor data views."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.camera_surface = pygame.Surface((width // 2, height // 2))
        self.lidar_surface = pygame.Surface((width // 2, height // 2))

    def render_camera(self, sensor_data: SensorData,
                      perception: PerceptionResult) -> pygame.Surface:
        """Render camera views with detections."""
        self.camera_surface.fill((20, 20, 30))

        views = [
            ("FRONT", sensor_data.camera_front),
            ("REAR", sensor_data.camera_rear),
        ]

        for i, (name, img) in enumerate(views):
            if img is not None and img.size > 0:
                surf = self._numpy_to_surface(img)
                surf = pygame.transform.scale(surf, (self.width // 2 - 10, self.height // 2 - 40))
                self.camera_surface.blit(surf, (5, 5 + i * (self.height // 2 - 30)))

            font = pygame.font.Font(None, 24)
            text = font.render(name, True, (200, 200, 200))
            self.camera_surface.blit(text, (10, 10 + i * (self.height // 2 - 30)))

        return self.camera_surface

    def render_lidar(self, sensor_data: SensorData,
                     vehicle_state: VehicleState) -> pygame.Surface:
        """Render LiDAR point cloud top-down."""
        self.lidar_surface.fill((10, 10, 20))

        if sensor_data.lidar is not None and len(sensor_data.lidar) > 0:
            points = sensor_data.lidar[:, :2]

            scale = min(self.width, self.height) / 170.0
            cx, cy = self.width // 4, self.height // 4

            for pt in points[::10]:
                sx = int(cx + pt[1] * scale)
                sy = int(cy - pt[0] * scale)
                if 0 <= sx < self.width // 2 and 0 <= sy < self.height // 2:
                    dist = np.sqrt(pt[0]**2 + pt[1]**2)
                    intensity = min(255, int(255 * (1 - dist / 85)))
                    color = (intensity, intensity, intensity)
                    pygame.draw.circle(self.lidar_surface, color, (sx, sy), 1)

        pygame.draw.circle(self.lidar_surface, (0, 100, 255), (self.width // 4, self.height // 4), 5)

        font = pygame.font.Font(None, 24)
        text = font.render("LIDAR TOP-DOWN", True, (200, 200, 200))
        self.lidar_surface.blit(text, (10, 10))

        return self.lidar_surface

    def _numpy_to_surface(self, img: np.ndarray) -> pygame.Surface:
        """Convert numpy array to pygame surface."""
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = np.rot90(img)
            img = pygame.surfarray.make_surface(img)
        else:
            img = pygame.surfarray.make_surface(img)
        return img.convert()