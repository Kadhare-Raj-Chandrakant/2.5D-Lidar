"""Pre-canned demo scenarios: real LiDAR txt + Offroad-style synthetic."""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fovea_lidar'))

SCENARIOS = {
    'urban': {'desc': 'Medium stage: trees + rocks, flat ground'},
    'offroad': {'desc': 'Hard stage: elevation + tall grass'},
    'highway': {'desc': 'Easy stage: flat + geometric obstacles'},
}


def load_csite_txt(path: str, max_points: int = 20000) -> np.ndarray:
    """Load lidar_viewer CSite*.txt (X Y Z I pairs per line) into Nx3 array."""
    pts = []
    with open(path) as f:
        for line in f:
            vals = line.split()
            # Each line holds two (X Y Z I) records
            for i in range(0, len(vals) - 3, 4):
                try:
                    x, y, z = float(vals[i]), float(vals[i+1]), float(vals[i+2])
                    pts.append([x, y, z])
                    if len(pts) >= max_points:
                        break
                except ValueError:
                    continue
            if len(pts) >= max_points:
                break
    pts = np.array(pts, dtype=np.float32)
    # Recenter to origin for grid map
    pts[:, 0] -= pts[:, 0].mean()
    pts[:, 1] -= pts[:, 1].mean()
    pts[:, 2] -= pts[:, 2].min()
    return pts


def run_real_data_demo(path: str, frames: int = 50):
    from fovea_lidar.preprocess import preprocess_points
    from fovea_lidar.grid_map import GridMap2D, GridMapConfig
    from fovea_lidar.risk import compute_risk
    from fovea_lidar.uncertainty import compute_uncertainty
    from fovea_lidar.foveation import compute_foveation_pipeline

    pts = load_csite_txt(path)
    print(f"Loaded {len(pts)} real LiDAR points from {path}")

    grid = GridMap2D(GridMapConfig(resolution=0.5, size_x=100, size_y=100,
                                   origin_x=-25.0, origin_y=-25.0))
    rois = []
    for f in range(frames):
        chunk = pts[f::frames]  # stream chunks to simulate scans
        chunk = preprocess_points(chunk, 0.5, 60.0, 0.2, True)
        grid.update(chunk)
        risk = compute_risk(grid)
        unc = compute_uncertainty(grid)
        rois = compute_foveation_pipeline(grid, risk, unc, rois, f)
        if f % 10 == 0:
            print(f"  frame {f}: {len(chunk)} pts, {len(rois)} ROIs, risk_max={risk.max():.2f}")
    print(f"Done. Final ROIs: {len(rois)}")
