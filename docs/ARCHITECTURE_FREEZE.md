# Architecture Status

Version:
V1.0

Status:
FROZEN

Authority:
ARCHITECTURE_FREEZE.md defines the technical implementation baseline.

Modification Policy:

Any change affecting:

- module boundaries
- interfaces
- data flow
- core algorithms

requires architecture review before implementation.

---

# Architecture Freeze Document: Adaptive Variable Resolution 2.5D LiDAR Mapping System

**Project:** Adaptive Variable Resolution 2.5D LiDAR Mapping System  
**Problem Statement ID:** 26053  
**Organization:** Defence Research and Development Organisation (DRDO)  
**Department:** Department of Defence R&D  
**Category:** Software  
**Theme:** Smart Vehicles  
**Document Classification:** Official Frozen Architecture Specification  
**Status:** FROZEN — Single Source of Truth  
**Architecture Authority:** Lead Systems Architect  
**Effective Date:** September 29, 2026  

---

## 1. System Identity

### 1.1 Project Title & Metadata
* **Problem Statement ID:** 26053
* **Title:** Adaptive Variable Resolution 2.5D LiDAR Mapping for Dynamic Environment Perception
* **Organization:** DRDO (Department of Defence R&D)
* **Theme:** Smart Vehicles | **Category:** Software
* **Repository Scope:** Core Packages (`fovea_lidar`, `src/perception`, `FastDEM`, `Offroad-Nav`, `web-ui`).

### 1.2 Problem Statement & Objective
Modern autonomous ground platforms require rich 3D LiDAR spatial awareness without the prohibitive memory, compute, and latency penalties of uniform volumetric processing. The objective of this system is to transform raw 3D LiDAR point clouds into an adaptive variable-resolution semantic 2.5D elevation representation that concentrates spatial acuity and compute resources dynamically on hazards, terrain roughness, and unobserved regions while maintaining a coarse global safety envelope.

### 1.3 Architecture Boundaries
In strict alignment with DRDO PS 26053 and `docs/PROJECT_CONSTITUTION.md`, system boundaries are established as follows:

1. **Core Perception & Mapping Scope (DRDO PS 26053):**
   * **Sensory Ingestion & Preprocessing:** Point cloud filtering, range gating, NaN/Inf stripping (`fovea_lidar/preprocess.py`, `src/perception/sensor_simulator.py`).
   * **2.5D Multi-Resolution Elevation Grid Mapping:** Concentric multi-tier foveated grids (`src/perception/foveated_grid.py`, `fovea_lidar/grid_map.py`) and FastDEM surface mapping (`FastDEM/`).
   * **Risk, Uncertainty, and Foveation Scoring:** Spatial hazard identification, observation curiosity decay, and predictive dynamic halos (`fovea_lidar/risk.py`, `uncertainty.py`, `foveation.py`).
   * **Deep Semantic Segmentation:** PointNet point cloud semantic segmentation (`src/perception/models/pointnet.py`) and DBSCAN obstacle clustering (`src/perception/object_detector.py`).
   * **Real-Time Visualization & Telemetry:** ROS2 RViz marker publishers (`fovea_lidar/viz.py`) and WebSocket JSON telemetry bridge (`src/simulation/websocket_server.py`) feeding the 3D WebGL dashboard (`web-ui/`).

2. **Downstream Simulation Integration Boundary:**
   * Downstream modules (`src/planning/behavior_planner.py`, `local_planner.py`, and `src/control/control_module.py`) exist in the repository strictly as a **closed-loop simulation testbed** to evaluate and benchmark perception outputs in dynamic traffic scenarios. They do NOT constitute mandatory core requirements of DRDO PS 26053 perception.

### 1.4 Intended Operational Environment
* Dynamic obstacle environments, multi-lane roadway corridors, and unstructured terrain.
* Target compute hardware: Resource-constrained embedded platforms (NVIDIA Jetson Orin/Xavier, GTX 1650-class GPUs) up to desktop simulation workstations.

---

## 2. Core Problem Definition

### 2.1 The Perception Problem Being Solved
Standard LiDAR-based perception processes point clouds uniformly. In a 32- or 64-beam LiDAR system generating $500,000$ to $1,000,000$ points per second, over $80\%$ of points fall on empty ground, sky, or irrelevant static background far away from vehicle collision trajectories. Processing this uniform data leads to:
- Excessive memory bandwidth and cache thrashing.
- Latency spikes during complex scenes with high object counts.
- High thermal dissipation and power draw on embedded robotic platforms.

### 2.2 Why Adaptive Variable Resolution is Required
Biological vision utilizes a **fovea**: an extremely high-acuity central zone surrounded by coarse peripheral awareness. By concentrating computation where spatial uncertainty and collision risks are concentrated, the vehicle achieves millimetric spatial awareness on hazards while preserving an ambient safety envelope across the remaining field of view.

### 2.3 Current Limitations of Conventional LiDAR Mapping
- **Uniform Voxel Grids:** Fixed voxel sizes force a harsh tradeoff: fine voxels ($5\text{ cm}$) exhaust memory and CPU; coarse voxels ($50\text{ cm}$) obliterate small obstacles and curbs.
- **Static Resolution 2D Costmaps:** Standard 2D occupancy grids neglect terrain elevation changes, negative obstacles (ditches), and ground clearance variance.
- **Unbounded Processing Latencies:** When point density spikes, perception queues back up, leading to stale obstacle states and vehicle safety disengagements.

### 2.4 Proposed & Implemented Methodology
1. **Multi-Resolution 2.5D Elevation Grid:** Concentric spatial rings: Inner Fovea ($0.05\text{ m}$ cell size, $\pm 5\text{ m}$ range), Mid Zone ($0.15\text{ m}$, $\pm 15\text{ m}$), and Outer Peripheral ($0.40\text{ m}$, $\pm 30\text{ m}$).
2. **Algorithmic Risk Formulation:** Fusing occupancy count, elevation variance (roughness), proximity falloff, and dynamic obstacle velocity halos into an actionable spatial scalar field.
3. **Curiosity-Driven Uncertainty:** Tracking observation density with temporal decay ($1 / \text{obs\_count}$) to direct attention to uninspected blind spots.
4. **Hysteresis Anti-Flicker:** Retaining detected ROIs across $N=5$ consecutive frames to guarantee temporal tracking stability.
5. **Deterministic Coarse Fallback:** A dedicated coarse $1.0\text{ m}$ safety grid continuously maintained in parallel that instantly takes over navigation planning if processing exceeds the $100\text{ ms}$ threshold.

---

## 3. Frozen System Philosophy

### 3.1 Non-Negotiable Priorities
1. **Safety Over Precision:** If processing spikes or high-res foveation stalls, the system immediately drops to the coarse fallback map rather than stalling or missing an obstacle.
2. **Strict Time Budgeting:** Total frame budget is pinned to $100\text{ ms}$ ($10\text{ Hz}$). No algorithmic component is permitted to block the pipeline.
3. **Local Computability (Deterministic Execution):** Core perception, risk scoring, and trajectory generation operate without external network dependencies or remote API calls.

### 3.2 Accepted Trade-Offs
- **Peripheral Coarseness:** Peripheral obstacles are tracked with lower spatial fidelity until they enter vehicle approach vectors or generate high risk scores.
- **Quantization in Elevation:** The 2.5D elevation surface stores single elevation mean/max per cell, accepting that complex vertical overhangs (e.g., bridges) are projected onto ground elevation layers.
- **Synthetic Sensor Fallback:** When physical hardware or CARLA simulators are offline, synthetic sensor generators provide real-time mock data without halting behavioral execution.

---

## 4. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SENSOR INGESTION LAYER                             │
│  - LiDAR PointCloud2 (Top 32-channel, 85m range)                            │
│  - Stereo / Monocular Camera Feeds (Front, Rear, Surround)                  │
│  - Radar Targets & GNSS/IMU Odometry State                                  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PREPROCESSING & FILTERING LAYER                       │
│  - NaN & Infinite Value Removal                                             │
│  - Range Gating (min: 0.5m, max: 50.0m - 85.0m)                             │
│  - Dynamic Voxel Downsampling (Voxel size: 0.1m)                            │
│  - Point Budget Capping (max_points_per_frame: 50,000)                      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       2.5D ELEVATION MAPPING LAYER                          │
│  - Multi-Resolution Concentric Rings (Inner: 0.05m, Mid: 0.15m, Outer: 0.4m)│
│  - FastDEM Elevation Surface Aggregation (Mean / Max Height, Cell Variance) │
│  - Ground Clearance & Roughness Calculation                                 │
│  - Continuous 1.0m Coarse Global Safety Map (Parallel Thread/Buffer)        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   RISK, UNCERTAINTY & FOVEATION LAYER                       │
│  - Static Hazard Formulation: Occupancy + Roughness + Elevation Var + Prox  │
│  - Dynamic Hazard Halos: DBSCAN Objects + Predictive Velocity Trajectories  │
│  - Exploration Uncertainty: Decay over observation count                    │
│  - Foveation Score: S = α * Risk + β * Uncertainty                          │
│  - Peak Finding & Non-Maximum Suppression (Top-K = 10 ROIs)                 │
│  - Temporal Hysteresis Filter (5-frame persistence)                         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DEEP PERCEPTION & SENSOR FUSION                         │
│  - PointNet 3D Semantic Point Cloud Segmentation (Road, Vehicle, Ped, Ground)│
│  - DBSCAN 3D Spatial Clustering + Bounding Box Fitting                      │
│  - Extended Kalman Filter (EKF) Multi-Object Tracking                       │
│  - Polynomial Lane Detection (Curvature, Offset, Confidence)                │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 CORE OUTPUT: PERCEPTION & 2.5D SEMANTIC MAP                 │
│  - Foveated 2.5D Semantic Elevation Surface & Occupancy Grid                │
│  - Categorized Drivable Terrain, Static Hazards, and Dynamic Obstacles       │
│  - ROS2 Visual Markers (/fovea/*) & WebSocket Telemetry Stream (ws://:8765) │
│  - Real-Time WebGL Dashboard Visualization (http://localhost:3000)          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼ (Optional Perception Feed)
┌─────────────────────────────────────────────────────────────────────────────┐
│           DOWNSTREAM CLOSED-LOOP SIMULATION TESTBED (OPTIONAL HARNESS)      │
│  - Global Path Planner (Cached A* Road Graph Waypoints)                     │
│  - Behavior State Machine: Lane Follow, Overtake, Stop, Emergency Stop      │
│  - Adaptive Cruise Control (ACC) Time-Headway & Safety Distance Computation │
│  - Local Trajectory Optimization: Quartic/Quintic Frenet Polynomials        │
│  - Vehicle Dynamics: Bicycle Kinematic Model & Longitudinal/Lateral Control │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Detailed Module Specification

### 5.1 Module: `fovea_lidar.node` (`FoveaLidarNode`)
* **Purpose:** ROS2 perception node orchestrating pre-filtering, 2.5D grid construction, hazard scoring, ROI extraction, and fallback monitoring.
* **Input:** `sensor_msgs/msg/PointCloud2` on `/lidar_points`.
* **Output:** `visualization_msgs/msg/MarkerArray` on `/fovea/elevation_map`, `/fovea/occupancy_map`, `/fovea/risk_map`, `/fovea/foveation_rois`, `/fovea/fallback_map`; `std_msgs/msg/Bool` on `/fovea/fallback_active`.
* **Responsibilities:** Subscribes to incoming point clouds, executes downsampling, invokes risk and uncertainty pipelines, runs hysteresis, monitors frame latency, and publishes visualization markers.
* **Internal Logic:** Spawns a periodic timer (`1.0 / viz_rate_hz`). If execution time exceeds `fallback_latency_ms` ($100\text{ ms}$), triggers `_on_fallback` to broadcast the coarse map.
* **Dependencies:** `rclpy`, `preprocess`, `grid_map`, `risk`, `uncertainty`, `foveation`, `hysteresis`, `fallback`, `viz`.
* **Owned Interfaces:** Parameters defined under namespace `fovea_lidar_node`.
* **Modification Restrictions:** FROZEN. No changes to topic names, QoS profiles, or timer hooks.

### 5.2 Module: `fovea_lidar.grid_map` (`GridMap2D`)
* **Purpose:** High-performance 2.5D spatial grid representing terrain elevation, occupancy counts, observation history, and surface roughness.
* **Input:** $N \times 3$ NumPy array of $(x, y, z)$ coordinates.
* **Output:** 2D NumPy matrices for elevation, occupancy, observation counts, and roughness.
* **Responsibilities:** Coordinate transforms between world space $(X, Y)$ and discrete grid indices $(gx, gy)$; incremental aggregation of point statistics.
* **Internal Logic:** Vectorized index projection via floor division by resolution; cell-wise running mean and variance computation. Maintains a parallel `coarse_map` with resolution $1.0\text{ m}$.
* **Dependencies:** `numpy`, `GridMapConfig`.
* **Modification Restrictions:** FROZEN. Coordinate transformation math is frozen.

### 5.3 Module: `fovea_lidar.risk`
* **Purpose:** Computes a normalized spatial hazard matrix over the grid.
* **Input:** `GridMap2D` instance, list of dynamic objects.
* **Output:** 2D float array of risk scores clipped to $[0.0, 10.0]$.
* **Responsibilities:** Quantifies obstacle presence, terrain roughness, vehicle proximity, and dynamic obstacle safety halos.
* **Internal Logic:** Linear combination:
  $$R(x, y) = w_{occ} \cdot O + w_{var} \cdot \sigma_z^2 + w_{rough} \cdot R_{surf} + w_{prox} \cdot \exp\left(-\frac{\sqrt{x^2 + y^2}}{d_{falloff}}\right)$$
  Dynamic hazard halos project circular decay fields around tracked object centroids: $w_{halo} \cdot (1 - d/r_{halo})$.
* **Dependencies:** `numpy`, `benchmark`.
* **Modification Restrictions:** FROZEN. Risk weight coefficients and falloff models must not be altered without benchmark re-validation.

### 5.4 Module: `fovea_lidar.foveation`
* **Purpose:** Computes the master foveation score and extracts bounded Regions of Interest (ROIs).
* **Input:** Risk array, uncertainty array, previous ROIs list.
* **Output:** List of `ROI` dataclass objects.
* **Responsibilities:** Blends risk and curiosity, extracts spatial score peaks using non-maximum suppression (NMS), creates adaptive bounding boxes, and applies temporal hysteresis.
* **Internal Logic:** Sorts score array, iteratively selects peaks above `threshold` ($0.3$), applies suppression radius ($3$ cells), expands boxes proportional to score, and calls `apply_hysteresis`.
* **Dependencies:** `numpy`, `dataclasses.ROI`.
* **Modification Restrictions:** FROZEN. Top-K limit ($10$) and NMS suppression radius ($3$) are frozen.

### 5.5 Module: `fovea_lidar.fallback` (`FallbackController`)
* **Purpose:** Guarantees real-time execution safety via deterministic latency-triggered degradation.
* **Input:** Frame execution start and end timestamps.
* **Output:** Boolean fallback state; triggers fallback/recovery callbacks.
* **Responsibilities:** Detects timing budget violations ($> 100\text{ ms}$ or runtime exceptions) and switches perception output to the coarse global map.
* **Internal Logic:** Sliding window latency tracking; requires $5$ consecutive nominal frames before resetting fallback mode.
* **Dependencies:** `time`, `numpy`.
* **Modification Restrictions:** FROZEN. Timing threshold ($100\text{ ms}$) is non-negotiable.

### 5.6 Module: `src.perception.foveated_grid` (`FoveatedGrid25D`)
* **Purpose:** AV simulation multi-tier concentric 2.5D elevation grid model.
* **Input:** Vehicle pose `(x, y, yaw)` and synthetic/physical point cloud.
* **Output:** Multi-tier elevation grids and semantic occupancy layers.
* **Responsibilities:** Manages 3 concentric foveal rings: Inner Fovea ($10\text{ m} \times 10\text{ m}$ @ $0.05\text{ m}$), Mid Region ($30\text{ m} \times 30\text{ m}$ @ $0.15\text{ m}$), and Outer Ambient ($60\text{ m} \times 60\text{ m}$ @ $0.40\text{ m}$).
* **Dependencies:** `numpy`, `scipy.spatial`.
* **Modification Restrictions:** FROZEN. Ring geometries and resolutions are locked.

### 5.7 Module: `src.perception.models.pointnet` (`PointNetSeg`)
* **Purpose:** Deep learning 3D point cloud semantic segmentation network.
* **Input:** $B \times N \times 3$ coordinate tensors.
* **Output:** $B \times N \times C$ per-point class classification probabilities (4 classes: Road, Vehicle, Pedestrian, Ground/Obstacle).
* **Responsibilities:** Extracts permutation-invariant global and local point cloud features using T-Net spatial transformations, multi-layer shared MLPs ($64, 128, 1024$), and feature concatenation.
* **Dependencies:** `torch`, `torch.nn`.
* **Modification Restrictions:** FROZEN. Model weights, T-Net architectures, and class index mappings are locked.

### 5.8 Module: `src.perception.sensor_fusion` (`SensorFusion`)
* **Purpose:** Multi-sensor spatial association and persistent object state tracking.
* **Input:** 3D bounding boxes from LiDAR object detector, 2D bounding boxes from camera detector.
* **Output:** Tracked list of `DetectedObject` instances with stable track IDs and velocities.
* **Responsibilities:** 3D-to-2D geometric frustum projection; Hungarian association; continuous state filtering with Kalman filtering.
* **Internal Logic:** Constant velocity motion model: State vector $[x, y, z, v_x, v_y, v_z]^T$.
* **Dependencies:** `numpy`, `filterpy.kalman` / direct matrix formulation.
* **Modification Restrictions:** FROZEN. State vector dimensionality and association thresholds are locked.

### 5.9 Module: `src.planning.behavior_planner` (`BehaviorPlanner`)
* **Purpose:** High-level tactical decision maker executing finite state machine (FSM) transitions.
* **Input:** Vehicle state, perception result (tracked vehicles, pedestrians, traffic signal states).
* **Output:** `BehaviorDecision` dataclass (`BehaviorState`, target speed, target lane, stop distance).
* **Responsibilities:** Manages lane following, left/right overtaking maneuvers, crosswalk pedestrian yielding, traffic signal adherence, and emergency stops.
* **Internal Logic:** 
  - Time-Headway calculation: $d_{safe} = d_{min} + v \cdot T_{headway}$.
  - State transitions: `LANE_FOLLOW` $\to$ `LANE_CHANGE_LEFT` triggered when lead vehicle speed $< 75\%$ target speed and adjacent lane gap $\ge 25\text{ m}$.
  - Re-entry: `LANE_CHANGE_RIGHT` triggered once clear of overtaken obstacle by $\ge 20\text{ m}$.
* **Dependencies:** `src.types.BehaviorState`, `src.types.BehaviorDecision`.
* **Modification Restrictions:** FROZEN. Safety gap constants and state enumeration values are immutable.

### 5.10 Module: `src.planning.local_planner` (`LocalPlanner`)
* **Purpose:** Collision-free, kinematically feasible trajectory generation in Frenet coordinate frame.
* **Input:** Current vehicle state, reference path waypoints, behavior decision, perception obstacles.
* **Output:** `Trajectory` dataclass containing timed waypoints with target curvatures and velocities.
* **Responsibilities:** Computes longitudinal quintic polynomials and lateral quartic polynomials minimizing jerk, lateral acceleration, target deviation, and obstacle collision cost.
* **Dependencies:** `numpy`, `src.types.Trajectory`, `src.types.Waypoint`.
* **Modification Restrictions:** FROZEN. Frenet conversion and cost weight matrices are locked.

### 5.11 Module: `src.control.control_module` (`ControlModule`)
* **Purpose:** Executes low-level vehicular trajectory tracking.
* **Input:** Current vehicle state, planned trajectory, behavior decision, time delta $dt$.
* **Output:** `ControlCommand` dataclass (`steer`, `throttle`, `brake`, `reverse`).
* **Responsibilities:** Coordinates lateral steering control (Pure Pursuit / Stanley) and longitudinal speed control (PID).
* **Internal Logic:**
  - Pure Pursuit: $\delta = \arctan\left(\frac{2 L \sin\alpha}{L_{lookahead}}\right)$ where $L_{lookahead} = k \cdot v + L_0$.
  - PID: $a_{cmd} = K_p e_v + K_i \int e_v dt + K_d \frac{de_v}{dt}$.
* **Dependencies:** `src.control.lateral_control`, `src.control.longitudinal_control`.
* **Modification Restrictions:** FROZEN. Wheelbase ($L = 2.875\text{ m}$) and controller gains are locked.

### 5.12 Module: `src.simulation.websocket_server` (`SimulationWebSocketServer`)
* **Purpose:** High-throughput JSON state serialization and WebSocket broadcasting server.
* **Input:** Vehicle state, perception result, trajectory, behavior decision, control command, sensor snapshots.
* **Output:** Asynchronous WebSocket frame broadcasts to port `8765`.
* **Responsibilities:** Serializes simulation data at $\sim 30\text{ Hz}$ for consumption by the 3D Web UI frontend. Handles client connect/disconnect events safely.
* **Dependencies:** `asyncio`, `websockets`, `json`.
* **Modification Restrictions:** FROZEN. Broadcast schema, payload field names, and port `8765` are locked.

---

## 6. Data Flow Architecture

### 6.1 Sequential Data Flow

```
[Raw LiDAR / Synthetic Engine]
               │ (Points: x, y, z, intensity)
               ▼
   [Preprocessing Pipeline]
   (NaN Strip, Range Gate, Voxel Downsample)
               │ (Cleaned Points)
               ▼
     [2.5D Grid Generator]
     (Mean Elevation, Occupancy, Roughness)
               │
       ┌───────┴────────────────────────┐
       ▼                                ▼
[Risk Estimator]             [Uncertainty Estimator]
(Static Hazard + Halos)       (Decay over observation count)
       │                                │
       └───────┬────────────────────────┘
               ▼
    [Foveation Scorer & NMS]
   (Score = α·Risk + β·Uncertainty)
               │ (Top-K Peak Cells)
               ▼
   [ROI Generator & Hysteresis]
 (Expanded Box ROIs + 5-Frame Cache)
               │
               ├────────────────────────┐
               ▼                        ▼
     [PointNet Semantic Seg]   [DBSCAN Clustering & Fusion]
   (Per-Point Class Labeling)   (EKF Object Tracks & Velocities)
               │                        │
               └───────┬────────────────┘
                       ▼
             [Perception Result]
       (Objects, Lanes, Foveated Grids)
                       │
       ┌───────────────┴───────────────────────────────┐
       ▼                                               ▼
[Core Perception Telemetry & WebGL UI]   [Downstream Closed-Loop Simulation Testbed]
- ROS2 Visual Markers (/fovea/*)         - Behavior State Machine (ACC Gap Logic)
- WebSocket Frame Stream (ws://:8765)    - Frenet Local Planner (Quartic/Quintic)
- 3D Digital Twin Canvas (port 3000)     - Vehicle Control (Pure Pursuit & PID)
                                         - Bicycle Dynamics Integration
```

---

## 7. ROS2 Architecture

### 7.1 Package Manifest: `fovea_lidar`
* **Build System:** `ament_python`
* **Dependencies:** `rclpy`, `sensor_msgs`, `geometry_msgs`, `visualization_msgs`, `std_msgs`, `builtin_interfaces`.

### 7.2 Nodes & Topic Graph

| Node Name | Executable Name | Role |
| :--- | :--- | :--- |
| `fovea_lidar_node` | `fovea_node` | Core 2.5D foveated perception & risk estimation engine |
| `synthetic_publisher` | `synthetic_publisher` | Synthetic multi-obstacle and terrain point cloud generator |
| `rviz2` | `rviz2` | ROS2 official 3D hardware-accelerated visualizer |

### 7.3 Topic Specifications

| Topic Name | Message Type | Direction | Description |
| :--- | :--- | :--- | :--- |
| `/lidar_points` | `sensor_msgs/msg/PointCloud2` | Subscribed by `fovea_lidar_node` | Raw 3D point cloud input |
| `/fovea/elevation_map` | `visualization_msgs/msg/MarkerArray` | Published by `fovea_lidar_node` | Color-mapped 3D elevation cubes |
| `/fovea/occupancy_map` | `visualization_msgs/msg/MarkerArray` | Published by `fovea_lidar_node` | Occupied obstacle cells (red markers) |
| `/fovea/risk_map` | `visualization_msgs/msg/MarkerArray` | Published by `fovea_lidar_node` | Spatial hazard heatmap cubes |
| `/fovea/foveation_rois` | `visualization_msgs/msg/MarkerArray` | Published by `fovea_lidar_node` | Cyan wireframe ROI bounding boxes |
| `/fovea/fallback_map` | `visualization_msgs/msg/MarkerArray` | Published by `fovea_lidar_node` | Coarse 1.0m fallback map cubes |
| `/fovea/fallback_active` | `std_msgs/msg/Bool` | Published by `fovea_lidar_node` | High-latency fallback trigger flag |

### 7.4 ROS2 Parameters (`fovea_lidar/config/params.yaml`)
* `grid_resolution`: $0.2\text{ m/cell}$
* `grid_size_x`, `grid_size_y`: $200 \times 200$ cells ($40\text{ m} \times 40\text{ m}$ coverage)
* `grid_origin_x`, `grid_origin_y`: $-20.0\text{ m}, -20.0\text{ m}$
* `foveation_alpha`: $0.7$ (risk weight)
* `foveation_beta`: $0.3$ (uncertainty weight)
* `foveation_top_k`: $10$ (maximum active ROIs)
* `hysteresis_frames`: $5$ (anti-flicker retention frames)
* `fallback_latency_ms`: $100\text{ ms}$ (real-time cutoff threshold)
* `fallback_coarse_resolution`: $1.0\text{ m}$

---

## 8. Algorithm Architecture

### 8.1 Foveation Scoring Formula
$$\text{Score}(x, y) = \alpha \cdot \frac{\text{Risk}(x, y)}{\max(\text{Risk}) + \epsilon} + \beta \cdot \frac{\text{Uncertainty}(x, y)}{\max(\text{Uncertainty}) + \epsilon}$$
* Default parameters: $\alpha = 0.7$, $\beta = 0.3$, $\epsilon = 10^{-6}$.
* Location: `fovea_lidar/fovea_lidar/foveation.py`.

### 8.2 Non-Maximum Suppression (NMS) Peak Extraction
1. Flatten score matrix and sort indices descending.
2. For each candidate peak cell $(x_i, y_i)$ with score $\ge \text{threshold}$ ($0.3$):
   - Reject if cell marked as suppressed.
   - Append to active peaks list.
   - Suppress all surrounding cells within radius $r = 3$ cells.
   - Stop when peak count equals `top_k` ($10$).
* Location: `fovea_lidar/fovea_lidar/foveation.py::find_peak_cells`.

### 8.3 Observation Uncertainty with Temporal Decay
$$\text{Uncertainty}(x, y) = U_{base} \cdot \exp\left(-\lambda \cdot N_{obs}(x, y)\right)$$
* Where $U_{base} = 1.0$, $\lambda = 0.1$, and $N_{obs}$ is the cumulative point hit count.
* Location: `fovea_lidar/fovea_lidar/uncertainty.py`.

### 8.4 Dynamic Object Safety Halo Expansion
$$R_{halo}(x, y) = \sum_{k=1}^{M} w_{halo} \cdot \max\left(0, 1 - \frac{d_k(x, y)}{r_{halo}}\right)$$
* Where $d_k(x, y)$ is distance to object centroid $k$, $r_{halo} = 2.0\text{ m}$, and $w_{halo} = 2.0$.
* Location: `fovea_lidar/fovea_lidar/risk.py::compute_dynamic_risk`.

### 8.5 Frenet Polynomial Trajectory Optimization
* Lateral trajectory formulated as a quartic polynomial:
  $$d(t) = a_0 + a_1 t + a_2 t^2 + a_3 t^3 + a_4 t^4$$
* Longitudinal trajectory formulated as a quintic polynomial:
  $$s(t) = b_0 + b_1 t + b_2 t^2 + b_3 t^3 + b_4 t^4 + b_5 t^5$$
* Cost functional minimized:
  $$J = w_{jerk} \int \dddot{d}^2 dt + w_{curv} \int \kappa^2 dt + w_{dev} (d - d_{target})^2 + w_{coll} C_{obstacle}$$
* Location: `src/planning/local_planner.py`.

---

## 9. State Management

### 9.1 Behavior State Machine Transitions
* **States:** `LANE_FOLLOW`, `LANE_CHANGE_LEFT`, `LANE_CHANGE_RIGHT`, `STOP`, `EMERGENCY_STOP`, `INTERSECTION`, `PARKING`.
* **Lifecycle Rules:**
  - `LANE_FOLLOW` $\to$ `EMERGENCY_STOP`: Triggered when obstacle distance $< 5.0\text{ m}$ with relative approach speed.
  - `LANE_FOLLOW` $\to$ `STOP`: Triggered by Red traffic signal within $30\text{ m}$ or active crosswalk pedestrian.
  - `LANE_FOLLOW` $\to$ `LANE_CHANGE_LEFT`: Triggered when blocked by slow lead vehicle and adjacent lane safety corridor is clear.
  - `LANE_CHANGE_LEFT` $\to$ `LANE_CHANGE_RIGHT`: Triggered after forward progress past overtaken vehicle exceeds clearance buffer ($20.0\text{ m}$).

### 9.2 Tracked Object Lifecycle (Sensor Fusion EKF)
* `hits`: Number of successive sensor observations.
* `age`: Cumulative frame lifetime.
* Creation threshold: Spawned with $hits = 1$. Confirmed active when $hits \ge 3$.
* Pruning threshold: Deregistered when no sensor associations occur for $> 5$ consecutive frames.

---

## 10. Configuration Architecture

### 10.1 Primary Configuration Files
1. **ROS2 Parameter File:** `fovea_lidar/config/params.yaml`
   - Defines all grid boundaries, sensor clipping ranges, foveation alpha/beta weights, and fallback thresholds.
2. **Simulation System Config:** `src/config/settings.yaml`
   - Governs simulation physics step ($dt = 0.033\text{ s}$), vehicle physical parameters ($wheelbase = 2.875\text{ m}$, $mass = 1500\text{ kg}$), sensor mounting poses, planning horizon ($50\text{ m}$), and PID/Pure Pursuit gains.
3. **Frontend Vite Configuration:** `web-ui/vite.config.js`
   - Configures local port $3000$, HMR polling interval ($100\text{ ms}$), and reverse proxy `/ws` to `ws://localhost:8765`.

---

## 11. Runtime Architecture

### 11.1 System Startup Sequence
1. **Batch Launcher Execution:** [`run_project.bat`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/run_project.bat) or [`start_live.bat`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/start_live.bat).
2. **Backend Daemon Initialization:**
   - Spawns Python process (`main.py --headless` or `watch_backend.py`).
   - Launches asynchronous WebSocket server thread listening on `ws://localhost:8765`.
   - Initializes `WorldManager`, loads static roadway topology, dynamic traffic agents, and pedestrian crosswalks.
   - Instantiates `PerceptionModule`, `PlanningModule`, and `ControlModule`.
3. **Frontend Server Startup:**
   - Launches Vite development server in `web-ui` on `http://localhost:3000`.
   - Opens client web browser to simulation dashboard.
4. **WebSocket Connection Handshake:**
   - Client establishes duplex socket connection.
   - Server streams full telemetry state frames at $30\text{ Hz}$.

### 11.2 Shutdown Behavior
- `SIGINT` (Ctrl+C) trapped across backend and watcher processes.
- Clean WebSocket disconnection broadcast to client browser.
- Visualizer display buffers released cleanly.

---

## 12. Validation Architecture

### 12.1 Regression Test Suite
* **Script:** [`verify_simulation.py`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/verify_simulation.py)
* **Validations Executed:**
  1. Initialization check: Verifies $\ge 12$ persistent pedestrian agents exist in `WorldManager`.
  2. Scenario application check: Verifies `lane_change` scenario spawns lead truck and maintains traffic states without entity drops.
  3. Closed-loop simulation step: Steps the physics and perception loop across $350$ steps ($11.5\text{ s}$ simulation time).
  4. Assertions:
     - Vehicle achieves cruising speed $> 60\text{ km/h}$ (nominal: $85.3\text{ km/h}$).
     - `BehaviorState.LANE_CHANGE_LEFT` and `LANE_CHANGE_RIGHT` successfully execute.
     - Pedestrians remain persistent across every single step.

### 12.2 Standalone Demonstration Scripts
* `fovea_lidar/run_demo.py` & `fovea_lidar/run_enhanced_demo.py`: Standalone Matplotlib 6-panel evaluation of risk, uncertainty, and foveation without ROS2 requirement.

---

## 13. Frozen Interfaces

## DO NOT CHANGE WITHOUT ARCHITECT APPROVAL

The following interfaces, schemas, and directories are officially FROZEN and must not be modified, renamed, moved, or deleted:

1. **ROS2 Topic Interfaces:**
   - `/lidar_points` (`sensor_msgs/msg/PointCloud2`)
   - `/fovea/elevation_map` (`visualization_msgs/msg/MarkerArray`)
   - `/fovea/occupancy_map` (`visualization_msgs/msg/MarkerArray`)
   - `/fovea/risk_map` (`visualization_msgs/msg/MarkerArray`)
   - `/fovea/foveation_rois` (`visualization_msgs/msg/MarkerArray`)
   - `/fovea/fallback_map` (`visualization_msgs/msg/MarkerArray`)
   - `/fovea/fallback_active` (`std_msgs/msg/Bool`)
2. **WebSocket Telemetry Payload Keys (`ws://localhost:8765`):**
   - `vehicle_state`: `{x, y, yaw, speed, steer_angle, acceleration}`
   - `trajectory`: `[{x, y, speed, curvature}]`
   - `behavior`: `{state, target_lane, target_speed, reason}`
   - `perception`: `{objects: [...], lanes: [...], traffic_signal: {...}}`
   - `control`: `{steer, throttle, brake}`
3. **Core Dataclass Signatures (`src/types.py`):**
   - `VehicleState`, `BoundingBox3D`, `DetectedObject`, `PerceptionResult`, `Waypoint`, `Trajectory`, `BehaviorDecision`, `ControlCommand`.
4. **Behavior State Enumerations (`src/types.py::BehaviorState`):**
   - `LANE_FOLLOW`, `LANE_CHANGE_LEFT`, `LANE_CHANGE_RIGHT`, `STOP`, `EMERGENCY_STOP`, `INTERSECTION`, `PARKING`.
5. **Directory Boundaries:**
   - `fovea_lidar/`: ROS2 package root.
   - `src/`: Python core simulation and algorithmic modules.
   - `web-ui/`: Vite React Three Fiber client.
   - `FastDEM/`: 2.5D DEM mapping submodule.
   - `Offroad-Nav/`: Navigation stack and 3D datasets.

---

## 14. Known Limitations

The following items are recorded as existing technical characteristics and limitations of the current implementation (not to be altered during this freeze):

1. **2.5D Overhang Inversion:** The 2.5D elevation surface stores single height statistics per $(x, y)$ coordinate cell; multi-level structures (such as bridges or overpasses) cannot represent open underpasses in the elevation layer.
2. **Pygame / Headless Dual-Path:** Visualization bifurcates between native Pygame rendering (`src/visualization/visualizer.py`) and the WebGL frontend (`web-ui/`). When running `--headless`, Pygame is deactivated and state is piped exclusively via WebSocket.
3. **FastDEM Pybind Dependency:** The FastDEM C++ pybind extension requires a local C++ compilation environment; if missing, the system defaults to the native vectorized NumPy grid builder.
4. **Synthetic Obstacle Generator:** In the absence of a live physical LiDAR sensor or active CARLA server, synthetic sensor generators synthesize planar road points and geometric bounding boxes.

---

## 15. Future Development Boundary

### 15.1 Allowed Future Changes
- Addition of new scenario profiles within `src/simulation/scenario.py` conforming to existing interfaces.
- Incremental performance optimizations within internal module logic that preserve existing function signatures and test assertions.
- Expansion of automated test assertions within `verify_simulation.py` or new standalone pytest suites.
- Documentation additions and tuning parameter adjustments within `params.yaml` backed by quantitative benchmarks.

### 15.2 Forbidden Changes
- Architectural redesigns or changes to the high-level data flow pipeline.
- Silent replacement or removal of existing modules, algorithms, or classes.
- Alteration of ROS topic names, message types, or WebSocket communication JSON schemas.
- Renaming or re-architecting directory boundaries (`fovea_lidar/`, `src/`, `web-ui/`, etc.).
- Modification of immutable frozen contracts without formal Architectural Review Board review.
