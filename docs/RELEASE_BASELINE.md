# Release Baseline Specification: V1.0 Architecture Baseline

**Project:** Adaptive Variable Resolution 2.5D LiDAR Mapping System  
**Problem Statement:** DRDO PS 26053 — *Adaptive Variable Resolution 2.5D LiDAR Mapping for Dynamic Environment Perception*  
**Document Authority:** Release Manager  
**Classification:** Level 3 Authority (Official Stable Release Reference)  
**Status:** STABLE ENGINEERING BASELINE  
**Effective Date:** September 29, 2026  

---

## 1. Release Identity

* **Project:** Adaptive Variable Resolution 2.5D LiDAR Mapping System
* **Release Version:** V1.0 Architecture Baseline
* **Problem Statement ID:** DRDO PS 26053
* **Organization:** Defence Research and Development Organisation (DRDO)
* **Department:** Department of Defence R&D
* **Category:** Software
* **Theme:** Smart Vehicles
* **Status:** Stable Engineering Baseline

---

## 2. Baseline Authority

This release represents the canonical, verified, and frozen technical state of the project. It is governed strictly by the following repository authority documents:

1. [`docs/PROJECT_CONSTITUTION.md`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/docs/PROJECT_CONSTITUTION.md) (Level 1 Authority: Governance, Mission, and Boundaries)
2. [`docs/ARCHITECTURE_FREEZE.md`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/docs/ARCHITECTURE_FREEZE.md) (Level 2 Authority: Frozen Architecture V1.0)
3. [`docs/VALIDATION_PROTOCOL.md`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/docs/VALIDATION_PROTOCOL.md) (Level 3 Authority: Verification Protocol V1.0)

**Compatibility Mandate:** Any future code commit, bug resolution, or capability extension must preserve backwards compatibility with this V1.0 baseline. No implementation may silently regress, break interfaces, or violate frozen module boundaries.

---

## 3. Frozen System Capabilities

This baseline certifies the following verified capabilities (and excludes unverified or future research ideas):

### 3.1 3D LiDAR Ingestion & Preprocessing
* Ingestion of raw 3D point cloud streams (`sensor_msgs/msg/PointCloud2`).
* Vectorized NaN and infinite coordinate stripping.
* Range gating bounded between $0.5\text{ m}$ (near-body clearance) and $50.0\text{ m}$ to $85.0\text{ m}$ (sensor maximum).
* Voxel-grid downsampling with point budget capping ($50,000$ points/frame) to prevent compute stalls.

### 3.2 Deep Learning Semantic Perception Pipeline
* PointNet 3D point cloud semantic segmentation (`src/perception/models/pointnet.py`) generating per-point classification labels (Ground/Drivable, Non-Drivable Obstacle, Vehicles, Pedestrians).
* Geometric DBSCAN spatial clustering for bounding box extraction.

### 3.3 2.5D Elevation & Occupancy Grid Mapping
* Projection of 3D point coordinates into discrete 2.5D spatial grids (`fovea_lidar/grid_map.py`, `src/perception/foveated_grid.py`).
* Cell-level elevation height aggregation (mean and maximum).
* Occupancy probability calculation and surface roughness estimation (elevation variance $\sigma_z^2$).
* Synchronous maintenance of a parallel coarse $1.0\text{ m}$ safety fallback map.

### 3.4 Adaptive Variable-Resolution & Foveation Engine
* Multi-objective foveation scoring combining spatial collision risk ($\alpha = 0.7$) and curiosity-driven exploration uncertainty ($\beta = 0.3$).
* Dynamic hazard safety halo expansion around moving obstacle trajectories.
* Non-Maximum Suppression (NMS) peak cell extraction (Top-$K = 10$ active ROIs).
* Temporal hysteresis filter retaining detected ROIs across $N = 5$ consecutive frames to prevent visual/tracking flicker.
* Deterministic latency-triggered fallback controller that swaps perception output to the coarse $1.0\text{ m}$ safety map if frame latency exceeds $100\text{ ms}$.

### 3.5 Real-Time Visualization & Telemetry Layer
* Native ROS2 RViz visualization marker generation (`visualization_msgs/msg/MarkerArray`) publishing color-coded elevation cubes, occupancy boundaries, risk heatmaps, and cyan ROI wireframes.
* Real-time WebSocket JSON state serialization (`src/simulation/websocket_server.py`) streaming telemetry at $\sim 30\text{ Hz}$ on `ws://localhost:8765`.
* Interactive WebGL 3D digital twin dashboard (`web-ui/`) rendering live elevation surfaces, traffic agents, and telemetry HUD on `http://localhost:3000`.

### 3.6 Dynamic Tracking & Lifecycle System
* Extended Kalman Filter (EKF) multi-object state estimation.
* Object lifecycle management tracking hits, age, velocity vectors, and clean track deletion after $5$ consecutive missed observations.

---

## 4. Validated Components

The baseline has been verified across the following platforms and software environments:

### 4.1 Target Software Environment
* **Primary Operating System:** Linux (Ubuntu 22.04 LTS) / Windows cross-platform developer workstation.
* **Robotics Middleware:** ROS2 Humble / Iron (`ament_python` build toolchain).
* **Language Runtimes:** Python 3.10+ / 3.11, Node.js v20+ / v24.

### 4.2 Verified Package & Subsystem Manifest

| Subsystem | Canonical Path | Verified State |
| :--- | :--- | :--- |
| **ROS2 Core Package** | [`fovea_lidar/`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/fovea_lidar/) | Verified `package.xml`, launch files, and ROS2 nodes (`fovea_node`, `synthetic_publisher`) |
| **LiDAR Preprocessor** | `fovea_lidar/fovea_lidar/preprocess.py` | Verified range filtering, voxelization, NaN removal |
| **2.5D Grid Engine** | `fovea_lidar/fovea_lidar/grid_map.py` | Verified coordinate transforms, elevation aggregation |
| **Hazard & Foveation** | `fovea_lidar/fovea_lidar/foveation.py` | Verified dual-scoring, NMS peak extraction, hysteresis |
| **Fallback Controller** | `fovea_lidar/fovea_lidar/fallback.py` | Verified $100\text{ ms}$ latency monitoring and recovery |
| **PointNet Model** | `src/perception/models/pointnet.py` | Verified 3D tensor inference and class probabilities |
| **Sensor Fusion Tracker** | `src/perception/sensor_fusion.py` | Verified EKF kinematic filtering and track persistence |
| **WebSocket Bridge** | `src/simulation/websocket_server.py` | Verified asynchronous $30\text{ Hz}$ state streaming |
| **3D WebGL Dashboard** | `web-ui/` | Verified React Three Fiber canvas on port $3000$ |
| **Downstream Testbed** | `src/planning/`, `src/control/`, `verify_simulation.py` | Verified closed-loop regression test harness ($100\%$ pass) |

---

## 5. Known Stable Architecture Reference

* **Architecture Specification Version:** V1.0 (Detailed in [`docs/ARCHITECTURE_FREEZE.md`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/docs/ARCHITECTURE_FREEZE.md))
* **Validation Protocol Version:** V1.0 (Detailed in [`docs/VALIDATION_PROTOCOL.md`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/docs/VALIDATION_PROTOCOL.md))
* **Architectural Decisions Baseline:** ADR 01 through 07 (Detailed in [`docs/DECISIONS.md`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/docs/DECISIONS.md))
* **Recovery Checkpoint Archive:** `.checkpoints/checkpoint_stable_phase/` and [`rollback.bat`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/rollback.bat)

---

## 6. Known Limitations & Technical Debt

To maintain absolute engineering transparency, the following technical debt and constraints are recorded as inherent to the V1.0 baseline:

1. **2.5D Vertical Overhang Inversion:** The 2.5D grid compresses 3D points into a single elevation height per $(x, y)$ coordinate cell; multi-level vertical structures (e.g., overpasses, tunnels) project roof and ground simultaneously into elevation obstacles.
2. **C++ Pybind Toolchain Prerequisite (FastDEM):** FastDEM pybind integration requires a host C++ compiler. A vectorized NumPy fallback executes if the compiled binary is absent.
3. **Synthetic Sensor Standalone Mode:** In the absence of live physical LiDAR hardware or a running CARLA simulator, synthetic sensor generators provide real-time point clouds to maintain continuous testing capability.
4. **Pygame vs. WebGL Bifurcation:** Visualization operates in two distinct modes: native desktop Pygame (`src/visualization/visualizer.py`) or headless WebSocket streaming to the WebGL dashboard (`web-ui/`).

---

## 7. Future Change Policy

Any post-V1.0 modification must strictly adhere to the following four-step governance protocol:

1. **Formal Change Request:** Identify defect or capability requirement, referencing affected modules and frozen interfaces.
2. **Architecture Impact Review:** Execute Level 4 Architecture Compliance Audit (`docs/VALIDATION_PROTOCOL.md`) to guarantee zero interface drift or boundary violations.
3. **Validation Evidence:** Execute Levels 0–6 validation and provide deterministic test execution proof (e.g., terminal test logs with 100% assertions passing).
4. **Changelog Record:** Document change rationale, files touched, and validation outcome in [`docs/CHANGELOG.md`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/docs/CHANGELOG.md).

---

## 8. Baseline Declaration

The V1.0 baseline represents the first stable, documented, and validated state of the Adaptive Variable Resolution 2.5D LiDAR Mapping System.

Future development must preserve architectural integrity and maintain validation compliance.
