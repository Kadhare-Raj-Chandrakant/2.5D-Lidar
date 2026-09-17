#!/usr/bin/env python3
"""
Standalone demo of Foveated LiDAR Perception
Runs without ROS2 - uses synthetic data and matplotlib for visualization
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fovea_lidar'))

from fovea_lidar.preprocess import preprocess_points, range_filter, remove_nan_inf, voxel_downsample
from fovea_lidar.grid_map import GridMap2D, GridMapConfig
from fovea_lidar.risk import compute_risk
from fovea_lidar.uncertainty import compute_uncertainty
from fovea_lidar.foveation import compute_foveation_pipeline, ROI
from fovea_lidar.hysteresis import HysteresisManager
from fovea_lidar.fallback import FallbackController
from fovea_lidar.benchmark import benchmark_timer, BenchmarkTimer


def generate_synthetic_pointcloud(num_points=5000, max_range=50.0, frame=0, object_x=10.0, object_speed=2.0):
    """Generate synthetic LiDAR point cloud with ground plane + moving object."""
    np.random.seed(42 + frame)
    
    points = []
    # Ground plane
    for _ in range(num_points):
        r = np.random.uniform(0.5, max_range)
        theta = np.random.uniform(0, 2 * np.pi)
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        z = np.random.normal(0.0, 0.02)
        points.append([x, y, z])
    
    # Moving object (box)
    if frame > 10:
        object_x += object_speed * 0.1
        if object_x > max_range - 5:
            object_x = -max_range + 5
        for _ in range(500):
            x = object_x + np.random.uniform(-1.5, 1.5)
            y = np.random.uniform(-1.5, 1.5)
            z = np.random.uniform(0.0, 2.0)
            points.append([x, y, z])
    
    # Noise
    for _ in range(200):
        r = np.random.uniform(0.5, max_range)
        theta = np.random.uniform(0, 2 * np.pi)
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        z = np.random.uniform(-1.0, 3.0)
        points.append([x, y, z])
    
    return np.array(points, dtype=np.float32), object_x


def demo_pipeline():
    print("=" * 60)
    print("FOVEATED LIDAR PERCEPTION - STANDALONE DEMO")
    print("=" * 60)
    
    # Config
    config = {
        'max_range': 50.0,
        'min_range': 0.5,
        'voxel_size': 0.1,
        'grid_resolution': 0.5,
        'grid_size_x': 80,
        'grid_size_y': 80,
        'grid_origin_x': -20.0,
        'grid_origin_y': -20.0,
        'occupancy_threshold': 1,
        'risk_weight_occupancy': 1.0,
        'risk_weight_elevation_var': 0.5,
        'risk_weight_proximity': 0.3,
        'risk_weight_roughness': 0.2,
        'proximity_falloff': 10.0,
        'uncertainty_base': 1.0,
        'uncertainty_decay': 0.1,
        'foveation_alpha': 0.7,
        'foveation_beta': 0.3,
        'foveation_top_k': 8,
        'roi_min_size': 3,
        'roi_max_size': 15,
        'roi_expansion': 1,
        'hysteresis_frames': 5,
        'hysteresis_threshold': 0.3,
        'fallback_latency_ms': 500,
    }
    
    # Initialize components
    grid_config = GridMapConfig(
        resolution=config['grid_resolution'],
        size_x=config['grid_size_x'],
        size_y=config['grid_size_y'],
        origin_x=config['grid_origin_x'],
        origin_y=config['grid_origin_y'],
        occupancy_threshold=config['occupancy_threshold'],
        coarse_resolution=1.0,
    )
    grid_map = GridMap2D(grid_config)
    hysteresis = HysteresisManager(hysteresis_frames=config['hysteresis_frames'])
    fallback = FallbackController(max_latency_ms=config['fallback_latency_ms'])
    
    prev_rois = []
    frame_id = 0
    object_x = 10.0
    
    # Storage for visualization
    history = {
        'risk_maps': [],
        'uncertainty_maps': [],
        'rois': [],
        'elevations': [],
        'fallback_status': [],
        'frame_times': [],
    }
    
    print("\nRunning pipeline for 100 frames...")
    print("-" * 60)
    
    for frame in range(100):
        frame_start = time.perf_counter()
        fallback.record_frame_start()
        
        # Generate synthetic data
        points, object_x = generate_synthetic_pointcloud(
            num_points=5000, max_range=50.0, frame=frame, object_x=object_x
        )
        
        # Preprocess
        points = preprocess_points(
            points,
            min_range=config['min_range'],
            max_range=config['max_range'],
            voxel_size=config['voxel_size'],
            remove_nan=True,
        )
        
        # Update grid map
        grid_map.update(points)
        
        # Compute risk
        risk = compute_risk(
            grid_map,
            weight_occupancy=config['risk_weight_occupancy'],
            weight_elevation_var=config['risk_weight_elevation_var'],
            weight_proximity=config['risk_weight_proximity'],
            weight_roughness=config['risk_weight_roughness'],
            proximity_falloff=config['proximity_falloff'],
        )
        
        # Compute uncertainty
        uncertainty = compute_uncertainty(
            grid_map,
            base_uncertainty=config['uncertainty_base'],
            decay_rate=config['uncertainty_decay'],
        )
        
        # Foveation pipeline
        prev_rois = compute_foveation_pipeline(
            grid_map, risk, uncertainty, prev_rois, frame_id,
            alpha=config['foveation_alpha'],
            beta=config['foveation_beta'],
            top_k=config['foveation_top_k'],
            threshold=config['hysteresis_threshold'],
            roi_min_size=config['roi_min_size'],
            roi_max_size=config['roi_max_size'],
            roi_expansion=config['roi_expansion'],
            hysteresis_frames=config['hysteresis_frames'],
        )
        
        # Fallback check
        frame_time_ms = (time.perf_counter() - frame_start) * 1000
        fallback.record_frame_end(success=True)
        is_fallback = fallback.is_in_fallback()
        
        # Store for visualization
        if frame % 5 == 0:
            history['risk_maps'].append(risk.copy())
            history['uncertainty_maps'].append(uncertainty.copy())
            history['rois'].append([(r.center_x, r.center_y, r.size_x, r.size_y, r.score) for r in prev_rois])
            history['elevations'].append(grid_map.get_elevation().copy())
            history['fallback_status'].append(is_fallback)
            history['frame_times'].append(frame_time_ms)
        
        frame_id += 1
        
        if frame % 20 == 0:
            print(f"Frame {frame:3d}: pts={len(points):5d} | ROIs={len(prev_rois)} | "
                  f"Risk max={risk.max():.2f} | Unc max={uncertainty.max():.2f} | "
                  f"Time={frame_time_ms:.1f}ms | Fallback={is_fallback}")
    
    print("-" * 60)
    print("Pipeline complete. Generating visualization...")
    benchmark_timer.print_summary()
    
    return history, config, grid_map


def visualize_results(history, config, grid_map):
    """Create matplotlib visualization of the results."""
    fig = plt.figure(figsize=(18, 12))
    
    num_frames = len(history['risk_maps'])
    
    def animate(frame_idx):
        plt.clf()
        
        risk = history['risk_maps'][frame_idx]
        uncertainty = history['uncertainty_maps'][frame_idx]
        rois = history['rois'][frame_idx]
        elevation = history['elevations'][frame_idx]
        fallback_active = history['fallback_status'][frame_idx]
        frame_time = history['frame_times'][frame_idx]
        
        # 1. Risk Map
        ax1 = plt.subplot(2, 3, 1)
        im1 = ax1.imshow(risk, origin='lower', cmap='hot', vmin=0, vmax=risk.max() if risk.max() > 0 else 1,
                         extent=[-20, 20, -20, 20], aspect='equal')
        ax1.set_title(f'Risk Map (Frame {frame_idx*5})')
        ax1.set_xlabel('X (m)')
        ax1.set_ylabel('Y (m)')
        plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
        
        # Draw ROIs
        for rx, ry, rsx, rsy, score in rois:
            res = config['grid_resolution']
            rect = Rectangle((rx - rsx*res/2, ry - rsy*res/2), rsx*res, rsy*res,
                           linewidth=2, edgecolor='cyan', facecolor='none')
            ax1.add_patch(rect)
            ax1.text(rx, ry, f'{score:.2f}', color='cyan', fontsize=8, ha='center', va='center')
        
        # 2. Uncertainty Map
        ax2 = plt.subplot(2, 3, 2)
        im2 = ax2.imshow(uncertainty, origin='lower', cmap='Blues', vmin=0, vmax=1.0,
                         extent=[-20, 20, -20, 20], aspect='equal')
        ax2.set_title('Uncertainty Map')
        ax2.set_xlabel('X (m)')
        ax2.set_ylabel('Y (m)')
        plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
        
        # 3. Elevation Map
        ax3 = plt.subplot(2, 3, 3)
        im3 = ax3.imshow(np.nan_to_num(elevation, nan=-2), origin='lower', cmap='terrain',
                         vmin=-2, vmax=3, extent=[-20, 20, -20, 20], aspect='equal')
        ax3.set_title('Elevation Map')
        ax3.set_xlabel('X (m)')
        ax3.set_ylabel('Y (m)')
        plt.colorbar(im3, ax=ax3, fraction=0.046, pad=0.04)
        
        # 4. Foveation Score (Risk + Uncertainty)
        ax4 = plt.subplot(2, 3, 4)
        risk_norm = risk / (risk.max() + 1e-6) if risk.max() > 0 else risk
        unc_norm = uncertainty / (uncertainty.max() + 1e-6) if uncertainty.max() > 0 else uncertainty
        foveation_score = config['foveation_alpha'] * risk_norm + config['foveation_beta'] * unc_norm
        im4 = ax4.imshow(foveation_score, origin='lower', cmap='viridis', vmin=0, vmax=1,
                         extent=[-20, 20, -20, 20], aspect='equal')
        ax4.set_title('Foveation Score (α·Risk + β·Uncertainty)')
        ax4.set_xlabel('X (m)')
        ax4.set_ylabel('Y (m)')
        plt.colorbar(im4, ax=ax4, fraction=0.046, pad=0.04)
        
        for rx, ry, rsx, rsy, score in rois:
            res = config['grid_resolution']
            rect = Rectangle((rx - rsx*res/2, ry - rsy*res/2), rsx*res, rsy*res,
                           linewidth=2, edgecolor='red', facecolor='none')
            ax4.add_patch(rect)
        
        # 5. Occupancy Grid
        ax5 = plt.subplot(2, 3, 5)
        occupancy = grid_map.get_occupancy()
        im5 = ax5.imshow(occupancy, origin='lower', cmap='gray_r', vmin=0, vmax=1,
                         extent=[-20, 20, -20, 20], aspect='equal')
        ax5.set_title('Occupancy Grid')
        ax5.set_xlabel('X (m)')
        ax5.set_ylabel('Y (m)')
        
        for rx, ry, rsx, rsy, score in rois:
            res = config['grid_resolution']
            rect = Rectangle((rx - rsx*res/2, ry - rsy*res/2), rsx*res, rsy*res,
                           linewidth=2, edgecolor='lime', facecolor='none')
            ax5.add_patch(rect)
        
        # 6. Stats Panel
        ax6 = plt.subplot(2, 3, 6)
        ax6.axis('off')
        stats_text = f"""
FRAME STATISTICS
{'='*30}
Frame: {frame_idx * 5}
Frame Time: {frame_time:.2f} ms
Fallback Active: {'YES [ALERT]' if fallback_active else 'NO [OK]'}
Active ROIs: {len(rois)}

RISK STATS
Max: {risk.max():.3f}
Mean: {risk.mean():.3f}
Occupied Cells: {np.sum(risk > 0.1)}

UNCERTAINTY STATS
Max: {uncertainty.max():.3f}
Mean: {uncertainty.mean():.3f}

FOVEATION
α (Risk): {config['foveation_alpha']}
β (Uncertainty): {config['foveation_beta']}
Top-K ROIs: {config['foveation_top_k']}
Hysteresis: {config['hysteresis_frames']} frames
"""
        ax6.text(0.05, 0.95, stats_text, transform=ax6.transAxes, fontsize=9,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
    
    anim = animation.FuncAnimation(fig, animate, frames=num_frames, interval=500, repeat=True)
    
    # Save animation
    print("Saving animation to fovea_demo.gif...")
    anim.save('fovea_demo.gif', writer='pillow', fps=2)
    print("Done! Open fovea_demo.gif to see the visualization.")
    
    # Also save a static summary figure
    fig2, axes = plt.subplots(2, 3, figsize=(18, 10))
    frame_idx = num_frames // 2
    
    risk = history['risk_maps'][frame_idx]
    uncertainty = history['uncertainty_maps'][frame_idx]
    rois = history['rois'][frame_idx]
    elevation = history['elevations'][frame_idx]
    
    axes[0,0].imshow(risk, origin='lower', cmap='hot', extent=[-20,20,-20,20])
    axes[0,0].set_title('Risk Map')
    
    axes[0,1].imshow(uncertainty, origin='lower', cmap='Blues', vmin=0, vmax=1, extent=[-20,20,-20,20])
    axes[0,1].set_title('Uncertainty Map')
    
    axes[0,2].imshow(np.nan_to_num(elevation, nan=-2), origin='lower', cmap='terrain', vmin=-2, vmax=3, extent=[-20,20,-20,20])
    axes[0,2].set_title('Elevation Map')
    
    foveation_score = config['foveation_alpha'] * (risk/(risk.max()+1e-6)) + config['foveation_beta'] * (uncertainty/(uncertainty.max()+1e-6))
    axes[1,0].imshow(foveation_score, origin='lower', cmap='viridis', vmin=0, vmax=1, extent=[-20,20,-20,20])
    axes[1,0].set_title('Foveation Score')
    for rx, ry, rsx, rsy, score in rois:
        res = config['grid_resolution']
        rect = Rectangle((rx - rsx*res/2, ry - rsy*res/2), rsx*res, rsy*res, linewidth=2, edgecolor='red', facecolor='none')
        axes[1,0].add_patch(rect)
    
    axes[1,1].imshow(grid_map.get_occupancy(), origin='lower', cmap='gray_r', extent=[-20,20,-20,20])
    axes[1,1].set_title('Occupancy Grid')
    
    axes[1,2].axis('off')
    axes[1,2].text(0.1, 0.5, f"Demo Complete!\n\nFrames: {num_frames}\nAvg Frame Time: {np.mean(history['frame_times']):.1f}ms\nROIs Tracked: {len(rois)}", fontsize=14)
    
    plt.tight_layout()
    plt.savefig('fovea_summary.png', dpi=150)
    print("Saved summary to fovea_summary.png")
    
    return anim


if __name__ == '__main__':
    print("Starting Foveated LiDAR Demo...\n")
    history, config, grid_map = demo_pipeline()
    
    try:
        visualize_results(history, config, grid_map)
        print("\n[OK] Demo completed successfully!")
        print("Output files:")
        print("  - fovea_demo.gif (animation)")
        print("  - fovea_summary.png (static summary)")
    except Exception as e:
        print(f"\nVisualization error (matplotlib may not be available): {e}")
        print("Pipeline ran successfully - check console output above.")
        print("\nTo install matplotlib: pip install matplotlib pillow")