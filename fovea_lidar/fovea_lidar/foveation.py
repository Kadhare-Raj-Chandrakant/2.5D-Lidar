import numpy as np
from grid_map import GridMap2D
from benchmark import benchmark_timer
from typing import List, Tuple, Dict
from dataclasses import dataclass


@dataclass
class ROI:
    """Region of Interest for foveated processing."""
    center_x: float
    center_y: float
    size_x: int
    size_y: int
    score: float
    cells: List[Tuple[int, int]]
    frame_created: int
    frame_last_seen: int


def compute_foveation_score(
    risk: np.ndarray,
    uncertainty: np.ndarray,
    alpha: float = 0.7,
    beta: float = 0.3,
) -> np.ndarray:
    """Compute foveation score = alpha * risk + beta * uncertainty."""
    with benchmark_timer.time("foveation_score"):
        risk_norm = risk / (risk.max() + 1e-6) if risk.max() > 0 else risk
        unc_norm = uncertainty / (uncertainty.max() + 1e-6) if uncertainty.max() > 0 else uncertainty
        score = alpha * risk_norm + beta * unc_norm
        return score


def find_peak_cells(score: np.ndarray, top_k: int = 10, threshold: float = 0.3) -> List[Tuple[int, int, float]]:
    """Find top-K peak cells above threshold using non-maximum suppression."""
    flat_indices = np.argsort(score.ravel())[::-1]
    peaks = []
    size_y, size_x = score.shape

    suppressed = np.zeros_like(score, dtype=bool)

    for idx in flat_indices:
        if len(peaks) >= top_k:
            break
        y, x = divmod(idx, size_x)
        if score[y, x] < threshold:
            break
        if suppressed[y, x]:
            continue

        peaks.append((x, y, score[y, x]))

        suppress_radius = 3
        y_min = max(0, y - suppress_radius)
        y_max = min(size_y, y + suppress_radius + 1)
        x_min = max(0, x - suppress_radius)
        x_max = min(size_x, x + suppress_radius + 1)
        suppressed[y_min:y_max, x_min:x_max] = True

    return peaks


def create_rois_from_peaks(
    peaks: List[Tuple[int, int, float]],
    grid_map: GridMap2D,
    roi_min_size: int = 3,
    roi_max_size: int = 15,
    roi_expansion: int = 1,
    current_frame: int = 0,
) -> List[ROI]:
    """Create ROI boxes around peak cells."""
    rois = []

    for gx, gy, score in peaks:
        size = roi_min_size + int(score * (roi_max_size - roi_min_size))
        half = size // 2

        x_min = max(0, gx - half - roi_expansion)
        x_max = min(grid_map.size_x, gx + half + roi_expansion + 1)
        y_min = max(0, gy - half - roi_expansion)
        y_max = min(grid_map.size_y, gy + half + roi_expansion + 1)

        cells = [(x, y) for y in range(y_min, y_max) for x in range(x_min, x_max)]

        cx, cy = grid_map.grid_to_world(gx, gy)

        roi = ROI(
            center_x=cx,
            center_y=cy,
            size_x=x_max - x_min,
            size_y=y_max - y_min,
            score=score,
            cells=cells,
            frame_created=current_frame,
            frame_last_seen=current_frame,
        )
        rois.append(roi)

    return rois


def apply_hysteresis(
    current_rois: List[ROI],
    previous_rois: List[ROI],
    hysteresis_frames: int = 5,
    current_frame: int = 0,
) -> List[ROI]:
    """Keep ROIs alive for hysteresis_frames after they disappear from peaks."""
    merged = []
    matched_prev_indices = set()

    for curr in current_rois:
        matched = False
        for i, prev in enumerate(previous_rois):
            if (abs(curr.center_x - prev.center_x) < 1.0 and
                abs(curr.center_y - prev.center_y) < 1.0):
                curr.frame_created = prev.frame_created
                curr.frame_last_seen = current_frame
                merged.append(curr)
                matched_prev_indices.add(i)
                matched = True
                break
        if not matched:
            curr.frame_created = current_frame
            curr.frame_last_seen = current_frame
            merged.append(curr)

    # Only keep previous ROIs that were NOT matched this frame, and haven't expired
    for i, prev in enumerate(previous_rois):
        if i not in matched_prev_indices:
            if current_frame - prev.frame_last_seen <= hysteresis_frames:
                # Keep but DON'T update frame_last_seen - let it expire naturally
                merged.append(prev)

    return merged


def compute_foveation_pipeline(
    grid_map: GridMap2D,
    risk: np.ndarray,
    uncertainty: np.ndarray,
    prev_rois: List[ROI],
    frame_id: int,
    alpha: float = 0.7,
    beta: float = 0.3,
    top_k: int = 10,
    threshold: float = 0.3,
    roi_min_size: int = 3,
    roi_max_size: int = 15,
    roi_expansion: int = 1,
    hysteresis_frames: int = 5,
) -> List[ROI]:
    """Complete foveation pipeline."""
    score = compute_foveation_score(risk, uncertainty, alpha, beta)
    peaks = find_peak_cells(score, top_k, threshold)
    new_rois = create_rois_from_peaks(peaks, grid_map, roi_min_size, roi_max_size, roi_expansion, frame_id)
    rois = apply_hysteresis(new_rois, prev_rois, hysteresis_frames, frame_id)
    return rois