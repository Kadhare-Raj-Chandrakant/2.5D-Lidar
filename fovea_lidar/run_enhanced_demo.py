#!/usr/bin/env python3
"""
Enhanced Foveated LiDAR Perception - Real-time Interactive Demo
Features:
- Live matplotlib animation window
- Dynamic object detection & tracking
- Predictive foveation with safety halos
- Compute budget allocation
- Web dashboard (Flask + SocketIO)
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle, Circle
from matplotlib.widgets import Button, Slider, CheckButtons
import time
import sys
import os
import threading
import json
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fovea_lidar'))

from fovea_lidar.preprocess import preprocess_points
from fovea_lidar.grid_map import GridMap2D, GridMapConfig
from fovea_lidar.risk import compute_risk
from fovea_lidar.uncertainty import compute_uncertainty
from fovea_lidar.foveation import compute_foveation_pipeline, ROI
from fovea_lidar.hysteresis import HysteresisManager
from fovea_lidar.fallback import FallbackController
from fovea_lidar.benchmark import benchmark_timer, BenchmarkTimer
from fovea_lidar.dynamic_objects import DynamicObjectTracker, DynamicObject, compute_dynamic_risk
from fovea_lidar.compute_allocator import ComputeAllocator, ComputeBudget, AdaptiveResolutionManager


class EnhancedDemo:
    def __init__(self, use_web_dashboard: bool = False):
        self.use_web = use_web_dashboard
        self.running = True
        self.paused = False
        self.frame = 0
        self.object_x = 10.0
        self.object_speed = 3.0
        
        # Config
        self.config = {
            'max_range': 50.0,
            'min_range': 0.5,
            'voxel_size': 0.1,
            'grid_resolution': 0.4,
            'grid_size_x': 100,
            'grid_size_y': 100,
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
        self._init_components()
        
        # History for plots
        self.history_len = 100
        self.frame_times = deque(maxlen=self.history_len)
        self.roi_counts = deque(maxlen=self.history_len)
        self.risk_max = deque(maxlen=self.history_len)
        self.budget_util = deque(maxlen=self.history_len)
        
        # Web dashboard
        if self.use_web:
            self._init_web_dashboard()
        
        # Matplotlib setup
        self._init_plots()
        
    def _init_components(self):
        grid_config = GridMapConfig(
            resolution=self.config['grid_resolution'],
            size_x=self.config['grid_size_x'],
            size_y=self.config['grid_size_y'],
            origin_x=self.config['grid_origin_x'],
            origin_y=self.config['grid_origin_y'],
            occupancy_threshold=self.config['occupancy_threshold'],
            coarse_resolution=1.0,
        )
        self.grid_map = GridMap2D(grid_config)
        self.hysteresis = HysteresisManager(hysteresis_frames=self.config['hysteresis_frames'])
        self.fallback = FallbackController(max_latency_ms=self.config['fallback_latency_ms'])
        
        budget = ComputeBudget(total_budget_ms=self.config['fallback_latency_ms'])
        self.compute_allocator = ComputeAllocator(budget)
        self.resolution_manager = AdaptiveResolutionManager(self.grid_map)
        
        self.tracker = DynamicObjectTracker(
            cluster_eps=1.2,
            cluster_min_samples=15,
            max_association_dist=3.0,
            dt=0.1,
        )
        
        self.prev_rois = []
        
    def _init_plots(self):
        self.fig = plt.figure(figsize=(20, 12))
        self.fig.suptitle('Foveated LiDAR Perception - Real-time Demo', fontsize=16, fontweight='bold')
        
        # Grid layout: 3 rows x 4 cols
        gs = self.fig.add_gridspec(3, 4, hspace=0.35, wspace=0.25)
        
        # Row 0: Main maps
        self.ax_risk = self.fig.add_subplot(gs[0, 0])
        self.ax_uncertainty = self.fig.add_subplot(gs[0, 1])
        self.ax_elevation = self.fig.add_subplot(gs[0, 2])
        self.ax_foveation = self.fig.add_subplot(gs[0, 3])
        
        # Row 1: Occupancy + Dynamic objects + ROI detail + Budget
        self.ax_occupancy = self.fig.add_subplot(gs[1, 0])
        self.ax_dynamic = self.fig.add_subplot(gs[1, 1])
        self.ax_roi_detail = self.fig.add_subplot(gs[1, 2])
        self.ax_budget = self.fig.add_subplot(gs[1, 3])
        
        # Row 2: Time series plots
        self.ax_perf = self.fig.add_subplot(gs[2, 0])
        self.ax_roi_hist = self.fig.add_subplot(gs[2, 1])
        self.ax_risk_hist = self.fig.add_subplot(gs[2, 2])
        self.ax_status = self.fig.add_subplot(gs[2, 3])
        
        self._setup_map_axes()
        self._setup_controls()
        
    def _setup_map_axes(self):
        extent = [-20, 20, -20, 20]
        
        for ax, title, cmap in [
            (self.ax_risk, 'Risk Map', 'hot'),
            (self.ax_uncertainty, 'Uncertainty', 'Blues'),
            (self.ax_elevation, 'Elevation', 'terrain'),
            (self.ax_foveation, 'Foveation Score', 'viridis'),
            (self.ax_occupancy, 'Occupancy Grid', 'gray_r'),
            (self.ax_dynamic, 'Dynamic Objects', 'plasma'),
        ]:
            ax.set_xlim(-20, 20)
            ax.set_ylim(-20, 20)
            ax.set_aspect('equal')
            ax.set_title(title, fontsize=11, fontweight='bold')
            ax.set_xlabel('X (m)')
            ax.set_ylabel('Y (m)')
            ax.grid(True, alpha=0.3)
        
        self.ax_roi_detail.set_title('ROI Detail', fontsize=11, fontweight='bold')
        self.ax_roi_detail.axis('off')
        
        self.ax_budget.set_title('Compute Budget', fontsize=11, fontweight='bold')
        
        # Time series axes
        for ax, title, ylabel in [
            (self.ax_perf, 'Frame Time (ms)', 'ms'),
            (self.ax_roi_hist, 'Active ROIs', 'count'),
            (self.ax_risk_hist, 'Max Risk', 'score'),
        ]:
            ax.set_title(title, fontsize=10)
            ax.set_ylabel(ylabel)
            ax.set_xlabel('Frame')
            ax.grid(True, alpha=0.3)
            ax.set_xlim(0, self.history_len)
        
        self.ax_status.set_title('System Status', fontsize=11, fontweight='bold')
        self.ax_status.axis('off')
        
    def _setup_controls(self):
        # Pause button
        ax_pause = self.fig.add_axes([0.02, 0.02, 0.08, 0.04])
        self.btn_pause = Button(ax_pause, 'Pause')
        self.btn_pause.on_clicked(self._toggle_pause)
        
        # Speed slider
        ax_speed = self.fig.add_axes([0.12, 0.02, 0.2, 0.03])
        self.slider_speed = Slider(ax_speed, 'Obj Speed', 0.5, 8.0, valinit=3.0)
        self.slider_speed.on_changed(self._update_speed)
        
        # Foveation alpha/beta sliders
        ax_alpha = self.fig.add_axes([0.35, 0.02, 0.15, 0.03])
        self.slider_alpha = Slider(ax_alpha, 'α (Risk)', 0.0, 1.0, valinit=0.7)
        self.slider_alpha.on_changed(self._update_alpha)
        
        ax_beta = self.fig.add_axes([0.52, 0.02, 0.15, 0.03])
        self.slider_beta = Slider(ax_beta, 'β (Uncertainty)', 0.0, 1.0, valinit=0.3)
        self.slider_beta.on_changed(self._update_beta)
        
        # Checkboxes for layers
        ax_check = self.fig.add_axes([0.7, 0.01, 0.25, 0.08])
        self.check = CheckButtons(
            ax_check,
            ['Show ROIs', 'Show Halos', 'Show Predictions', 'Fallback'],
            [True, True, True, False]
        )
        self.check.on_clicked(self._toggle_layer)
        
        self.show_rois = True
        self.show_halos = True
        self.show_predictions = True
        self.show_fallback = False
        
    def _toggle_pause(self, event):
        self.paused = not self.paused
        self.btn_pause.label.set_text('Resume' if self.paused else 'Pause')
        
    def _update_speed(self, val):
        self.object_speed = val
        
    def _update_alpha(self, val):
        if getattr(self, '_updating_sliders', False):
            return
        self._updating_sliders = True
        self.config['foveation_alpha'] = val
        total = val + self.config['foveation_beta']
        if total > 0:
            self.config['foveation_beta'] = self.config['foveation_beta'] / total * (1 - val)
            self.slider_beta.set_val(self.config['foveation_beta'])
        self._updating_sliders = False
        
    def _update_beta(self, val):
        if getattr(self, '_updating_sliders', False):
            return
        self._updating_sliders = True
        self.config['foveation_beta'] = val
        total = val + self.config['foveation_alpha']
        if total > 0:
            self.config['foveation_alpha'] = self.config['foveation_alpha'] / total * (1 - val)
            self.slider_alpha.set_val(self.config['foveation_alpha'])
        self._updating_sliders = False
        
    def _toggle_layer(self, label):
        if label == 'Show ROIs':
            self.show_rois = not self.show_rois
        elif label == 'Show Halos':
            self.show_halos = not self.show_halos
        elif label == 'Show Predictions':
            self.show_predictions = not self.show_predictions
        elif label == 'Fallback':
            self.show_fallback = not self.show_fallback
            
    def _init_web_dashboard(self):
        from flask import Flask, render_template_string
        from flask_socketio import SocketIO
        
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        @self.app.route('/')
        def index():
            return self._get_dashboard_html()
        
        @self.socketio.on('connect')
        def handle_connect():
            print('Web client connected')
            
        self.web_thread = threading.Thread(target=self._run_web, daemon=True)
        self.web_thread.start()
        
    def _run_web(self):
        self.socketio.run(self.app, host='0.0.0.0', port=5000, debug=False)
        
    def _get_dashboard_html(self):
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Foveated LiDAR Dashboard</title>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 0; background: #1a1a2e; color: #eee; }
        .header { background: #16213e; padding: 1rem; border-bottom: 2px solid #e94560; }
        .container { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; padding: 1rem; }
        .card { background: #16213e; border-radius: 8px; padding: 1rem; border: 1px solid #0f3460; }
        .card h3 { margin: 0 0 1rem; color: #e94560; }
        .metric { font-size: 2rem; font-weight: bold; color: #00d9a5; }
        .status-ok { color: #00d9a5; }
        .status-warn { color: #ffd60a; }
        .status-error { color: #e94560; }
        #mapPlot, #perfPlot { width: 100%; height: 400px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Foveated LiDAR Perception Dashboard</h1>
    </div>
    <div class="container">
        <div class="card">
            <h3>System Metrics</h3>
            <div>Frame Time: <span id="frameTime" class="metric">--</span> ms</div>
            <div>FPS: <span id="fps" class="metric">--</span></div>
            <div>Active ROIs: <span id="roiCount" class="metric">--</span></div>
            <div>Max Risk: <span id="maxRisk" class="metric">--</span></div>
            <div>Budget: <span id="budget" class="metric">--</span>%</div>
            <div>Status: <span id="status" class="status-ok">RUNNING</span></div>
        </div>
        <div class="card">
            <h3>Dynamic Objects</h3>
            <div id="objects">Waiting for data...</div>
        </div>
        <div class="card">
            <h3>Risk Map</h3>
            <div id="mapPlot"></div>
        </div>
        <div class="card">
            <h3>Performance</h3>
            <div id="perfPlot"></div>
        </div>
    </div>
    <script>
        const socket = io();
        const perfData = {times: [], rois: [], risk: [], budget: []};
        
        socket.on('update', (data) => {
            document.getElementById('frameTime').textContent = data.frame_time.toFixed(1);
            document.getElementById('fps').textContent = (1000/data.frame_time).toFixed(1);
            document.getElementById('roiCount').textContent = data.roi_count;
            document.getElementById('maxRisk').textContent = data.max_risk.toFixed(2);
            document.getElementById('budget').textContent = (data.budget_util * 100).toFixed(1);
            document.getElementById('status').textContent = data.fallback ? 'FALLBACK' : 'RUNNING';
            document.getElementById('status').className = data.fallback ? 'status-error' : 'status-ok';
            
            perfData.times.push(data.frame_time);
            perfData.rois.push(data.roi_count);
            perfData.risk.push(data.max_risk);
            if (perfData.times.length > 100) { perfData.times.shift(); perfData.rois.shift(); perfData.risk.shift(); }
            
            perfData.budget.push(data.budget_util * 100);
            if (perfData.budget.length > 100) { perfData.budget.shift(); }
            Plotly.newPlot('perfPlot', [
                {y: perfData.times, name: 'Frame Time (ms)', line: {color: '#00d9a5'}},
                {y: perfData.rois, name: 'ROIs', yaxis: 'y2', line: {color: '#e94560'}},
                {y: perfData.budget, name: 'Budget %', yaxis: 'y2', line: {color: '#ffd60a', dash: 'dot'}},
            ], {yaxis: {title: 'ms'}, yaxis2: {title: 'ROIs / %', overlaying: 'y', side: 'right', range: [0, 110]}, paper_bgcolor: '#16213e', plot_bgcolor: '#1a1a2e', font: {color: '#eee'}, margin: {t: 20}});
            
            document.getElementById('objects').innerHTML = data.objects.map(o => 
                `<div>ID ${o.id}: pos=(${o.x.toFixed(1)}, ${o.y.toFixed(1)}) vel=(${o.vx.toFixed(1)}, ${o.vy.toFixed(1)}) halo=${o.halo.toFixed(1)}m</div>`
            ).join('');
        });
    </script>
</body>
</html>
"""
        
    def generate_pointcloud(self) -> np.ndarray:
        np.random.seed(42 + self.frame)
        points = []
        
        # Ground plane with elevation variations (Offroad-style multi-scale terrain)
        for _ in range(2200):
            r = np.random.uniform(0.5, self.config['max_range'])
            theta = np.random.uniform(0, 2 * np.pi)
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            # Offroad-style multi-scale terrain: hills + undulations + ripples
            z = (0.30 * np.sin(x * 0.15) * np.cos(y * 0.15) +
                 0.10 * np.sin(x * 0.50) * np.cos(y * 0.50) +
                 0.02 * np.sin(x * 2.00) * np.cos(y * 2.00) +
                 np.random.normal(0.0, 0.03))
            points.append([x, y, z])

        # Rock clusters (Offroad-Nav medium-stage style)
        for cx, cy, n_rocks in [(-12, -12, 5), (12, 12, 5), (-5, 5, 3), (5, -5, 3)]:
            for _ in range(n_rocks * 40):
                points.append([cx + np.random.uniform(-3.0, 3.0),
                               cy + np.random.uniform(-3.0, 3.0),
                               np.random.uniform(0.1, 1.5)])

        # Ditch (negative elevation, hard-stage style)
        for _ in range(200):
            points.append([np.random.uniform(-10.5, 10.5),
                           -10 + np.random.uniform(-0.5, 0.5),
                           np.random.uniform(-1.2, -0.3)])
        
        # Multiple moving objects
        num_objects = 3
        for obj_idx in range(num_objects):
            phase = obj_idx * 2 * np.pi / num_objects
            obj_x = 15 * np.cos(self.frame * 0.05 + phase)
            obj_y = 10 * np.sin(self.frame * 0.05 + phase)
            obj_z = 0.5
            
            for _ in range(300):
                x = obj_x + np.random.uniform(-1.0, 1.0)
                y = obj_y + np.random.uniform(-1.0, 1.0)
                z = obj_z + np.random.uniform(0.0, 1.5)
                points.append([x, y, z])
        
        # Static obstacles
        for _ in range(5):
            ox = np.random.uniform(-15, 15)
            oy = np.random.uniform(-15, 15)
            for _ in range(100):
                x = ox + np.random.uniform(-1.5, 1.5)
                y = oy + np.random.uniform(-1.5, 1.5)
                z = np.random.uniform(0.0, 2.0)
                points.append([x, y, z])
        
        # Sensor noise
        for _ in range(150):
            r = np.random.uniform(0.5, self.config['max_range'])
            theta = np.random.uniform(0, 2 * np.pi)
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            z = np.random.uniform(-0.5, 3.0)
            points.append([x, y, z])
        
        return np.array(points, dtype=np.float32)
    
    def process_frame(self):
        if self.paused:
            return
            
        frame_start = time.perf_counter()
        self.fallback.record_frame_start()
        
        # Generate & preprocess
        points = self.generate_pointcloud()
        points = preprocess_points(
            points,
            min_range=self.config['min_range'],
            max_range=self.config['max_range'],
            voxel_size=self.config['voxel_size'],
            remove_nan=True,
        )
        
        # Update grid map
        self.grid_map.update(points)
        
        # Dynamic object tracking
        objects = self.tracker.update(points)
        
        # Compute risk (static + dynamic)
        static_risk = compute_risk(
            self.grid_map,
            weight_occupancy=self.config['risk_weight_occupancy'],
            weight_elevation_var=self.config['risk_weight_elevation_var'],
            weight_proximity=self.config['risk_weight_proximity'],
            weight_roughness=self.config['risk_weight_roughness'],
            proximity_falloff=self.config['proximity_falloff'],
        )
        
        dynamic_risk = compute_dynamic_risk(self.grid_map, objects)
        risk = np.maximum(static_risk, dynamic_risk)
        
        # Compute uncertainty
        uncertainty = compute_uncertainty(
            self.grid_map,
            base_uncertainty=self.config['uncertainty_base'],
            decay_rate=self.config['uncertainty_decay'],
        )
        
        # Foveation pipeline
        self.prev_rois = compute_foveation_pipeline(
            self.grid_map, risk, uncertainty, self.prev_rois, self.frame,
            alpha=self.config['foveation_alpha'],
            beta=self.config['foveation_beta'],
            top_k=self.config['foveation_top_k'],
            threshold=self.config['hysteresis_threshold'],
            roi_min_size=self.config['roi_min_size'],
            roi_max_size=self.config['roi_max_size'],
            roi_expansion=self.config['roi_expansion'],
            hysteresis_frames=self.config['hysteresis_frames'],
        )
        
        # Compute allocation
        self.compute_allocator.allocate_roi_budgets(
            self.prev_rois, risk, uncertainty, self.grid_map
        )
        
        # Fallback check
        frame_time_ms = (time.perf_counter() - frame_start) * 1000
        self.fallback.record_frame_end(success=True)
        is_fallback = self.fallback.is_in_fallback()
        
        # Record history
        self.frame_times.append(frame_time_ms)
        self.roi_counts.append(len(self.prev_rois))
        self.risk_max.append(risk.max())
        budget_status = self.compute_allocator.get_budget_status()
        self.budget_util.append(budget_status['utilization'])
        
        # Web dashboard update
        if self.use_web:
            obj_data = [{
                'id': o.id, 'x': o.center[0], 'y': o.center[1],
                'vx': o.velocity[0], 'vy': o.velocity[1],
                'halo': o.get_halo_radius()
            } for o in objects]
            
            self.socketio.emit('update', {
                'frame_time': frame_time_ms,
                'roi_count': len(self.prev_rois),
                'max_risk': risk.max(),
                'budget_util': budget_status['utilization'],
                'fallback': is_fallback,
                'objects': obj_data,
            })
        
        self.frame += 1
        return {
            'points': points, 'risk': risk, 'uncertainty': uncertainty,
            'objects': objects, 'rois': self.prev_rois, 'fallback': is_fallback,
            'frame_time': frame_time_ms, 'budget': budget_status,
        }
    
    def update_plots(self, data):
        risk = data['risk']
        uncertainty = data['uncertainty']
        objects = data['objects']
        rois = data['rois']
        fallback = data['fallback']
        frame_time = data['frame_time']
        budget = data['budget']
        
        extent = [-20, 20, -20, 20]
        res = self.config['grid_resolution']
        
        # Risk map
        self.ax_risk.clear()
        im = self.ax_risk.imshow(risk, origin='lower', cmap='hot', vmin=0, vmax=max(5, risk.max()), extent=extent, aspect='equal')
        self.ax_risk.set_title('Risk Map', fontweight='bold')
        self.ax_risk.set_xlabel('X (m)'); self.ax_risk.set_ylabel('Y (m)')
        
        # Uncertainty
        self.ax_uncertainty.clear()
        self.ax_uncertainty.imshow(uncertainty, origin='lower', cmap='Blues', vmin=0, vmax=1.5, extent=extent, aspect='equal')
        self.ax_uncertainty.set_title('Uncertainty', fontweight='bold')
        
        # Elevation
        self.ax_elevation.clear()
        elev = self.grid_map.get_elevation()
        self.ax_elevation.imshow(np.nan_to_num(elev, nan=-2), origin='lower', cmap='terrain', vmin=-2, vmax=3, extent=extent, aspect='equal')
        self.ax_elevation.set_title('Elevation', fontweight='bold')
        
        # Foveation score
        self.ax_foveation.clear()
        risk_norm = risk / (risk.max() + 1e-6)
        unc_norm = uncertainty / (uncertainty.max() + 1e-6)
        fov_score = self.config['foveation_alpha'] * risk_norm + self.config['foveation_beta'] * unc_norm
        self.ax_foveation.imshow(fov_score, origin='lower', cmap='viridis', vmin=0, vmax=1, extent=extent, aspect='equal')
        self.ax_foveation.set_title('Foveation Score (αR + βU)', fontweight='bold')
        
        # Occupancy
        self.ax_occupancy.clear()
        occ = self.grid_map.get_occupancy()
        self.ax_occupancy.imshow(occ, origin='lower', cmap='gray_r', vmin=0, vmax=1, extent=extent, aspect='equal')
        self.ax_occupancy.set_title('Occupancy Grid', fontweight='bold')
        
        # Dynamic objects
        self.ax_dynamic.clear()
        self.ax_dynamic.set_xlim(-20, 20); self.ax_dynamic.set_ylim(-20, 20); self.ax_dynamic.set_aspect('equal')
        self.ax_dynamic.set_title('Dynamic Objects + Halos', fontweight='bold')
        self.ax_dynamic.grid(True, alpha=0.3)
        
        for obj in objects:
            # Object center
            self.ax_dynamic.plot(obj.center[0], obj.center[1], 'o', color=obj.color, markersize=10, markeredgecolor='white', markeredgewidth=2)
            # Velocity vector
            self.ax_dynamic.arrow(obj.center[0], obj.center[1], obj.velocity[0]*2, obj.velocity[1]*2, 
                                head_width=0.5, head_length=0.5, fc=obj.color, ec='white', linewidth=2)
            # Safety halo
            if self.show_halos:
                halo_r = obj.get_halo_radius()
                circle = Circle((obj.center[0], obj.center[1]), halo_r, fill=False, 
                              edgecolor=obj.color, linestyle='--', linewidth=2, alpha=0.6)
                self.ax_dynamic.add_patch(circle)
            # Predicted positions
            if self.show_predictions:
                for t in np.linspace(0.1, 2.0, 5):
                    pred = obj.predict(t)
                    self.ax_dynamic.plot(pred[0], pred[1], 'x', color=obj.color, alpha=0.5, markersize=6)
            # ID label
            self.ax_dynamic.text(obj.center[0], obj.center[1] + 1.5, f'ID:{obj.id}', 
                               color='white', fontsize=9, ha='center', fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.2', facecolor=obj.color, alpha=0.8))
        
        # Draw ROIs on all map axes
        if self.show_rois:
            for ax in [self.ax_risk, self.ax_foveation, self.ax_occupancy, self.ax_dynamic]:
                for roi in rois:
                    rect = Rectangle(
                        (roi.center_x - roi.size_x * res / 2, roi.center_y - roi.size_y * res / 2),
                        roi.size_x * res, roi.size_y * res,
                        linewidth=2, edgecolor='cyan', facecolor='none', alpha=0.8
                    )
                    ax.add_patch(rect)
                    ax.text(roi.center_x, roi.center_y, f'{roi.score:.2f}', 
                           color='cyan', fontsize=8, ha='center', va='center',
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.7))
        
        # ROI Detail panel
        self.ax_roi_detail.clear()
        self.ax_roi_detail.axis('off')
        roi_text = "ACTIVE ROIs\n" + "="*30 + "\n"
        for i, roi in enumerate(rois):
            cfg = self.compute_allocator.get_roi_processing_config(roi, i)
            roi_text += f"ROI {i}: pos=({roi.center_x:.1f}, {roi.center_y:.1f}) score={roi.score:.3f}\n"
            roi_text += f"  size={roi.size_x}x{roi.size_y} cells, budget={self.compute_allocator.roi_budgets.get(i, 0):.1f}ms\n"
            roi_text += f"  voxel={cfg['voxel_size']:.3f}, points={cfg['max_points']}\n\n"
        if not rois:
            roi_text += "No active ROIs"
        self.ax_roi_detail.text(0.05, 0.95, roi_text, transform=self.ax_roi_detail.transAxes,
                               fontsize=8, va='top', fontfamily='monospace',
                               bbox=dict(boxstyle='round', facecolor='#f0f0f0', alpha=0.9))
        
        # Budget panel
        self.ax_budget.clear()
        self.ax_budget.axis('off')
        budget_text = "COMPUTE BUDGET\n" + "="*30 + "\n"
        budget_text += f"Total Budget: {budget['total_budget_ms']:.0f} ms\n"
        budget_text += f"Used: {budget['used_ms']:.1f} ms ({budget['utilization']*100:.1f}%)\n"
        budget_text += f"Remaining: {budget['remaining_ms']:.1f} ms\n\n"
        budget_text += "Stage Breakdown:\n"
        for stage, t in budget['stage_times'].items():
            budget_text += f"  {stage}: {t:.1f} ms\n"
        if budget['roi_budgets']:
            budget_text += "\nROI Allocations:\n"
            for rid, b in budget['roi_budgets'].items():
                budget_text += f"  ROI {rid}: {b:.1f} ms\n"
        if budget['utilization'] > 0.9:
            budget_text += "\n[WARN] OVER BUDGET!"
        color = '#ff4444' if budget['utilization'] > 0.9 else '#00aa00'
        self.ax_budget.text(0.05, 0.95, budget_text, transform=self.ax_budget.transAxes,
                           fontsize=8, va='top', fontfamily='monospace',
                           bbox=dict(boxstyle='round', facecolor=color, alpha=0.1))
        
        # Performance history
        self.ax_perf.clear()
        self.ax_perf.plot(list(self.frame_times), 'g-', linewidth=1)
        self.ax_perf.axhline(y=self.config['fallback_latency_ms'], color='r', linestyle='--', alpha=0.5, label='Fallback Threshold')
        self.ax_perf.set_title('Frame Time (ms)', fontsize=10)
        self.ax_perf.set_ylabel('ms'); self.ax_perf.set_xlabel('Frame')
        self.ax_perf.grid(True, alpha=0.3)
        self.ax_perf.set_xlim(0, self.history_len)
        self.ax_perf.legend(fontsize=8)
        
        self.ax_roi_hist.clear()
        self.ax_roi_hist.plot(list(self.roi_counts), 'b-', linewidth=1)
        self.ax_roi_hist.set_title('Active ROIs', fontsize=10)
        self.ax_roi_hist.set_ylabel('count'); self.ax_roi_hist.set_xlabel('Frame')
        self.ax_roi_hist.grid(True, alpha=0.3)
        self.ax_roi_hist.set_xlim(0, self.history_len)
        
        self.ax_risk_hist.clear()
        self.ax_risk_hist.plot(list(self.risk_max), 'r-', linewidth=1)
        self.ax_risk_hist.set_title('Max Risk Score', fontsize=10)
        self.ax_risk_hist.set_ylabel('score'); self.ax_risk_hist.set_xlabel('Frame')
        self.ax_risk_hist.grid(True, alpha=0.3)
        self.ax_risk_hist.set_xlim(0, self.history_len)
        
        # Status panel
        self.ax_status.clear()
        self.ax_status.axis('off')
        status_text = f"""
SYSTEM STATUS
{'='*35}
Frame: {self.frame}
Time: {frame_time:.1f} ms ({(1000/frame_time):.1f} FPS)
Fallback: {'ACTIVE [ALERT]' if fallback else 'Normal [OK]'}
Active ROIs: {len(rois)}
Dynamic Objects: {len(objects)}
Budget Used: {budget['utilization']*100:.1f}%

FOVEATION PARAMS
{'='*35}
Alpha (Risk): {self.config['foveation_alpha']:.2f}
Beta (Uncertainty): {self.config['foveation_beta']:.2f}
Top-K: {self.config['foveation_top_k']}
Hysteresis: {self.config['hysteresis_frames']} frames
Threshold: {self.config['hysteresis_threshold']:.2f}

DYNAMIC OBJECTS
{'='*35}
"""
        for obj in objects:
            status_text += f"  ID{obj.id}: ({obj.center[0]:.1f}, {obj.center[1]:.1f}) v=({obj.velocity[0]:.1f}, {obj.velocity[1]:.1f}) halo={obj.get_halo_radius():.1f}m\n"
        
        self.ax_status.text(0.05, 0.95, status_text, transform=self.ax_status.transAxes,
                           fontsize=8, va='top', fontfamily='monospace',
                           bbox=dict(boxstyle='round', facecolor='#e8f5e9' if not fallback else '#fbe9e7', alpha=0.9))
        
        self.fig.canvas.draw_idle()
    
    def animate(self, frame):
        if not self.running:
            return
        
        data = self.process_frame()
        self.update_plots(data)
        return []
    
    def run(self, frames: int = 200, interval: int = 100):
        print("=" * 60)
        print("ENHANCED FOVEATED LIDAR - REAL-TIME DEMO")
        print("=" * 60)
        print("Controls:")
        print("  - Pause/Resume button")
        print("  - Object speed slider")
        print("  - Alpha/Beta weight sliders")
        print("  - Layer visibility checkboxes")
        if self.use_web:
            print("\nWeb dashboard: http://localhost:5000")
        print("\nClose window to exit.")
        print("=" * 60)
        
        ani = animation.FuncAnimation(
            self.fig, self.animate, frames=frames, 
            interval=interval, blit=False, repeat=True
        )
        
        plt.show()
        
        # Final benchmark
        benchmark_timer.print_summary()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--web', action='store_true', help='Enable web dashboard on port 5000')
    parser.add_argument('--frames', type=int, default=200, help='Number of frames')
    parser.add_argument('--interval', type=int, default=100, help='Frame interval (ms)')
    args = parser.parse_args()
    
    demo = EnhancedDemo(use_web_dashboard=args.web)
    demo.run(frames=args.frames, interval=args.interval)


if __name__ == '__main__':
    main()