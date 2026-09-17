"""Multi-sensor fusion for object tracking."""
import numpy as np
from typing import List, Dict, Optional
from ..types import DetectedObject, PerceptionResult, SensorData
from ..utils.config import config


class KalmanFilter:
    """Simple 2D constant velocity Kalman filter."""
    def __init__(self, dt: float = 0.1):
        self.dt = dt
        self.x = np.zeros(4)  # [x, y, vx, vy]
        self.P = np.eye(4) * 10
        self.F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])
        self.R = np.eye(2) * 0.5
        self.Q = np.eye(4) * 0.1

    def predict(self):
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x[:2]

    def update(self, z: np.ndarray):
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ self.H) @ self.P
        return self.x[:2]


class TrackedObject:
    """Tracked object with Kalman filter."""
    def __init__(self, obj: DetectedObject, track_id: int):
        self.track_id = track_id
        self.obj = obj
        self.kf = KalmanFilter()
        self.age = 0
        self.hits = 1
        self.time_since_update = 0

        if obj.bbox_3d:
            self.kf.x[:2] = [obj.bbox_3d.x, obj.bbox_3d.y]
        elif obj.bbox_2d:
            self.kf.x[:2] = [obj.bbox_2d.x, obj.bbox_2d.y]

    def predict(self):
        pos = self.kf.predict()
        self.age += 1
        self.time_since_update += 1
        if self.obj.bbox_3d:
            self.obj.bbox_3d.x, self.obj.bbox_3d.y = pos
        return pos

    def update(self, obj: DetectedObject):
        if obj.bbox_3d:
            z = np.array([obj.bbox_3d.x, obj.bbox_3d.y])
        elif obj.bbox_2d:
            z = np.array([obj.bbox_2d.x, obj.bbox_2d.y])
        else:
            return
        self.kf.update(z)
        self.hits += 1
        self.time_since_update = 0
        self.obj = obj


class SensorFusion:
    """Fuses camera, LiDAR, and radar detections with tracking."""

    def __init__(self):
        self.tracks: Dict[int, TrackedObject] = {}
        self.next_track_id = 0
        self.max_age = 30
        self.min_hits = 3
        self.iou_threshold = 0.3

    def fuse(self, camera_objs: List[DetectedObject],
             lidar_objs: List[DetectedObject],
             radar_objs: List[DetectedObject]) -> List[DetectedObject]:
        """Fuse detections from multiple sensors."""
        all_detections = camera_objs + lidar_objs + radar_objs

        for track in self.tracks.values():
            track.predict()

        matched_tracks = set()
        matched_dets = set()

        for i, track in enumerate(self.tracks.values()):
            best_iou = 0
            best_idx = -1
            for j, det in enumerate(all_detections):
                if j in matched_dets:
                    continue
                iou = self._compute_iou(track.obj, det)
                if iou > best_iou and iou > self.iou_threshold:
                    best_iou = iou
                    best_idx = j

            if best_idx >= 0:
                track.update(all_detections[best_idx])
                matched_tracks.add(track.track_id)
                matched_dets.add(best_idx)

        for j, det in enumerate(all_detections):
            if j not in matched_dets:
                track = TrackedObject(det, self.next_track_id)
                self.tracks[self.next_track_id] = track
                self.next_track_id += 1

        to_delete = []
        for track_id, track in self.tracks.items():
            if track.time_since_update > self.max_age:
                to_delete.append(track_id)

        for tid in to_delete:
            del self.tracks[tid]

        confirmed = []
        for track in self.tracks.values():
            if track.hits >= self.min_hits:
                track.obj.track_id = track.track_id
                track.obj.age = track.age
                track.obj.hits = track.hits
                confirmed.append(track.obj)

        return confirmed

    def _compute_iou(self, obj1: DetectedObject, obj2: DetectedObject) -> float:
        """Compute IoU between two objects (simplified)."""
        if obj1.bbox_3d and obj2.bbox_3d:
            dx = abs(obj1.bbox_3d.x - obj2.bbox_3d.x)
            dy = abs(obj1.bbox_3d.y - obj2.bbox_3d.y)
            if dx < 5 and dy < 5:
                return 1.0 / (1.0 + dx + dy)
        return 0.0

    def get_tracks(self) -> List[TrackedObject]:
        return list(self.tracks.values())