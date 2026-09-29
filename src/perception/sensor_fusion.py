"""Multi-sensor fusion for object tracking with multi-sensor deduplication."""
import numpy as np
from typing import List, Dict, Optional
from ..types import DetectedObject, PerceptionResult, SensorData, BoundingBox3D
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
            self.obj.bbox_3d.x, self.obj.bbox_3d.y = float(pos[0]), float(pos[1])
            vx, vy = float(self.kf.x[2]), float(self.kf.x[3])
            self.obj.bbox_3d.velocity = (vx, vy, 0.0)
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

        # Preserve richer classification and metadata if incoming object has it
        old_bbox = self.obj.bbox_3d
        self.obj = obj
        if self.obj.bbox_3d and old_bbox:
            if hasattr(old_bbox, 'jacketColor') and not hasattr(self.obj.bbox_3d, 'jacketColor'):
                self.obj.bbox_3d.jacketColor = old_bbox.jacketColor
            if hasattr(old_bbox, 'isCrossing'):
                self.obj.bbox_3d.isCrossing = old_bbox.isCrossing

        if self.obj.bbox_3d:
            vx, vy = float(self.kf.x[2]), float(self.kf.x[3])
            if obj.bbox_3d.velocity and abs(obj.bbox_3d.velocity[0]) > 0.5:
                vx = obj.bbox_3d.velocity[0]
            self.obj.bbox_3d.velocity = (vx, vy, 0.0)


class SensorFusion:
    """Fuses camera, LiDAR, and radar detections with multi-sensor deduplication."""

    def __init__(self):
        self.tracks: Dict[int, TrackedObject] = {}
        self.next_track_id = 0
        self.max_age = 15
        self.min_hits = 2
        self.spatial_gate = 3.2  # Max distance in meters to associate multi-sensor returns

    def _cluster_cross_sensor_detections(self, detections: List[DetectedObject]) -> List[DetectedObject]:
        """Merge detections from different sensors for the exact same physical actor."""
        fused = []
        used = set()

        for i, det_a in enumerate(detections):
            if i in used or not det_a.bbox_3d:
                continue

            merged_det = det_a
            used.add(i)

            for j in range(i + 1, len(detections)):
                if j in used or not detections[j].bbox_3d:
                    continue

                det_b = detections[j]
                dist = np.hypot(det_a.bbox_3d.x - det_b.bbox_3d.x, det_a.bbox_3d.y - det_b.bbox_3d.y)
                if dist < self.spatial_gate:
                    used.add(j)
                    # Merge properties: keep more specific class and LiDAR geometry
                    if det_b.bbox_3d.class_name in ['truck', 'bus', 'pedestrian', 'person']:
                        merged_det.bbox_3d.class_name = det_b.bbox_3d.class_name
                        merged_det.bbox_3d.length = det_b.bbox_3d.length
                        merged_det.bbox_3d.width = det_b.bbox_3d.width
                        merged_det.bbox_3d.height = det_b.bbox_3d.height

                    # If det_b has velocity from radar, adopt it
                    if det_b.bbox_3d.velocity and abs(det_b.bbox_3d.velocity[0]) > 0.1:
                        merged_det.bbox_3d.velocity = det_b.bbox_3d.velocity

                    merged_det.bbox_3d.confidence = min(0.99, merged_det.bbox_3d.confidence + 0.15)

            fused.append(merged_det)

        return fused

    def fuse(self, camera_objs: List[DetectedObject],
             lidar_objs: List[DetectedObject],
             radar_objs: List[DetectedObject]) -> List[DetectedObject]:
        """Fuse detections from multiple sensors without creating duplicate ghost tracks."""
        raw_detections = [d for d in (lidar_objs + radar_objs) if d.bbox_3d]
        all_detections = self._cluster_cross_sensor_detections(raw_detections)

        # 1. Predict track states
        for track in self.tracks.values():
            track.predict()

        matched_tracks = set()
        matched_dets = set()

        # 2. Associate detections with tracks via spatial distance
        for track_id, track in self.tracks.items():
            if not track.obj.bbox_3d:
                continue
            t_x = track.obj.bbox_3d.x
            t_y = track.obj.bbox_3d.y

            best_dist = float('inf')
            best_idx = -1

            for j, det in enumerate(all_detections):
                if j in matched_dets or not det.bbox_3d:
                    continue
                d = np.hypot(t_x - det.bbox_3d.x, t_y - det.bbox_3d.y)
                if d < best_dist and d < self.spatial_gate:
                    best_dist = d
                    best_idx = j

            if best_idx >= 0:
                track.update(all_detections[best_idx])
                matched_tracks.add(track_id)
                matched_dets.add(best_idx)

        # 3. Create new tracks only for genuinely new unmatched detections
        for j, det in enumerate(all_detections):
            if j not in matched_dets:
                track = TrackedObject(det, self.next_track_id)
                self.tracks[self.next_track_id] = track
                self.next_track_id += 1

        # 4. Prune stale tracks
        to_delete = [
            tid for tid, trk in self.tracks.items()
            if trk.time_since_update > self.max_age
        ]
        for tid in to_delete:
            del self.tracks[tid]

        # 5. Return confirmed tracks (one per physical obstacle)
        confirmed = []
        for track in self.tracks.values():
            if track.hits >= self.min_hits and track.obj.bbox_3d:
                track.obj.track_id = track.track_id
                track.obj.id = track.track_id
                track.obj.age = track.age
                track.obj.hits = track.hits
                confirmed.append(track.obj)

        return confirmed

    def get_tracks(self) -> List[TrackedObject]:
        return list(self.tracks.values())