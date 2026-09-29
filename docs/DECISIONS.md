# Architectural Decisions Record (ADR)

**Project:** Adaptive Variable Resolution 2.5D LiDAR Mapping System  
**Repository:** `2.5.1`  
**Document Authority:** Lead Systems Architect  
**Status:** ACTIVE  

---

### Decision: Biologically-Inspired Foveated Multi-Resolution 2.5D Mapping
* **Date:** 2026-09-15
* **Reason:** Uniform 3D point cloud voxelization exhausts embedded memory bandwidth and limits processing frame rates below real-time thresholds. A multi-tier concentric foveal grid (Inner: 0.05m, Mid: 0.15m, Outer: 0.40m) concentrates resolution where obstacles and path curvature demand high fidelity.
* **Impact:** Reduces compute load by up to $60\%$ while maintaining millimetric spatial accuracy in safety-critical vehicle corridors.
* **Status:** FROZEN & IMPLEMENTED

---

### Decision: Parallel Deterministic Coarse Fallback Safety Map
* **Date:** 2026-09-17
* **Reason:** Complex foveation pipelines or sudden dense point bursts can trigger latency spikes. If processing latency exceeds the $100\text{ ms}$ real-time threshold, the vehicle cannot afford to drop safety checks.
* **Impact:** A parallel $1.0\text{ m}$ coarse safety grid runs synchronously. If latency exceeds $100\text{ ms}$, the system immediately swaps output to the coarse map without halting autonomous control.
* **Status:** FROZEN & IMPLEMENTED

---

### Decision: Dual-Objective Risk and Curiosity Uncertainty Scoring
* **Date:** 2026-09-18
* **Reason:** Focusing attention solely on known obstacles creates blind spots in unexplored or shadowed peripheral sectors.
* **Impact:** Foveation scoring linearly combines Hazard Risk ($\alpha = 0.7$) and Observation Uncertainty ($\beta = 0.3$), ensuring the system inspects both imminent dangers and unobserved terrain regions.
* **Status:** FROZEN & IMPLEMENTED

---

### Decision: Temporal Hysteresis Persistence Filter for ROIs
* **Date:** 2026-09-19
* **Reason:** Point cloud sparsity and occlusions cause detected obstacle peak scores to fluctuate across consecutive frames, leading to flickering ROI bounding boxes and unstable tracking.
* **Impact:** ROIs persist for $N = 5$ frames after score drops below threshold, eliminating visual and tracking flicker.
* **Status:** FROZEN & IMPLEMENTED

---

### Decision: Decoupled Python Core Simulation and WebGL 3D Visualization via WebSocket
* **Date:** 2026-09-22
* **Reason:** Tight coupling of simulation physics and rendering inside a single GUI process (e.g., Pygame) degrades simulation timestep determinism and prevents browser-based remote teleoperation.
* **Impact:** The Python backend executes headless physics, perception, and planning at deterministic $30\text{ Hz}$ timesteps, serializing state frames over WebSocket (`ws://localhost:8765`) to an independent React Three Fiber client.
* **Status:** FROZEN & IMPLEMENTED

---

### Decision: Frenet-Frame Polynomial Trajectory Generation with FSM Behavior Arbitration
* **Date:** 2026-09-24
* **Reason:** Cartesian path generation struggles with curved highway roadways and multi-lane boundaries. Frenet frame decomposition $(s, d)$ decouples longitudinal progress from lateral lane-keeping.
* **Impact:** Enables smooth jerk-minimizing quartic/quintic polynomial generation for overtaking, lane centering, and emergency stops.
* **Status:** FROZEN & IMPLEMENTED

---

### Decision: Hybrid Deep Learning Semantic Segmentation (PointNet) & Geometric DBSCAN Clustering
* **Date:** 2026-09-26
* **Reason:** Pure geometric clustering fails to classify object categories, while full deep learning end-to-end models introduce latency and lack explicit bounding box kinematics.
* **Impact:** PointNet provides per-point semantic classes (Road, Vehicle, Pedestrian, Ground) while DBSCAN and an Extended Kalman Filter manage kinematic bounding box tracking and velocity estimation.
* **Status:** FROZEN & IMPLEMENTED
