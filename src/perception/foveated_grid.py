"""Variable-Resolution 2.5D Semantic Elevation Grid Engine.

Projects 3D LiDAR points classified by the deep learning pipeline into
a concentric multi-resolution 2.5D elevation grid:
  - Inner Ring (0 to 10m):   5cm cells (0.05m)  -> Critical safety zone (curbs, potholes, pedestrians)
  - Mid Ring   (10 to 30m):  20cm cells (0.20m) -> Vehicle road corridor
  - Outer Ring (30 to 100m): 50cm cells (0.50m) -> Distant environment horizon

Provides elevation layers (z_min, z_max, z_mean, roughness) and semantic layers
with >90% memory reduction compared to a uniform 5cm 3D grid.
"""

import numpy as np
import time
from typing import Dict, List, Tuple, Optional


class FoveatedGrid25D:
    """Adaptive variable-resolution 2.5D elevation and semantic grid."""

    def __init__(
        self,
        r_inner: float = 10.0,
        r_mid: float = 30.0,
        r_outer: float = 100.0,
        res_inner: float = 0.05,   # 5cm
        res_mid: float = 0.20,     # 20cm
        res_outer: float = 0.50,   # 50cm
    ):
        self.r_inner = r_inner
        self.r_mid = r_mid
        self.r_outer = r_outer

        self.res_inner = res_inner
        self.res_mid = res_mid
        self.res_outer = res_outer

        # Grid dimension calculations
        # Tier 0 (Inner): 20m x 20m bounding box at 0.05m -> 400 x 400 = 160,000 cells (masked to circle)
        self.dim_inner = int(np.ceil(2 * r_inner / res_inner))
        # Tier 1 (Mid): 60m x 60m ring at 0.20m -> 300 x 300 = 90,000 cells (masked to annulus)
        self.dim_mid = int(np.ceil(2 * r_mid / res_mid))
        # Tier 2 (Outer): 200m x 200m ring at 0.50m -> 400 x 400 = 160,000 cells (masked to annulus)
        self.dim_outer = int(np.ceil(2 * r_outer / res_outer))

        # Memory benchmark metrics
        self.bytes_per_cell = 16  # 4 floats: z_min, z_max, z_mean, roughness + 2 bytes: class_id, count
        self._calculate_theoretical_memory()

    def _calculate_theoretical_memory(self):
        """Calculates theoretical memory footprint of Uniform vs Variable-Resolution grid."""
        # Uniform 5cm grid covering 200m x 200m
        uniform_dim = int(200.0 / self.res_inner)  # 4000 x 4000
        self.uniform_total_cells = uniform_dim * uniform_dim  # 16,000,000 cells
        self.uniform_memory_mb = (self.uniform_total_cells * self.bytes_per_cell) / (1024 * 1024)  # ~244.1 MB

        # Variable resolution active cells:
        # Inner circle: pi * 10^2 / 0.05^2 = ~125,663 cells
        # Mid annulus: pi * (30^2 - 10^2) / 0.20^2 = ~62,831 cells
        # Outer annulus: pi * (100^2 - 30^2) / 0.50^2 = ~114,353 cells
        # Total active cells: ~302,847 cells
        self.foveated_total_cells = int(
            np.pi * (self.r_inner ** 2) / (self.res_inner ** 2) +
            np.pi * (self.r_mid ** 2 - self.r_inner ** 2) / (self.res_mid ** 2) +
            np.pi * (self.r_outer ** 2 - self.r_mid ** 2) / (self.res_outer ** 2)
        )
        self.foveated_memory_mb = (self.foveated_total_cells * self.bytes_per_cell) / (1024 * 1024)  # ~4.6 MB
        self.memory_savings_pct = (1.0 - self.foveated_memory_mb / self.uniform_memory_mb) * 100.0

    def build_grid(
        self,
        points: np.ndarray,
        labels: np.ndarray,
        vehicle_pose: Optional[Dict[str, float]] = None,
    ) -> Dict:
        """Projects classified 3D points into a variable-resolution 2.5D elevation grid.

        Args:
            points: (N, 3+) array of points in vehicle frame
            labels: (N,) semantic class IDs (0..3)
            vehicle_pose: Optional dict with x, y, yaw

        Returns:
            Dictionary with grid summary, active cells, memory savings, and visualization payload.
        """
        t0 = time.perf_counter()

        if points is None or len(points) == 0:
            return self._empty_grid_payload()

        N = points.shape[0]
        xyz = points[:, :3]
        dists = np.sqrt(xyz[:, 0] ** 2 + xyz[:, 1] ** 2)

        # Distribute points into 3 concentric tiers
        mask_inner = dists <= self.r_inner
        mask_mid = (dists > self.r_inner) & (dists <= self.r_mid)
        mask_outer = (dists > self.r_mid) & (dists <= self.r_outer)

        # Sample active cells per tier for fast serialization & visualization
        cells_inner = self._bin_points(xyz[mask_inner], labels[mask_inner], self.res_inner, tier_id=0, max_cells=150)
        cells_mid = self._bin_points(xyz[mask_mid], labels[mask_mid], self.res_mid, tier_id=1, max_cells=120)
        cells_outer = self._bin_points(xyz[mask_outer], labels[mask_outer], self.res_outer, tier_id=2, max_cells=80)

        all_cells = cells_inner + cells_mid + cells_outer
        processing_time_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "tier_metrics": [
                {"tier": 0, "name": "Inner Safety (0-10m)", "res_m": self.res_inner, "count": int(np.sum(mask_inner))},
                {"tier": 1, "name": "Mid Corridor (10-30m)", "res_m": self.res_mid, "count": int(np.sum(mask_mid))},
                {"tier": 2, "name": "Outer Horizon (30-100m)", "res_m": self.res_outer, "count": int(np.sum(mask_outer))},
            ],
            "memory_benchmark": {
                "uniform_3d_mb": round(self.uniform_memory_mb, 1),
                "foveated_25d_mb": round(self.foveated_memory_mb, 1),
                "reduction_pct": round(self.memory_savings_pct, 1),
                "uniform_cells": self.uniform_total_cells,
                "foveated_cells": self.foveated_total_cells,
            },
            "latency_ms": round(processing_time_ms, 2),
            "fps": round(1000.0 / max(processing_time_ms, 0.5), 1),
            "cells": all_cells,
        }

    def _bin_points(
        self,
        pts: np.ndarray,
        lbls: np.ndarray,
        resolution: float,
        tier_id: int,
        max_cells: int = 150
    ) -> List[Dict]:
        """Aggregates points into 2.5D cells with elevation stats and dominant class."""
        if len(pts) == 0:
            return []

        # Quantize XY to grid coordinates
        gx = np.floor(pts[:, 0] / resolution).astype(np.int32)
        gy = np.floor(pts[:, 1] / resolution).astype(np.int32)

        # Unique cell keys using integer hash
        keys = (gx.astype(np.int64) << 32) | (gy.astype(np.int64) & 0xFFFFFFFF)
        unique_keys, indices, counts = np.unique(keys, return_inverse=True, return_counts=True)

        cells = []
        limit = min(len(unique_keys), max_cells)
        # Select representative cells across the space
        step = max(1, len(unique_keys) // limit)

        for i in range(0, len(unique_keys), step):
            if len(cells) >= max_cells:
                break
            cell_mask = indices == i
            cell_z = pts[cell_mask, 2]
            cell_lbl = lbls[cell_mask]

            k = unique_keys[i]
            x_int = int(k >> 32)
            y_int = int(k & 0xFFFFFFFF)
            if y_int >= 0x80000000:
                y_int -= 0x100000000

            center_x = float((x_int + 0.5) * resolution)
            center_y = float((y_int + 0.5) * resolution)

            z_min = float(np.min(cell_z))
            z_max = float(np.max(cell_z))
            z_mean = float(np.mean(cell_z))
            roughness = float(np.std(cell_z)) if len(cell_z) > 1 else 0.0

            # Dominant semantic class (bincount)
            dom_class = int(np.argmax(np.bincount(cell_lbl, minlength=4)))

            cells.append({
                "x": round(center_x, 2),
                "y": round(center_y, 2),
                "z_mean": round(z_mean, 2),
                "z_diff": round(z_max - z_min, 2),
                "roughness": round(roughness, 3),
                "class_id": dom_class,
                "tier": tier_id,
                "size": resolution,
            })

        return cells

    def _empty_grid_payload(self) -> Dict:
        return {
            "tier_metrics": [
                {"tier": 0, "name": "Inner Safety (0-10m)", "res_m": self.res_inner, "count": 0},
                {"tier": 1, "name": "Mid Corridor (10-30m)", "res_m": self.res_mid, "count": 0},
                {"tier": 2, "name": "Outer Horizon (30-100m)", "res_m": self.res_outer, "count": 0},
            ],
            "memory_benchmark": {
                "uniform_3d_mb": round(self.uniform_memory_mb, 1),
                "foveated_25d_mb": round(self.foveated_memory_mb, 1),
                "reduction_pct": round(self.memory_savings_pct, 1),
                "uniform_cells": self.uniform_total_cells,
                "foveated_cells": self.foveated_total_cells,
            },
            "latency_ms": 0.0,
            "fps": 60.0,
            "cells": [],
        }
