import numpy as np
from grid_map import GridMap2D
from benchmark import benchmark_timer


def compute_uncertainty(
    grid_map: GridMap2D,
    base_uncertainty: float = 1.0,
    decay_rate: float = 0.1,
) -> np.ndarray:
    """Compute uncertainty based on observation count.
    
    Uncertainty decreases as more observations are made.
    """
    with benchmark_timer.time("uncertainty_computation"):
        obs_count = grid_map.get_observation_count()
        uncertainty = base_uncertainty / (obs_count * decay_rate + 1e-6)
        return np.clip(uncertainty, 0.0, base_uncertainty)


def compute_uncertainty_with_decay(
    grid_map: GridMap2D,
    current_uncertainty: np.ndarray,
    decay_factor: float = 0.95,
    min_uncertainty: float = 0.01,
) -> np.ndarray:
    """Apply temporal decay to uncertainty (areas become more uncertain over time if not observed)."""
    with benchmark_timer.time("uncertainty_decay"):
        new_uncertainty = current_uncertainty * decay_factor
        obs_count = grid_map.get_observation_count()
        observed_mask = obs_count > 0
        new_uncertainty[observed_mask] = np.minimum(
            new_uncertainty[observed_mask],
            1.0 / (obs_count[observed_mask] * 0.1 + 1e-6)
        )
        return np.clip(new_uncertainty, min_uncertainty, 1.0)