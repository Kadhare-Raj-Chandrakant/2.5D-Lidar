import numpy as np
from typing import Tuple, Optional, List
from dataclasses import dataclass
from benchmark import benchmark_timer


@dataclass
class GridMapConfig:
    resolution: float = 0.2
    size_x: int = 200
    size_y: int = 200
    origin_x: float = -20.0
    origin_y: float = -20.0
    occupancy_threshold: int = 1
    max_height_diff: float = 2.0
    coarse_resolution: float = 1.0


class GridMap2D:
    def __init__(self, config: GridMapConfig):
        self.config = config
        self.size_x = config.size_x
        self.size_y = config.size_y
        self.resolution = config.resolution
        self.origin_x = config.origin_x
        self.origin_y = config.origin_y

        self.elevation = np.full((self.size_y, self.size_x), np.nan, dtype=np.float32)
        self.elevation_sum = np.zeros((self.size_y, self.size_x), dtype=np.float32)
        self.elevation_sq_sum = np.zeros((self.size_y, self.size_x), dtype=np.float32)
        self.occupancy_count = np.zeros((self.size_y, self.size_x), dtype=np.int32)
        self.observation_count = np.zeros((self.size_y, self.size_x), dtype=np.int32)
        self.roughness = np.zeros((self.size_y, self.size_x), dtype=np.float32)
        self.min_z = np.full((self.size_y, self.size_x), np.inf, dtype=np.float32)
        self.max_z = np.full((self.size_y, self.size_x), -np.inf, dtype=np.float32)

        self.coarse_map = None
        self._init_coarse_map()

    def _init_coarse_map(self):
        coarse_size_x = int(self.size_x * self.resolution / self.config.coarse_resolution)
        coarse_size_y = int(self.size_y * self.resolution / self.config.coarse_resolution)
        self.coarse_map = CoarseGridMap(
            resolution=self.config.coarse_resolution,
            size_x=coarse_size_x,
            size_y=coarse_size_y,
            origin_x=self.origin_x,
            origin_y=self.origin_y,
        )

    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        gx = int((x - self.origin_x) / self.resolution)
        gy = int((y - self.origin_y) / self.resolution)
        return gx, gy

    def grid_to_world(self, gx: int, gy: int) -> Tuple[float, float]:
        x = self.origin_x + (gx + 0.5) * self.resolution
        y = self.origin_y + (gy + 0.5) * self.resolution
        return x, y

    def is_valid_cell(self, gx: int, gy: int) -> bool:
        return 0 <= gx < self.size_x and 0 <= gy < self.size_y

    def update(self, points: np.ndarray):
        with benchmark_timer.time("grid_update"):
            if points.size == 0:
                return

            gx = ((points[:, 0] - self.origin_x) / self.resolution).astype(np.int32)
            gy = ((points[:, 1] - self.origin_y) / self.resolution).astype(np.int32)
            z = points[:, 2]

            valid = (gx >= 0) & (gx < self.size_x) & (gy >= 0) & (gy < self.size_y)
            gx = gx[valid]
            gy = gy[valid]
            z = z[valid]

            if gx.size == 0:
                return

            for i in range(len(gx)):
                ix, iy = gx[i], gy[i]
                self.elevation_sum[iy, ix] += z[i]
                self.elevation_sq_sum[iy, ix] += z[i] * z[i]
                self.occupancy_count[iy, ix] += 1
                self.observation_count[iy, ix] += 1
                self.min_z[iy, ix] = min(self.min_z[iy, ix], z[i])
                self.max_z[iy, ix] = max(self.max_z[iy, ix], z[i])

                self.coarse_map.update_point(points[i])

            self._recompute_elevation()
            self._recompute_roughness()

    def _recompute_elevation(self):
        mask = self.occupancy_count > 0
        self.elevation[mask] = self.elevation_sum[mask] / self.occupancy_count[mask]

    def _recompute_roughness(self):
        mask = self.occupancy_count > 1
        if np.any(mask):
            mean = self.elevation_sum[mask] / self.occupancy_count[mask]
            var = self.elevation_sq_sum[mask] / self.occupancy_count[mask] - mean ** 2
            self.roughness[mask] = np.sqrt(np.maximum(var, 0))
            height_diff = self.max_z[mask] - self.min_z[mask]
            self.roughness[mask] = np.maximum(self.roughness[mask], height_diff * 0.5)

    def get_occupancy(self) -> np.ndarray:
        return (self.occupancy_count >= self.config.occupancy_threshold).astype(np.float32)

    def get_elevation(self) -> np.ndarray:
        return self.elevation.copy()

    def get_roughness(self) -> np.ndarray:
        return self.roughness.copy()

    def get_observation_count(self) -> np.ndarray:
        return self.observation_count.copy()

    def get_uncertainty(self) -> np.ndarray:
        return 1.0 / (self.observation_count.astype(np.float32) + 1e-6)

    def get_cell_info(self, gx: int, gy: int) -> dict:
        if not self.is_valid_cell(gx, gy):
            return {}
        return {
            'elevation': self.elevation[gy, gx],
            'occupancy': self.occupancy_count[gy, gx] >= self.config.occupancy_threshold,
            'obs_count': self.observation_count[gy, gx],
            'roughness': self.roughness[gy, gx],
            'uncertainty': 1.0 / (self.observation_count[gy, gx] + 1e-6),
        }

    def reset(self):
        self.elevation.fill(np.nan)
        self.elevation_sum.fill(0)
        self.elevation_sq_sum.fill(0)
        self.occupancy_count.fill(0)
        self.observation_count.fill(0)
        self.roughness.fill(0)
        self.min_z.fill(np.inf)
        self.max_z.fill(-np.inf)
        self.coarse_map.reset()

    def get_bounds(self) -> Tuple[float, float, float, float]:
        return (self.origin_x, self.origin_y,
                self.origin_x + self.size_x * self.resolution,
                self.origin_y + self.size_y * self.resolution)


class CoarseGridMap:
    def __init__(self, resolution: float, size_x: int, size_y: int, origin_x: float, origin_y: float):
        self.resolution = resolution
        self.size_x = size_x
        self.size_y = size_y
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.elevation = np.full((size_y, size_x), np.nan, dtype=np.float32)
        self.occupancy = np.zeros((size_y, size_x), dtype=np.int32)
        self.obs_count = np.zeros((size_y, size_x), dtype=np.int32)

    def update_point(self, point: np.ndarray):
        gx = int((point[0] - self.origin_x) / self.resolution)
        gy = int((point[1] - self.origin_y) / self.resolution)
        if 0 <= gx < self.size_x and 0 <= gy < self.size_y:
            if np.isnan(self.elevation[gy, gx]):
                self.elevation[gy, gx] = point[2]
            else:
                self.elevation[gy, gx] = (self.elevation[gy, gx] * self.obs_count[gy, gx] + point[2]) / (self.obs_count[gy, gx] + 1)
            self.occupancy[gy, gx] += 1
            self.obs_count[gy, gx] += 1

    def reset(self):
        self.elevation.fill(np.nan)
        self.occupancy.fill(0)
        self.obs_count.fill(0)

    def get_occupancy_grid(self) -> np.ndarray:
        return (self.occupancy > 0).astype(np.float32)

    def get_elevation_grid(self) -> np.ndarray:
        return self.elevation.copy()