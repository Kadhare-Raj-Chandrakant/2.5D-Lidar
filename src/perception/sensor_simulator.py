"""Sensor simulation for pygame mode."""
import numpy as np
import cv2
from typing import List, Optional, Tuple
from ..types import SensorData, DetectedObject, BoundingBox3D, BoundingBox2D, VehicleState
from ..utils.config import config
import math


class SensorSimulator:
    """Simulates vehicle sensors in pygame mode."""

    def __init__(self, world_objects: List = None):
        self.world_objects = world_objects or []
        self.camera_config = config.get('sensors.camera', [])
        self.lidar_config = config.get('sensors.lidar', [])
        self.radar_config = config.get('sensors.radar', [])

    def simulate(self, vehicle_state: VehicleState, dt: float) -> SensorData:
        """Generate synthetic sensor data based on world state."""
        sensor_data = SensorData()
        sensor_data.timestamp = vehicle_state.timestamp

        sensor_data.camera_front = self._simulate_camera(vehicle_state, "front")
        sensor_data.camera_rear = self._simulate_camera(vehicle_state, "rear")

        sensor_data.lidar = self._simulate_lidar(vehicle_state)
        sensor_data.radar = self._simulate_radar(vehicle_state)

        return sensor_data

    def _simulate_camera(self, vehicle_state: VehicleState, name: str) -> np.ndarray:
        """Generate synthetic camera image with detected objects drawn."""
        cfg = next((c for c in self.camera_config if c['name'] == name), None)
        if not cfg:
            return np.zeros((480, 640, 3), dtype=np.uint8)

        width = cfg.get('width', 640)
        height = cfg.get('height', 480)
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:] = (50, 50, 60)  # Dark background

        fov = np.deg2rad(cfg.get('fov', 90))
        focal_length = width / (2 * np.tan(fov / 2))

        for obj in self.world_objects:
            if not hasattr(obj, 'bbox_3d'):
                continue

            rel_x = obj.bbox_3d.x - vehicle_state.x
            rel_y = obj.bbox_3d.y - vehicle_state.y

            yaw = vehicle_state.yaw
            cos_yaw = np.cos(-yaw)
            sin_yaw = np.sin(-yaw)

            local_x = cos_yaw * rel_x - sin_yaw * rel_y
            local_y = sin_yaw * rel_x + cos_yaw * rel_y

            if local_x <= 0:
                continue

            u = int(width / 2 + focal_length * local_y / local_x)
            v = int(height / 2 - focal_length * obj.bbox_3d.z / local_x)

            if 0 <= u < width and 0 <= v < height:
                box_w = int(focal_length * obj.bbox_3d.width / local_x)
                box_h = int(focal_length * obj.bbox_3d.height / local_x)

                x1 = max(0, u - box_w // 2)
                y1 = max(0, v - box_h // 2)
                x2 = min(width, u + box_w // 2)
                y2 = min(height, v + box_h // 2)

                cls_name = obj.bbox_3d.class_name if obj.bbox_3d else "unknown"
                color = (0, 255, 0) if cls_name == "car" else (255, 0, 0)
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                cv2.putText(img, cls_name, (x1, y1 - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        cv2.putText(img, f"{name.upper()} CAM", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        return img

    def _simulate_lidar(self, vehicle_state: VehicleState) -> np.ndarray:
        """Generate synthetic LiDAR point cloud."""
        cfg = self.lidar_config[0] if self.lidar_config else {}
        channels = cfg.get('channels', 32)
        range_max = cfg.get('range', 85.0)
        points_per_channel = cfg.get('points_per_second', 500000) // (channels * 20)

        points = []

        for obj in self.world_objects:
            if not hasattr(obj, 'bbox_3d'):
                continue

            rel_x = obj.bbox_3d.x - vehicle_state.x
            rel_y = obj.bbox_3d.y - vehicle_state.y
            rel_z = obj.bbox_3d.z - vehicle_state.z if hasattr(vehicle_state, 'z') else 0

            dist = np.sqrt(rel_x**2 + rel_y**2 + rel_z**2)
            if dist > range_max:
                continue

            num_points = min(points_per_channel, max(10, int(1000 / (dist + 1))))

            for _ in range(num_points):
                dx = np.random.uniform(-obj.bbox_3d.width/2, obj.bbox_3d.width/2)
                dy = np.random.uniform(-obj.bbox_3d.length/2, obj.bbox_3d.length/2)
                dz = np.random.uniform(-obj.bbox_3d.height/2, obj.bbox_3d.height/2)

                yaw = obj.bbox_3d.yaw
                cos_yaw = np.cos(yaw)
                sin_yaw = np.sin(yaw)

                wx = obj.bbox_3d.x + cos_yaw * dx - sin_yaw * dy
                wy = obj.bbox_3d.y + sin_yaw * dx + cos_yaw * dy
                wz = obj.bbox_3d.z + dz

                points.append([wx, wy, wz, 1.0])

        if not points:
            return np.empty((0, 4))

        return np.array(points)

    def _simulate_radar(self, vehicle_state: VehicleState) -> List[dict]:
        """Generate synthetic radar detections."""
        detections = []
        for obj in self.world_objects:
            if not hasattr(obj, 'bbox_3d'):
                continue

            rel_x = obj.bbox_3d.x - vehicle_state.x
            rel_y = obj.bbox_3d.y - vehicle_state.y

            dist = np.sqrt(rel_x**2 + rel_y**2)
            if dist > 100:
                continue

            yaw = vehicle_state.yaw
            cos_yaw = np.cos(-yaw)
            sin_yaw = np.sin(-yaw)

            local_x = cos_yaw * rel_x - sin_yaw * rel_y
            local_y = sin_yaw * rel_x + cos_yaw * rel_y

            if local_x <= 0:
                continue

            detections.append({
                'x': obj.bbox_3d.x,
                'y': obj.bbox_3d.y,
                'z': obj.bbox_3d.z,
                'local_x': local_x,
                'local_y': local_y,
                'length': obj.bbox_3d.length,
                'width': obj.bbox_3d.width,
                'height': obj.bbox_3d.height,
                'yaw': obj.bbox_3d.yaw,
                'class_name': getattr(obj.bbox_3d, 'class_name', 'vehicle'),
                'velocity': obj.bbox_3d.velocity[0] if obj.bbox_3d.velocity else 0,
                'rcs': 10.0
            })

        return detections

    def update_world_objects(self, objects: List):
        """Update the list of world objects for sensor simulation."""
        self.world_objects = objects