#!/usr/bin/env python3
"""
Foveated LiDAR Perception - Headless Demo Generator
Generates high-quality animation showcasing all features
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fovea_lidar'))

from fovea_lidar.preprocess import preprocess_points
from fovea_lidar.grid_map import GridMap2D, GridMapConfig
from fovea_lidar.risk import compute_risk
from fovea_lidar.uncertainty import compute_uncertainty
from fovea_lidar.foveation import compute_foveation_pipeline, ROI
from fovea_lidar.hysteresis import HysteresisManager
from fovea_lidar.fallback import FallbackController
from fovea_lidar.benchmark import benchmark_timer
from fovea_lidar.dynamic_objects import DynamicObjectTracker, compute_dynamic_risk
from fovea_lidar.compute_allocator import ComputeAllocator, ComputeBudget
from fovea_lidar.spectral_viz import GridSpace2D, SpectralConfig, create_professional_2d_view


def generate_scenario(frame: int, num_frames: int = 120) -> np.ndarray:
    """Generate realistic multi-object scenario with Offroad-Nav inspired terrain."""
    np.random.seed(42 + frame)
    points = []

    # Base ground: multi-scale hills (Offroad-Nav hard-stage style)
    for _ in range(3000):
        r = np.random.uniform(0.5, 40.0)
        theta = np.random.uniform(0, 2 * np.pi)
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        z = (0.30 * np.sin(x * 0.15) * np.cos(y * 0.15) +
             0.10 * np.sin(x * 0.50) * np.cos(y * 0.50) +
             0.02 * np.sin(x * 2.00) * np.cos(y * 2.00) +
             np.random.normal(0.0, 0.03))
        points.append([x, y, z])

    # Rock clusters (Offroad-Nav medium-stage style)
    for cx, cy, n_rocks in [(-12, -12, 8), (-12, 12, 6), (12, -12, 5),
                            (12, 12, 7), (-5, 5, 4), (5, -5, 4)]:
        for _ in range(n_rocks * 50):
            points.append([cx + np.random.uniform(-3.0, 3.0),
                           cy + np.random.uniform(-3.0, 3.0),
                           np.random.uniform(0.1, 1.5)])

    # Tree clusters: trunk + canopy
    for cx, cy, n_trees in [(-18, -18, 4), (-18, 18, 3), (18, -18, 3),
                            (18, 18, 4), (-8, 8, 2), (8, -8, 2)]:
        for _ in range(n_trees * 80):
            x = cx + np.random.uniform(-2.5, 2.5)
            y = cy + np.random.uniform(-2.5, 2.5)
            z = np.random.uniform(0.0, 0.5) if np.random.random() < 0.2 else np.random.uniform(2.0, 5.0)
            points.append([x, y, z])

    # Ditches / trenches (negative elevation)
    for x1, y1, x2, y2 in [(-10, -10, -10, 10), (10, -10, 10, 10)]:
        for _ in range(300):
            points.append([np.random.uniform(min(x1, x2) - 0.5, max(x1, x2) + 0.5),
                           np.random.uniform(min(y1, y2) - 0.5, max(y1, y2) + 0.5),
                           np.random.uniform(-1.5, -0.3)])

    # Grass patches (dense low returns)
    for cx, cy in [(-15, 5), (15, -5), (0, -8)]:
        for _ in range(200):
            points.append([cx + np.random.uniform(-3.0, 3.0),
                           cy + np.random.uniform(-3.0, 3.0),
                           np.random.uniform(0.05, 0.3)])
    
    # Moving vehicles (3 cars)
    for i in range(3):
        phase = i * 2 * np.pi / 3
        t = frame * 0.08
        # Car 1: circular path
        if i == 0:
            cx = 12 * np.cos(t + phase)
            cy = 8 * np.sin(t + phase)
        # Car 2: figure-8
        elif i == 1:
            cx = 10 * np.sin(t * 0.7)
            cy = 6 * np.sin(t * 1.4)
        # Car 3: straight line crossing
        else:
            cx = -15 + t * 2.5
            cy = 5 * np.sin(t * 0.5)
        
        # Vehicle bounding box points
        for _ in range(250):
            x = cx + np.random.uniform(-1.2, 1.2)
            y = cy + np.random.uniform(-0.8, 0.8)
            z = np.random.uniform(0.0, 1.6)
            points.append([x, y, z])
    
    # Pedestrians (2)
    for i in range(2):
        phase = i * np.pi
        cx = 3 * np.cos(frame * 0.15 + phase)
        cy = -10 + frame * 0.3
        for _ in range(80):
            x = cx + np.random.uniform(-0.3, 0.3)
            y = cy + np.random.uniform(-0.3, 0.3)
            z = np.random.uniform(0.0, 1.8)
            points.append([x, y, z])
    
    # Static obstacles (buildings, poles)
    static_obs = [(-15, -15), (15, -15), (-18, 10), (18, 10), (0, 18), (-8, 5), (8, -5)]
    for ox, oy in static_obs:
        for _ in range(150):
            x = ox + np.random.uniform(-1.0, 1.0)
            y = oy + np.random.uniform(-1.0, 1.0)
            z = np.random.uniform(0.0, 3.0)
            points.append([x, y, z])
    
    # Sensor noise
    for _ in range(200):
        r = np.random.uniform(0.5, 40.0)
        theta = np.random.uniform(0, 2 * np.pi)
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        z = np.random.uniform(-0.5, 4.0)
        points.append([x, y, z])
    
    return np.array(points, dtype=np.float32)


def create_animation():
    print("=" * 60)
    print("FOVEATED LIDAR PERCEPTION - DEMO GENERATOR")
    print("=" * 60)
    
    # Config
    config = {
        'max_range': 40.0, 'min_range': 0.5, 'voxel_size': 0.1,
        'grid_resolution': 0.4, 'grid_size_x': 100, 'grid_size_y': 100,
        'grid_origin_x': -20.0, 'grid_origin_y': -20.0,
        'occupancy_threshold': 1,
        'risk_weight_occupancy': 1.0, 'risk_weight_elevation_var': 0.5,
        'risk_weight_proximity': 0.3, 'risk_weight_roughness': 0.2,
        'proximity_falloff': 10.0,
        'uncertainty_base': 1.0, 'uncertainty_decay': 0.1,
        'foveation_alpha': 0.7, 'foveation_beta': 0.3,
        'foveation_top_k': 8, 'roi_min_size': 3, 'roi_max_size': 15,
        'roi_expansion': 1, 'hysteresis_frames': 5,
        'hysteresis_threshold': 0.3, 'fallback_latency_ms': 200,
    }
    
    # Initialize
    grid_config = GridMapConfig(
        resolution=config['grid_resolution'],
        size_x=config['grid_size_x'], size_y=config['grid_size_y'],
        origin_x=config['grid_origin_x'], origin_y=config['grid_origin_y'],
        occupancy_threshold=config['occupancy_threshold'],
        coarse_resolution=1.0,
    )
    grid_map = GridMap2D(grid_config)
    hysteresis = HysteresisManager(hysteresis_frames=config['hysteresis_frames'])
    fallback = FallbackController(max_latency_ms=config['fallback_latency_ms'])
    
    budget = ComputeBudget(total_budget_ms=config['fallback_latency_ms'])
    allocator = ComputeAllocator(budget)
    
    tracker = DynamicObjectTracker(
        cluster_eps=1.2, cluster_min_samples=15,
        max_association_dist=3.0, dt=0.1,
    )
    
    prev_rois = []
    
    # Storage for animation frames
    frames_data = []
    num_frames = 100
    
    print(f"\nProcessing {num_frames} frames...")
    
    for frame in range(num_frames):
        frame_start = time.perf_counter()
        fallback.record_frame_start()
        
        # Generate & process
        points = generate_scenario(frame)
        points = preprocess_points(points, config['min_range'], config['max_range'], 
                                   config['voxel_size'], True)
        grid_map.update(points)
        
        objects = tracker.update(points)
        
        static_risk = compute_risk(grid_map, config['risk_weight_occupancy'],
            config['risk_weight_elevation_var'], config['risk_weight_proximity'],
            config['risk_weight_roughness'], config['proximity_falloff'])
        
        dynamic_risk = compute_dynamic_risk(grid_map, objects)
        risk = np.maximum(static_risk, dynamic_risk)
        
        uncertainty = compute_uncertainty(grid_map, config['uncertainty_base'], config['uncertainty_decay'])
        
        prev_rois = compute_foveation_pipeline(grid_map, risk, uncertainty, prev_rois, frame,
            config['foveation_alpha'], config['foveation_beta'], config['foveation_top_k'],
            config['hysteresis_threshold'], config['roi_min_size'], config['roi_max_size'],
            config['roi_expansion'], config['hysteresis_frames'])
        
        allocator.allocate_roi_budgets(prev_rois, risk, uncertainty, grid_map)
        
        frame_time = (time.perf_counter() - frame_start) * 1000
        fallback.record_frame_end(True)
        is_fallback = fallback.is_in_fallback()
        
        # Store frame data
        # Create spectral layers (lidar_viewer style)
        spectral_config = SpectralConfig(color_map='spectral', min_max_percentile=(2.0, 98.0))
        spectral_layers = create_professional_2d_view(grid_map, points, config['grid_resolution'])
        
        frames_data.append({
            'frame': frame, 'points': points, 'risk': risk, 'uncertainty': uncertainty,
            'objects': objects, 'rois': prev_rois, 'fallback': is_fallback,
            'frame_time': frame_time, 'budget': allocator.get_budget_status(),
            'elevation': grid_map.get_elevation().copy(),
            'occupancy': grid_map.get_occupancy().copy(),
            'spectral_layers': spectral_layers,
        })
        
        if frame % 20 == 0:
            print(f"  Frame {frame:3d}: {len(points)} pts, {len(objects)} objects, {len(prev_rois)} ROIs, {frame_time:.1f}ms")
    
    print("\nGenerating animation...")
    
    # Create figure
    fig = plt.figure(figsize=(22, 14))
    fig.suptitle('Foveated LiDAR Perception System - Technical Demo', fontsize=18, fontweight='bold', y=0.98)
    
    gs = fig.add_gridspec(4, 5, hspace=0.32, wspace=0.22, height_ratios=[1, 1, 1, 0.8])
    
    # Axes
    axes = {}
    extent = [-20, 20, -20, 20]
    res = config['grid_resolution']
    
    map_configs = [
        ('risk', 'Risk Map (Static + Dynamic)', 'hot', (0, 5)),
        ('uncertainty', 'Uncertainty Map', 'Blues', (0, 1.5)),
        ('elevation', 'Elevation Map', 'terrain', (-2, 3)),
        ('foveation', 'Foveation Score (αR + βU)', 'viridis', (0, 1)),
        ('occupancy', 'Occupancy Grid', 'gray_r', (0, 1)),
        ('dynamic', 'Dynamic Objects + Safety Halos', 'plasma', None),
    ]
    
    for idx, (key, title, cmap, vrange) in enumerate(map_configs):
        row = idx // 3
        col = idx % 3
        axes[key] = fig.add_subplot(gs[row, col])
        axes[key].set_xlim(-20, 20)
        axes[key].set_ylim(-20, 20)
        axes[key].set_aspect('equal')
        axes[key].set_title(title, fontsize=11, fontweight='bold')
        axes[key].set_xlabel('X (m)')
        axes[key].set_ylabel('Y (m)')
        axes[key].grid(True, alpha=0.3)
    
    # Spectral layers (lidar_viewer style) - Row 1, Col 3
    axes['spectral_max'] = fig.add_subplot(gs[1, 3])
    axes['spectral_max'].set_xlim(-20, 20)
    axes['spectral_max'].set_ylim(-20, 20)
    axes['spectral_max'].set_aspect('equal')
    axes['spectral_max'].set_title('Max Height (Spectral)', fontsize=10, fontweight='bold')
    axes['spectral_max'].set_xlabel('X (m)')
    axes['spectral_max'].set_ylabel('Y (m)')
    
    axes['spectral_avg'] = fig.add_subplot(gs[2, 3])
    axes['spectral_avg'].set_xlim(-20, 20)
    axes['spectral_avg'].set_ylim(-20, 20)
    axes['spectral_avg'].set_aspect('equal')
    axes['spectral_avg'].set_title('Avg Height (Spectral)', fontsize=10, fontweight='bold')
    axes['spectral_avg'].set_xlabel('X (m)')
    axes['spectral_avg'].set_ylabel('Y (m)')
    
    # ROI detail panel
    axes['roi_detail'] = fig.add_subplot(gs[0, 3])
    axes['roi_detail'].axis('off')
    axes['roi_detail'].set_title('ROI Compute Allocation', fontsize=11, fontweight='bold')
    
    # Budget panel
    axes['budget'] = fig.add_subplot(gs[0, 4])
    axes['budget'].axis('off')
    axes['budget'].set_title('Compute Budget Monitor', fontsize=11, fontweight='bold')
    
    # Performance plots
    axes['perf'] = fig.add_subplot(gs[3, 0])
    axes['perf'].set_title('Frame Time (ms)', fontsize=10)
    axes['perf'].set_ylabel('ms'); axes['perf'].set_xlabel('Frame')
    axes['perf'].grid(True, alpha=0.3)
    
    axes['roi_hist'] = fig.add_subplot(gs[3, 1])
    axes['roi_hist'].set_title('Active ROIs', fontsize=10)
    axes['roi_hist'].set_ylabel('count'); axes['roi_hist'].set_xlabel('Frame')
    axes['roi_hist'].grid(True, alpha=0.3)
    
    axes['risk_hist'] = fig.add_subplot(gs[3, 2])
    axes['risk_hist'].set_title('Max Risk Score', fontsize=10)
    axes['risk_hist'].set_ylabel('score'); axes['risk_hist'].set_xlabel('Frame')
    axes['risk_hist'].grid(True, alpha=0.3)
    
    # Budget utilization
    axes['budget_hist'] = fig.add_subplot(gs[3, 3])
    axes['budget_hist'].set_title('Budget Utilization', fontsize=10)
    axes['budget_hist'].set_ylabel('%'); axes['budget_hist'].set_xlabel('Frame')
    axes['budget_hist'].grid(True, alpha=0.3)
    axes['budget_hist'].axhline(y=90, color='r', linestyle='--', alpha=0.5)
    
    # Status panel
    axes['status'] = fig.add_subplot(gs[:, 4])
    axes['status'].axis('off')
    axes['status'].set_title('System Status & Innovation Highlights', fontsize=11, fontweight='bold')
    
    # Animation function
    frame_times = []
    roi_counts = []
    risk_max = []
    budget_utils = []
    
    def animate(idx):
        data = frames_data[idx]
        risk = data['risk']
        uncertainty = data['uncertainty']
        objects = data['objects']
        rois = data['rois']
        fallback = data['fallback']
        frame_time = data['frame_time']
        budget = data['budget']
        
        frame_times.append(frame_time)
        roi_counts.append(len(rois))
        risk_max.append(risk.max())
        budget_utils.append(budget['utilization'] * 100)
        
        # Risk map
        axes['risk'].clear()
        im = axes['risk'].imshow(risk, origin='lower', cmap='hot', vmin=0, vmax=5, extent=extent, aspect='equal')
        axes['risk'].set_title('Risk Map (Static + Dynamic)', fontweight='bold')
        axes['risk'].set_xlabel('X (m)'); axes['risk'].set_ylabel('Y (m)')
        
        # Uncertainty
        axes['uncertainty'].clear()
        axes['uncertainty'].imshow(uncertainty, origin='lower', cmap='Blues', vmin=0, vmax=1.5, extent=extent, aspect='equal')
        axes['uncertainty'].set_title('Uncertainty Map', fontweight='bold')
        
        # Elevation
        axes['elevation'].clear()
        elev = data['elevation']
        axes['elevation'].imshow(np.nan_to_num(elev, nan=-2), origin='lower', cmap='terrain', vmin=-2, vmax=3, extent=extent, aspect='equal')
        axes['elevation'].set_title('Elevation Map', fontweight='bold')
        
        # Foveation
        axes['foveation'].clear()
        risk_norm = risk / (risk.max() + 1e-6)
        unc_norm = uncertainty / (uncertainty.max() + 1e-6)
        fov = config['foveation_alpha'] * risk_norm + config['foveation_beta'] * unc_norm
        axes['foveation'].imshow(fov, origin='lower', cmap='viridis', vmin=0, vmax=1, extent=extent, aspect='equal')
        axes['foveation'].set_title('Foveation Score (αR + βU)', fontweight='bold')
        
        # Occupancy
        axes['occupancy'].clear()
        axes['occupancy'].imshow(data['occupancy'], origin='lower', cmap='gray_r', vmin=0, vmax=1, extent=extent, aspect='equal')
        axes['occupancy'].set_title('Occupancy Grid', fontweight='bold')
        
        # Dynamic objects
        axes['dynamic'].clear()
        axes['dynamic'].set_xlim(-20, 20); axes['dynamic'].set_ylim(-20, 20); axes['dynamic'].set_aspect('equal')
        axes['dynamic'].set_title('Dynamic Objects + Safety Halos', fontweight='bold')
        axes['dynamic'].grid(True, alpha=0.3)
        
        colors = [(1,0,0), (0,1,0), (0,0,1), (1,1,0), (1,0,1)]
        for j, obj in enumerate(objects):
            color = colors[j % len(colors)]
            # Center
            axes['dynamic'].plot(obj.center[0], obj.center[1], 'o', color=color, markersize=12, 
                               markeredgecolor='white', markeredgewidth=2)
            # Velocity arrow
            axes['dynamic'].arrow(obj.center[0], obj.center[1], obj.velocity[0]*3, obj.velocity[1]*3,
                                head_width=0.6, head_length=0.6, fc=color, ec='white', linewidth=2.5)
            # Safety halo
            halo_r = obj.get_halo_radius()
            circle = Circle((obj.center[0], obj.center[1]), halo_r, fill=False, 
                          edgecolor=color, linestyle='--', linewidth=2.5, alpha=0.7)
            axes['dynamic'].add_patch(circle)
            # Predicted trajectory
            for t in np.linspace(0.2, 2.5, 6):
                pred = obj.predict(t)
                axes['dynamic'].plot(pred[0], pred[1], 'x', color=color, alpha=0.4, markersize=8)
            # Label
            axes['dynamic'].text(obj.center[0], obj.center[1] + 1.8, f'ID:{obj.id} v={np.linalg.norm(obj.velocity[:2]):.1f}m/s',
                               color='white', fontsize=9, ha='center', fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.9))
        
        # Draw ROIs on map panels
        for ax_key in ['risk', 'foveation', 'occupancy', 'dynamic']:
            ax = axes[ax_key]
            for roi in rois:
                rect = Rectangle(
                    (roi.center_x - roi.size_x * res / 2, roi.center_y - roi.size_y * res / 2),
                    roi.size_x * res, roi.size_y * res,
                    linewidth=2.5, edgecolor='cyan', facecolor='none', alpha=0.9
                )
                ax.add_patch(rect)
                ax.text(roi.center_x, roi.center_y, f'{roi.score:.2f}', 
                       color='cyan', fontsize=9, ha='center', va='center', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.7))
        
        # Spectral layers (lidar_viewer style) - display spectral max/avg height
        spectral = data.get('spectral_layers', {})
        if 'max_height' in spectral:
            axes['spectral_max'].clear()
            axes['spectral_max'].imshow(spectral['max_height'], origin='lower', extent=extent, aspect='equal')
            axes['spectral_max'].set_title('Max Height (Spectral)', fontweight='bold')
            axes['spectral_max'].set_xlabel('X (m)'); axes['spectral_max'].set_ylabel('Y (m)')
            # Draw ROIs on spectral
            for roi in rois:
                rect = Rectangle(
                    (roi.center_x - roi.size_x * res / 2, roi.center_y - roi.size_y * res / 2),
                    roi.size_x * res, roi.size_y * res,
                    linewidth=2, edgecolor='white', facecolor='none', alpha=0.8
                )
                axes['spectral_max'].add_patch(rect)
        
        if 'avg_height' in spectral:
            axes['spectral_avg'].clear()
            axes['spectral_avg'].imshow(spectral['avg_height'], origin='lower', extent=extent, aspect='equal')
            axes['spectral_avg'].set_title('Avg Height (Spectral)', fontweight='bold')
            axes['spectral_avg'].set_xlabel('X (m)'); axes['spectral_avg'].set_ylabel('Y (m)')
            for roi in rois:
                rect = Rectangle(
                    (roi.center_x - roi.size_x * res / 2, roi.center_y - roi.size_y * res / 2),
                    roi.size_x * res, roi.size_y * res,
                    linewidth=2, edgecolor='white', facecolor='none', alpha=0.8
                )
                axes['spectral_avg'].add_patch(rect)
        
        # ROI detail
        axes['roi_detail'].clear()
        axes['roi_detail'].axis('off')
        roi_text = "ACTIVE REGIONS OF INTEREST\n" + "="*35 + "\n"
        for i, roi in enumerate(rois):
            cfg = allocator.get_roi_processing_config(roi, i)
            b = allocator.roi_budgets.get(i, 0)
            roi_text += f"ROI {i}: ({roi.center_x:.1f}, {roi.center_y:.1f})  Score: {roi.score:.3f}\n"
            roi_text += f"  Size: {roi.size_x}×{roi.size_y} cells  Budget: {b:.1f}ms\n"
            roi_text += f"  Voxel: {cfg['voxel_size']:.3f}m  MaxPts: {cfg['max_points']}\n"
            roi_text += f"  Normals: {cfg['use_normals']}  Classify: {cfg['use_classification']}\n\n"
        if not rois:
            roi_text += "No active ROIs\n"
        axes['roi_detail'].text(0.02, 0.98, roi_text, transform=axes['roi_detail'].transAxes,
                               fontsize=7.5, va='top', fontfamily='monospace',
                               bbox=dict(boxstyle='round', facecolor='#f5f5f5', alpha=0.95))
        
        # Budget
        axes['budget'].clear()
        axes['budget'].axis('off')
        budget_text = "COMPUTE BUDGET MONITOR\n" + "="*35 + "\n"
        budget_text += f"Total Budget: {budget['total_budget_ms']:.0f} ms\n"
        budget_text += f"Used: {budget['used_ms']:.1f} ms ({budget['utilization']*100:.1f}%)\n"
        budget_text += f"Remaining: {budget['remaining_ms']:.1f} ms\n\n"
        budget_text += "Stage Times:\n"
        for stage, t in budget['stage_times'].items():
            budget_text += f"  {stage:<25s} {t:>6.1f} ms\n"
        budget_text += "\nROI Allocations:\n"
        for rid, b in budget['roi_budgets'].items():
            budget_text += f"  ROI {rid}: {b:.1f} ms\n"
        if budget['utilization'] > 0.9:
            budget_text += "\n⚠ OVER BUDGET - Fallback Risk!"
        axes['budget'].text(0.02, 0.98, budget_text, transform=axes['budget'].transAxes,
                           fontsize=7.5, va='top', fontfamily='monospace',
                           bbox=dict(boxstyle='round', facecolor='#fff3e0' if budget['utilization']>0.9 else '#e8f5e9', alpha=0.95))
        
        # Performance plots
        axes['perf'].clear()
        axes['perf'].plot(frame_times, 'g-', linewidth=1.5)
        axes['perf'].axhline(y=config['fallback_latency_ms'], color='r', linestyle='--', alpha=0.7, label='Fallback Threshold')
        axes['perf'].set_title('Frame Time (ms)', fontsize=10)
        axes['perf'].set_ylabel('ms'); axes['perf'].set_xlabel('Frame')
        axes['perf'].grid(True, alpha=0.3)
        axes['perf'].legend(fontsize=8)
        
        axes['roi_hist'].clear()
        axes['roi_hist'].plot(roi_counts, 'b-', linewidth=1.5)
        axes['roi_hist'].set_title('Active ROIs', fontsize=10)
        axes['roi_hist'].set_ylabel('count'); axes['roi_hist'].set_xlabel('Frame')
        axes['roi_hist'].grid(True, alpha=0.3)
        
        axes['risk_hist'].clear()
        axes['risk_hist'].plot(risk_max, 'r-', linewidth=1.5)
        axes['risk_hist'].set_title('Max Risk Score', fontsize=10)
        axes['risk_hist'].set_ylabel('score'); axes['risk_hist'].set_xlabel('Frame')
        axes['risk_hist'].grid(True, alpha=0.3)
        
        axes['budget_hist'].clear()
        axes['budget_hist'].plot(budget_utils, 'orange', linewidth=1.5)
        axes['budget_hist'].axhline(y=90, color='r', linestyle='--', alpha=0.5)
        axes['budget_hist'].set_title('Budget Utilization %', fontsize=10)
        axes['budget_hist'].set_ylabel('%'); axes['budget_hist'].set_xlabel('Frame')
        axes['budget_hist'].grid(True, alpha=0.3)
        axes['budget_hist'].set_ylim(0, 110)
        
        # Status panel
        axes['status'].clear()
        axes['status'].axis('off')
        status_text = f"""
SYSTEM STATUS
{'='*40}
Frame: {data['frame']} / {num_frames}
Frame Time: {frame_time:.1f} ms ({(1000/frame_time):.1f} FPS)
Fallback: {'ACTIVE [ALERT]' if fallback else 'Normal [OK]'}
Active ROIs: {len(rois)}
Dynamic Objects: {len(objects)}
Budget: {budget['utilization']*100:.1f}%

INNOVATION FEATURES
{'='*40}
[1] Foveated LiDAR (Smart Focus)
    Adaptive ROIs: {len(rois)} regions
    Resolution: {config['grid_resolution']}m base → {min(cfg['voxel_size'] for cfg in [allocator.get_roi_processing_config(r, i) for i,r in enumerate(rois)]) if rois else config['grid_resolution']:.3f}m in ROIs

[2] Risk-Aware Foveation (Danger Focus)
    α (Risk weight): {config['foveation_alpha']:.1f}
    β (Uncertainty): {config['foveation_beta']:.1f}
    Focuses on: Occupancy + Roughness + Proximity

[3] Uncertainty-Aware (Curiosity Focus)
    Uncertainty drives focus to blind spots
    Decay rate: {config['uncertainty_decay']}

[4] Global Safety Path (Backup)
    Coarse map: 1.0m resolution always updated
    Fallback threshold: {config['fallback_latency_ms']} ms
    Status: {'TRIGGERED' if fallback else 'STANDBY'}

[5] Hysteresis (Anti-Flicker)
    Persistence: {config['hysteresis_frames']} frames
    Prevents ROI thrashing

DYNAMIC OBJECTS
{'='*40}
"""
        for obj in objects:
            status_text += f"  ID{obj.id}: pos=({obj.center[0]:.1f},{obj.center[1]:.1f}) vel=({obj.velocity[0]:.1f},{obj.velocity[1]:.1f}) halo={obj.get_halo_radius():.1f}m\n"
        
        status_text += f"""

COMPUTE ALLOCATION
{'='*40}
Budget-aware processing per ROI
Higher risk/uncertainty → More compute
Fallback protects real-time guarantees
"""
        
        axes['status'].text(0.02, 0.98, status_text, transform=axes['status'].transAxes,
                           fontsize=7, va='top', fontfamily='monospace',
                           bbox=dict(boxstyle='round', facecolor='#fbe9e7' if fallback else '#e8f5e9', alpha=0.95))
        
        return []
    
    # Generate animation
    anim = animation.FuncAnimation(fig, animate, frames=num_frames, interval=100, blit=False)
    
    # Save
    print("Saving fovea_hackathon_demo.gif...")
    anim.save('fovea_hackathon_demo.gif', writer='pillow', fps=10, dpi=120)
    
    # Also save key frames as PNGs
    key_frames = [0, 25, 50, 75, 99]
    for kf in key_frames:
        animate(kf)
        plt.savefig(f'fovea_frame_{kf:03d}.png', dpi=150, bbox_inches='tight')
    
    print("Done!")
    print("Outputs:")
    print("  - fovea_hackathon_demo.gif (full animation)")
    print("  - fovea_frame_000.png, 025.png, 050.png, 075.png, 099.png (key frames)")
    benchmark_timer.print_summary()


if __name__ == '__main__':
    create_animation()