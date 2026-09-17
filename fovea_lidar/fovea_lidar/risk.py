import numpy as np
from grid_map import GridMap2D
from benchmark import benchmark_timer


def compute_risk(
    grid_map: GridMap2D,
    weight_occupancy: float = 1.0,
    weight_elevation_var: float = 0.5,
    weight_proximity: float = 0.3,
    weight_roughness: float = 0.2,
    proximity_falloff: float = 10.0,
) -> np.ndarray:
    """Compute risk score for each cell.
    
    Risk factors:
    - Occupancy: cells with obstacles are risky
    - Elevation variance: rough terrain is risky
    - Proximity: closer cells are more immediately relevant
    - Roughness: high roughness indicates complex terrain
    """
    with benchmark_timer.time("risk_computation"):
        size_y, size_x = grid_map.elevation.shape
        risk = np.zeros((size_y, size_x), dtype=np.float32)

        occupancy = grid_map.get_occupancy()
        roughness = grid_map.get_roughness()
        elevation = grid_map.get_elevation()

        if weight_occupancy > 0:
            risk += weight_occupancy * occupancy

        if weight_elevation_var > 0:
            risk += weight_elevation_var * np.nan_to_num(roughness, nan=0.0)

        if weight_roughness > 0:
            risk += weight_roughness * np.nan_to_num(roughness, nan=0.0)

        if weight_proximity > 0:
            y_indices, x_indices = np.indices((size_y, size_x))
            world_x = grid_map.origin_x + (x_indices + 0.5) * grid_map.resolution
            world_y = grid_map.origin_y + (y_indices + 0.5) * grid_map.resolution
            dist = np.sqrt(world_x ** 2 + world_y ** 2)
            proximity_risk = np.exp(-dist / proximity_falloff)
            risk += weight_proximity * proximity_risk

        risk = np.clip(risk, 0.0, 10.0)
        return risk


def compute_dynamic_risk(
    grid_map: GridMap2D,
    dynamic_objects: list,
    halo_radius: float = 2.0,
    halo_weight: float = 2.0,
) -> np.ndarray:
    """Add risk from dynamic objects with safety halos."""
    risk = np.zeros_like(grid_map.elevation)
    size_y, size_x = grid_map.elevation.shape

    for obj in dynamic_objects:
        cx, cy = obj['center'][:2]
        gx = int((cx - grid_map.origin_x) / grid_map.resolution)
        gy = int((cy - grid_map.origin_y) / grid_map.resolution)

        halo_cells = int(halo_radius / grid_map.resolution)
        y_min = max(0, gy - halo_cells)
        y_max = min(size_y, gy + halo_cells + 1)
        x_min = max(0, gx - halo_cells)
        x_max = min(size_x, gx + halo_cells + 1)

        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                dx = (x - gx) * grid_map.resolution
                dy = (y - gy) * grid_map.resolution
                dist = np.sqrt(dx * dx + dy * dy)
                if dist <= halo_radius:
                    risk[y, x] += halo_weight * (1.0 - dist / halo_radius)

    return np.clip(risk, 0.0, 10.0)


def combine_risk(static_risk: np.ndarray, dynamic_risk: np.ndarray) -> np.ndarray:
    return np.maximum(static_risk, dynamic_risk)