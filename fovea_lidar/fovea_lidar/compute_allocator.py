import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from fovea_lidar.foveation import ROI
from fovea_lidar.grid_map import GridMap2D
from benchmark import benchmark_timer


@dataclass
class ComputeBudget:
    total_budget_ms: float = 100.0
    min_roi_budget_ms: float = 5.0
    max_roi_budget_ms: float = 30.0
    coarse_map_budget_ms: float = 10.0
    preprocessing_budget_ms: float = 15.0
    risk_uncertainty_budget_ms: float = 10.0
    foveation_budget_ms: float = 5.0
    visualization_budget_ms: float = 5.0


class ComputeAllocator:
    def __init__(self, budget: ComputeBudget):
        self.budget = budget
        self.stage_times: Dict[str, float] = {}
        self.roi_budgets: Dict[int, float] = {}

    def allocate_roi_budgets(
        self,
        rois: List[ROI],
        risk_map: np.ndarray,
        uncertainty_map: np.ndarray,
        grid_map: GridMap2D,
    ) -> Dict[int, float]:
        """Allocate compute budget to ROIs based on importance."""
        with benchmark_timer.time("compute_allocation"):
            if not rois:
                return {}

            scores = []
            for roi in rois:
                gx = int((roi.center_x - grid_map.origin_x) / grid_map.resolution)
                gy = int((roi.center_y - grid_map.origin_y) / grid_map.resolution)
                if 0 <= gx < grid_map.size_x and 0 <= gy < grid_map.size_y:
                    risk_score = risk_map[gy, gx] if gy < risk_map.shape[0] and gx < risk_map.shape[1] else 0
                    unc_score = uncertainty_map[gy, gx] if gy < uncertainty_map.shape[0] and gx < uncertainty_map.shape[1] else 0
                    combined = 0.7 * risk_score + 0.3 * unc_score
                else:
                    combined = roi.score
                scores.append(combined)

            scores = np.array(scores)
            total_score = scores.sum()

            available_budget = (
                self.budget.total_budget_ms 
                - self.budget.preprocessing_budget_ms
                - self.budget.risk_uncertainty_budget_ms
                - self.budget.foveation_budget_ms
                - self.budget.visualization_budget_ms
                - self.budget.coarse_map_budget_ms
            )
            available_budget = max(available_budget, self.budget.min_roi_budget_ms)

            if total_score > 0:
                budgets = (scores / total_score) * available_budget
            else:
                budgets = np.ones(len(rois)) * available_budget / len(rois)

            budgets = np.clip(budgets, self.budget.min_roi_budget_ms, self.budget.max_roi_budget_ms)

            if budgets.sum() > available_budget:
                budgets = budgets / budgets.sum() * available_budget

            self.roi_budgets = {roi_id: float(b) for roi_id, b in enumerate(budgets)}
            return self.roi_budgets

    def get_roi_processing_config(self, roi: ROI, roi_id: int) -> Dict:
        """Get processing configuration for an ROI based on allocated budget."""
        budget = self.roi_budgets.get(roi_id, self.budget.min_roi_budget_ms)
        
        detail_level = budget / self.budget.max_roi_budget_ms
        
        return {
            'voxel_size': 0.05 + 0.15 * (1 - detail_level),
            'max_points': int(500 + 2000 * detail_level),
            'refinement_iterations': max(1, int(3 * detail_level)),
            'use_normals': detail_level > 0.5,
            'use_classification': detail_level > 0.7,
        }

    def record_stage_time(self, stage: str, time_ms: float):
        self.stage_times[stage] = time_ms

    def get_budget_status(self) -> Dict:
        total_used = sum(self.stage_times.values())
        return {
            'total_budget_ms': self.budget.total_budget_ms,
            'used_ms': total_used,
            'remaining_ms': self.budget.total_budget_ms - total_used,
            'utilization': total_used / self.budget.total_budget_ms if self.budget.total_budget_ms > 0 else 0,
            'stage_times': self.stage_times.copy(),
            'roi_budgets': self.roi_budgets.copy(),
        }

    def is_over_budget(self) -> bool:
        return sum(self.stage_times.values()) > self.budget.total_budget_ms

    def reset(self):
        self.stage_times.clear()
        self.roi_budgets.clear()


class AdaptiveResolutionManager:
    def __init__(self, grid_map: GridMap2D):
        self.grid_map = grid_map
        self.base_resolution = grid_map.resolution
        self.min_resolution = 0.05
        self.max_resolution = 1.0

    def get_roi_resolution(self, roi: ROI, importance: float) -> float:
        """Higher importance -> finer resolution."""
        return self.min_resolution + (self.base_resolution - self.min_resolution) * (1 - importance)

    def get_background_resolution(self, risk_map: np.ndarray, uncertainty_map: np.ndarray) -> float:
        """Coarser resolution for low-risk, low-uncertainty areas."""
        risk_norm = risk_map / (risk_map.max() + 1e-6)
        unc_norm = uncertainty_map / (uncertainty_map.max() + 1e-6)
        importance = 0.7 * risk_norm + 0.3 * unc_norm
        avg_importance = importance.mean()
        return self.base_resolution + (self.max_resolution - self.base_resolution) * (1 - avg_importance)