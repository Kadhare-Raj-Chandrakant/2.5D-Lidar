"""
Professional 2.5D LiDAR Visualization with Spectral Color Mapping
Ported from lidar_viewer (stanathong/lidar_viewer) GridSpace rendering
"""
import numpy as np
from typing import Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class SpectralConfig:
    """Color mapping configuration for 2.5D visualization"""
    color_map: str = "spectral"
    min_max_percentile: Tuple[float, float] = (1.0, 99.0)
    gamma: float = 1.0
    empty_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


def _generate_spectral_lut() -> np.ndarray:
    lut = np.zeros((256, 3), dtype=np.float32)
    for i in range(256):
        t = i / 255.0
        if t < 0.25:
            r = 0; g = 4 * t; b = 1
        elif t < 0.5:
            r = 0; g = 1; b = 1 - 4 * (t - 0.25)
        elif t < 0.75:
            r = 4 * (t - 0.5); g = 1; b = 0
        else:
            r = 1; g = 1 - 4 * (t - 0.75); b = 0
        lut[i] = [r, g, b]
    return lut


def _generate_viridis_lut() -> np.ndarray:
    lut = np.zeros((256, 3), dtype=np.float32)
    for i in range(256):
        t = i / 255.0
        r = 0.267 * (1 - np.cos(np.pi * t))
        g = 0.004 + 0.95 * t**1.5
        b = 0.5 * (1 + np.cos(np.pi * t))
        lut[i] = [np.clip(r, 0, 1), np.clip(g, 0, 1), np.clip(b, 0, 1)]
    return lut


def _generate_plasma_lut() -> np.ndarray:
    lut = np.zeros((256, 3), dtype=np.float32)
    for i in range(256):
        t = i / 255.0
        r = 0.05 + 0.95 * t**2
        g = 0.02 + 0.8 * t**1.5 * (1 - t)
        b = 0.5 * (1 - t)**2
        lut[i] = [np.clip(r, 0, 1), np.clip(g, 0, 1), np.clip(b, 0, 1)]
    return lut


_SPECTRAL_LUT = _generate_spectral_lut()
_VIRIDIS_LUT = _generate_viridis_lut()
_PLASMA_LUT = _generate_plasma_lut()
_JET_LUT = np.array([
    [0, 0, 0.5 + 0.5 * i/255] if i < 64 else
    [0, 0.5 + 0.5*(i-64)/191, 1] if i < 128 else
    [0.5*(i-128)/127, 1, 0.5*(255-i)/127] if i < 192 else
    [1, 0.5*(255-i)/63, 0] if i < 256 else [1, 0, 0]
    for i in range(256)
], dtype=np.float32)


_LUTS = {
    'spectral': _SPECTRAL_LUT,
    'viridis': _VIRIDIS_LUT,
    'plasma': _PLASMA_LUT,
    'jet': _JET_LUT,
}


class SpectralMapper:
    def __init__(self, config: SpectralConfig = None):
        self.config = config or SpectralConfig()
        self._lut = _LUTS.get(self.config.color_map, _SPECTRAL_LUT)
        self._value_range = None
        self._scaling_factor = 1.0
    
    def fit(self, data: np.ndarray) -> 'SpectralMapper':
        valid = data[np.isfinite(data)]
        if len(valid) == 0:
            self._value_range = (0.0, 1.0)
            self._scaling_factor = 1.0
            return self
        p_low, p_high = self.config.min_max_percentile
        vmin = np.percentile(valid, p_low)
        vmax = np.percentile(valid, p_high)
        if vmax <= vmin:
            vmin = valid.min(); vmax = valid.max()
            if vmax <= vmin: vmax = vmin + 1.0
        self._value_range = (float(vmin), float(vmax))
        self._scaling_factor = 255.0 / (vmax - vmin)
        return self
    
    def map(self, data: np.ndarray) -> np.ndarray:
        if self._value_range is None:
            self.fit(data)
        vmin, vmax = self._value_range
        # Handle NaN/inf before normalization to avoid RuntimeWarning
        finite_mask = np.isfinite(data)
        normalized = np.zeros_like(data, dtype=np.float32)
        normalized[finite_mask] = (data[finite_mask] - vmin) * self._scaling_factor
        normalized = np.clip(normalized, 0, 255).astype(np.uint8)
        if self.config.gamma != 1.0:
            normalized = np.power(normalized / 255.0, self.config.gamma) * 255
            normalized = np.clip(normalized, 0, 255).astype(np.uint8)
        rgb = self._lut[normalized]
        mask = ~np.isfinite(data)
        if mask.any():
            rgb[mask] = self.config.empty_color[:3]
        return rgb
    
    def map_rgba(self, data: np.ndarray, alpha: float = 1.0) -> np.ndarray:
        rgb = self.map(data)
        rgba = np.zeros((*data.shape, 4), dtype=np.float32)
        rgba[..., :3] = rgb
        rgba[..., 3] = alpha
        rgba[~np.isfinite(data), 3] = 0.0
        return rgba


class GridSpace2D:
    def __init__(self, resolution: float, size_x: int, size_y: int, origin_x: float, origin_y: float):
        self.resolution = resolution
        self.size_x = size_x
        self.size_y = size_y
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.max_height = np.full((size_y, size_x), -np.inf, dtype=np.float32)
        self.min_height = np.full((size_y, size_x), np.inf, dtype=np.float32)
        self.sum_height = np.zeros((size_y, size_x), dtype=np.float32)
        self.count = np.zeros((size_y, size_x), dtype=np.int32)
        self.avg_height = np.zeros((size_y, size_x), dtype=np.float32)
    
    def reset(self):
        self.max_height.fill(-np.inf)
        self.min_height.fill(np.inf)
        self.sum_height.fill(0)
        self.count.fill(0)
        self.avg_height.fill(0)
    
    def update(self, points: np.ndarray):
        if points.size == 0:
            return
        gx = ((points[:, 0] - self.origin_x) / self.resolution).astype(np.int32)
        gy = ((points[:, 1] - self.origin_y) / self.resolution).astype(np.int32)
        z = points[:, 2]
        valid = (gx >= 0) & (gx < self.size_x) & (gy >= 0) & (gy < self.size_y)
        gx, gy, z = gx[valid], gy[valid], z[valid]
        if gx.size == 0:
            return
        np.maximum.at(self.max_height, (gy, gx), z)
        np.minimum.at(self.min_height, (gy, gx), z)
        np.add.at(self.sum_height, (gy, gx), z)
        np.add.at(self.count, (gy, gx), 1)
        mask = self.count > 0
        self.avg_height[mask] = self.sum_height[mask] / self.count[mask]
        self.max_height[~mask] = np.nan
        self.min_height[~mask] = np.nan
    
    def get_layers(self) -> Dict[str, np.ndarray]:
        return {
            'max_height': self.max_height.copy(),
            'min_height': self.min_height.copy(),
            'avg_height': self.avg_height.copy(),
            'density': self.count.astype(np.float32),
        }
    
    def create_spectral_images(self, config: SpectralConfig = None) -> Dict[str, np.ndarray]:
        mapper = SpectralMapper(config)
        layers = self.get_layers()
        images = {}
        for name, data in layers.items():
            mapper.fit(data)
            images[name] = mapper.map_rgba(data, alpha=0.8)
        return images


def create_professional_2d_view(grid_map, points: np.ndarray = None, resolution: float = None) -> Dict[str, np.ndarray]:
    if resolution is None:
        resolution = grid_map.resolution
    gs = GridSpace2D(
        resolution=resolution,
        size_x=grid_map.size_x,
        size_y=grid_map.size_y,
        origin_x=grid_map.origin_x,
        origin_y=grid_map.origin_y,
    )
    if points is not None:
        gs.update(points)
    else:
        elev = grid_map.get_elevation()
        occ = grid_map.get_occupancy()
        valid = occ > 0
        ys, xs = np.where(valid)
        if len(xs) > 0:
            fake_points = np.column_stack([
                grid_map.origin_x + (xs + 0.5) * resolution,
                grid_map.origin_y + (ys + 0.5) * resolution,
                elev[ys, xs]
            ])
            gs.update(fake_points)
    return gs.create_spectral_images()
