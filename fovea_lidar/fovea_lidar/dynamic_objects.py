import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from scipy.spatial.distance import cdist
from benchmark import benchmark_timer


@dataclass
class DynamicObject:
    id: int
    center: np.ndarray          # [x, y, z]
    velocity: np.ndarray        # [vx, vy, vz]
    size: np.ndarray            # [width, length, height]
    points: np.ndarray          # Nx3 points belonging to this object
    age: int = 0
    hits: int = 1
    misses: int = 0
    color: Tuple[float, float, float] = field(default_factory=lambda: (0, 1, 0))
    cov: np.ndarray = field(default_factory=lambda: np.eye(3) * 0.1)

    def predict(self, dt: float) -> np.ndarray:
        """Predict position after dt seconds."""
        return self.center + self.velocity * dt

    def get_halo_radius(self, safety_factor: float = 1.5) -> float:
        """Safety halo radius based on size and velocity."""
        max_dim = max(self.size[0], self.size[1])
        speed = np.linalg.norm(self.velocity[:2])
        return safety_factor * (max_dim / 2 + speed * 1.0)  # 1s prediction horizon


class DynamicObjectTracker:
    def __init__(
        self,
        cluster_eps: float = 1.0,
        cluster_min_samples: int = 10,
        max_association_dist: float = 2.0,
        max_misses: int = 5,
        min_hits: int = 3,
        dt: float = 0.1,
    ):
        self.cluster_eps = cluster_eps
        self.cluster_min_samples = cluster_min_samples
        self.max_association_dist = max_association_dist
        self.max_misses = max_misses
        self.min_hits = min_hits
        self.dt = dt
        self.objects: Dict[int, DynamicObject] = {}
        self.next_id = 0
        self.colors = [
            (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0),
            (1, 0, 1), (0, 1, 1), (1, 0.5, 0), (0.5, 0, 1),
        ]

    def _dbscan_cluster(self, points: np.ndarray) -> List[np.ndarray]:
        """Simple grid-based clustering for point cloud segmentation."""
        if len(points) < self.cluster_min_samples:
            return []
        
        # Use voxel grid for clustering
        voxel_size = self.cluster_eps
        xy = points[:, :2]
        voxel_coords = np.floor(xy / voxel_size).astype(np.int32)
        
        # Find unique voxels and count points
        unique_voxels, inverse_indices, counts = np.unique(voxel_coords, axis=0, return_inverse=True, return_counts=True)
        
        # Filter voxels with enough points
        valid_mask = counts >= self.cluster_min_samples
        valid_voxels = unique_voxels[valid_mask]
        if len(valid_voxels) == 0:
            return []
        
        # Map valid voxel to index
        voxel_to_idx = {tuple(v): i for i, v in enumerate(valid_voxels)}
        
        # Build adjacency - find connected components
        visited = np.zeros(len(valid_voxels), dtype=bool)
        clusters = []
        
        for i in range(len(valid_voxels)):
            if visited[i]:
                continue
            
            # BFS to find connected component
            cluster_voxel_indices = []
            queue = [i]
            visited[i] = True
            
            while queue:
                v_idx = queue.pop(0)
                cluster_voxel_indices.append(v_idx)
                vx, vy = valid_voxels[v_idx]
                
                # Check 8-connected neighbors
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        neighbor = (vx + dx, vy + dy)
                        if neighbor in voxel_to_idx:
                            n_idx = voxel_to_idx[neighbor]
                            if not visited[n_idx]:
                                visited[n_idx] = True
                                queue.append(n_idx)
            
            # Collect points from cluster voxels
            cluster_mask = np.zeros(len(points), dtype=bool)
            for cv_idx in cluster_voxel_indices:
                # Find points belonging to this voxel
                voxel = valid_voxels[cv_idx]
                voxel_orig_idx = np.where((unique_voxels == voxel).all(axis=1))[0][0]
                cluster_mask |= (inverse_indices == voxel_orig_idx)
            
            cluster_pts = points[cluster_mask]
            if len(cluster_pts) >= self.cluster_min_samples:
                clusters.append(cluster_pts)
        
        return clusters

    def update(self, points: np.ndarray) -> List[DynamicObject]:
        """Update tracker with new point cloud."""
        with benchmark_timer.time("dynamic_tracking"):
            if len(points) == 0:
                self._age_objects()
                return list(self.objects.values())

            clusters = self._dbscan_cluster(points)
            detections = []

            for cluster in clusters:
                center = np.mean(cluster, axis=0)
                cov = np.cov(cluster[:, :2].T) if len(cluster) > 2 else np.eye(2) * 0.1
                size = np.ptp(cluster, axis=0)
                size = np.maximum(size, [0.5, 0.5, 0.5])
                
                detections.append({
                    'center': center,
                    'size': size,
                    'points': cluster,
                    'cov': cov,
                })

            matched_obj = self._associate(detections)
            self._age_objects(matched_obj)
            self._prune_lost()

            return [obj for obj in self.objects.values() if obj.hits >= self.min_hits]

    def _associate(self, detections: List[dict]) -> set:
        matched_det = set()
        matched_obj = set()

        for obj_id, obj in self.objects.items():
            if obj.misses > 0:
                continue
            
            pred_pos = obj.predict(self.dt)
            best_dist = float('inf')
            best_det_idx = -1

            for i, det in enumerate(detections):
                if i in matched_det:
                    continue
                dist = np.linalg.norm(pred_pos[:2] - det['center'][:2])
                if dist < best_dist and dist < self.max_association_dist:
                    best_dist = dist
                    best_det_idx = i

            if best_det_idx >= 0:
                det = detections[best_det_idx]
                matched_det.add(best_det_idx)
                matched_obj.add(obj_id)
                
                measured_vel = (det['center'] - obj.center) / self.dt
                obj.velocity = 0.7 * obj.velocity + 0.3 * measured_vel
                obj.center = det['center']
                obj.size = det['size']
                obj.points = det['points']
                obj.hits += 1
                obj.misses = 0
                obj.cov = det.get('cov', obj.cov)

        for i, det in enumerate(detections):
            if i not in matched_det:
                color = self.colors[self.next_id % len(self.colors)]
                obj = DynamicObject(
                    id=self.next_id,
                    center=det['center'],
                    velocity=np.zeros(3),
                    size=det['size'],
                    points=det['points'],
                    color=color,
                    cov=det.get('cov', np.eye(3) * 0.1),
                )
                self.objects[self.next_id] = obj
                matched_obj.add(self.next_id)  # New objects are "matched" this frame
                self.next_id += 1
        
        return matched_obj

    def _age_objects(self, matched_ids: set = None):
        if matched_ids is None:
            matched_ids = set()
        for obj_id, obj in self.objects.items():
            obj.age += 1
            if obj_id in matched_ids:
                obj.misses = 0
            else:
                obj.misses += 1
                if obj.misses > 0:
                    obj.center = obj.predict(self.dt)

    def _prune_lost(self):
        to_remove = [oid for oid, obj in self.objects.items() if obj.misses > self.max_misses]
        for oid in to_remove:
            del self.objects[oid]

    def get_confirmed_objects(self) -> List[DynamicObject]:
        return [obj for obj in self.objects.values() if obj.hits >= self.min_hits]


def compute_dynamic_risk(
    grid_map,
    objects: List[DynamicObject],
    halo_weight: float = 2.0,
    prediction_horizon: float = 2.0,
) -> np.ndarray:
    """Add risk from dynamic objects with predicted safety halos."""
    from fovea_lidar.risk import compute_risk
    risk = np.zeros_like(grid_map.elevation)
    size_y, size_x = risk.shape
    res = grid_map.resolution
    ox, oy = grid_map.origin_x, grid_map.origin_y

    for obj in objects:
        for t in np.linspace(0, prediction_horizon, 5):
            pred_pos = obj.predict(t)
            cx, cy = pred_pos[0], pred_pos[1]
            gx = int((cx - ox) / res)
            gy = int((cy - oy) / res)
            
            halo_r = obj.get_halo_radius()
            halo_cells = int(halo_r / res)
            
            y_min = max(0, gy - halo_cells)
            y_max = min(size_y, gy + halo_cells + 1)
            x_min = max(0, gx - halo_cells)
            x_max = min(size_x, gx + halo_cells + 1)

            for y in range(y_min, y_max):
                for x in range(x_min, x_max):
                    dx = (x - gx) * res
                    dy = (y - gy) * res
                    dist = np.sqrt(dx * dx + dy * dy)
                    if dist <= halo_r:
                        weight = halo_weight * (1.0 - dist / halo_r) * (1.0 - t / prediction_horizon * 0.5)
                        risk[y, x] = max(risk[y, x], weight)

    return np.clip(risk, 0.0, 10.0)