"""Object detection from camera/LiDAR data."""
import numpy as np
from typing import List, Optional
from ..types import SensorData, DetectedObject, BoundingBox3D, BoundingBox2D
from ..utils.config import config


class ObjectDetector:
    """Detects objects from sensor data."""

    def __init__(self):
        self.conf_threshold = config.get('perception.camera.confidence_threshold', 0.5)
        self.nms_threshold = config.get('perception.camera.nms_threshold', 0.4)
        self.classes = config.get('perception.camera.classes', [])
        self.lidar_eps = config.get('perception.lidar.clustering_eps', 0.5)
        self.lidar_min_points = config.get('perception.lidar.min_points', 10)

    def detect_camera(self, image: np.ndarray) -> List[DetectedObject]:
        """Detect objects from camera image."""
        return []

    def detect_lidar(self, points: np.ndarray) -> List[DetectedObject]:
        """Cluster LiDAR points into objects (simple Euclidean clustering)."""
        detections = []

        if points is None or len(points) == 0:
            return detections

        from sklearn.cluster import DBSCAN
        try:
            # Subsample dense point clouds for rapid < 2ms clustering
            if len(points) > 800:
                pts = points[::2, :3]
            else:
                pts = points[:, :3]
            clustering = DBSCAN(eps=self.lidar_eps, min_samples=max(4, self.lidar_min_points // 2)).fit(pts)
            labels = clustering.labels_
            points = pts
        except:
            return detections

        unique_labels = set(labels)
        obj_id = 0

        for label in unique_labels:
            if label == -1:
                continue

            cluster_points = points[labels == label]
            if len(cluster_points) < self.lidar_min_points:
                continue

            centroid = np.mean(cluster_points[:, :3], axis=0)
            min_vals = np.min(cluster_points[:, :3], axis=0)
            max_vals = np.max(cluster_points[:, :3], axis=0)
            dimensions = max_vals - min_vals

            if dimensions[0] < 0.35 or dimensions[1] < 0.35:
                continue

            class_name = self._classify_by_size(dimensions)

            detections.append(DetectedObject(
                id=obj_id,
                bbox_3d=BoundingBox3D(
                    x=centroid[0], y=centroid[1], z=centroid[2],
                    length=dimensions[1], width=dimensions[0], height=dimensions[2],
                    yaw=0.0,
                    confidence=min(0.95, len(cluster_points) / 50),
                    class_id=5 if class_name in ['pedestrian', 'person'] else (self.classes.index(class_name) if class_name in self.classes else 0),
                    class_name=class_name
                )
            ))
            obj_id += 1

        return detections

    def detect_radar(self, radar_data: List[dict]) -> List[DetectedObject]:
        """Convert radar detections to objects."""
        detections = []
        for i, det in enumerate(radar_data):
            cls = det.get('class_name', 'vehicle')
            detections.append(DetectedObject(
                id=i,
                bbox_3d=BoundingBox3D(
                    x=det['x'], y=det['y'], z=det.get('z', 0),
                    length=det.get('length', 4.0),
                    width=det.get('width', 2.0),
                    height=det.get('height', 1.5),
                    yaw=det.get('yaw', 0.0),
                    confidence=0.85,
                    class_id=5 if cls in ['pedestrian', 'person'] else 0,
                    class_name=cls,
                    velocity=(det.get('velocity', 0), 0, 0)
                )
            ))
        return detections

    def _classify_by_size(self, dims: np.ndarray) -> str:
        """Classify object by 3D dimensions."""
        length, width, height = dims[1], dims[0], dims[2]
        if width < 1.3 and length < 1.3 and height > 1.0:
            return "pedestrian"
        if length > 5.5:
            return "truck"
        elif length > 3.0:
            return "car"
        else:
            return "car"