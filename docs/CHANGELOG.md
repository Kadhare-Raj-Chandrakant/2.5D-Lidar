# Repository Changelog

All notable changes, audits, and governance events for this repository are documented in this file.

### [Simulation Autonomy, Traffic Deduplication & HUD Cleanup] - 2026-09-29

* **Date:** 2026-09-29
* **Task:** Autonomous behavior compliance, multi-sensor deduplication, rendering optimization, and HUD control cleanup.
* **Problems Addressed & Solutions:**
  - **Rule Following & Speed Regulation:** Regulated ego vehicle cruising speed to a realistic ~52 km/h (14.5 m/s), integrated active traffic signal and pedestrian crosswalk stopping into the behavior planning FSM (`src/planning/behavior_planner.py`), enabling smooth deceleration and full stops at red lights and pedestrian crossings before resumption.
  - **Traffic Overlap & Multiplication Fix:** Fixed multi-sensor fusion cross-sensor clustering (`src/perception/sensor_fusion.py`) to associate LiDAR, Radar, and camera returns of the same physical actor into a single track instead of spawning duplicate ghost tracks. Added spatial deduplication in 3D frontend rendering (`web-ui/src/components/Traffic.jsx`).
  - **HUD Autonomy Restoration:** Removed manual action-imposing buttons (`🚦 Pedestrians`, `⚡ Overtake`, `🛣️ 2.5D Grid`, and `⏸️ Pause / ▶️ Resume`) from [`HUD.jsx`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/web-ui/src/components/HUD.jsx), ensuring pure autonomous presentation while retaining non-intrusive camera view selection.
  - **Lag & Performance Optimization:** Quantized elevation grid updates in [`FoveatedGrid25D.jsx`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/web-ui/src/components/FoveatedGrid25D.jsx) to eliminate per-frame mesh re-allocations; optimized shadow map resolutions in [`App.jsx`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/web-ui/src/App.jsx); removed redundant secondary obstacle wireframes; verified locked 60 FPS performance via browser verification.
  - **Runner Port Lookup Fix:** Updated [`run.py`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/run.py) to resolve `netstat.exe` directly via Windows System32 path with stderr suppression.
* **Governance Compliance:** Preserved frozen architecture boundaries, interfaces, and PointNet backbone integrity in accordance with `PROJECT_CONSTITUTION.md` and `ARCHITECTURE_FREEZE.md`.

---

### [Unified Single-Command Runner Baseline] - 2026-09-29

* **Date:** 2026-09-29
* **Task:** Streamlined project startup and orchestration tooling (`run.py`, `run.bat`, `run_project.bat`).
* **Purpose:** Replaced multi-step terminal commands and verbose logging with a unified single-command launcher providing health probing, auto-browser launch, and clean process supervision.
* **Tooling Artifacts:**
  - `run.py` — Unified runner script with automated port release, health checking (WebSocket :8765, HTTP :3000), browser opening, and clean Ctrl+C supervision.
  - `run.bat` / `run_project.bat` — One-click Windows launch shortcuts forwarding CLI flags (`--status`, `--stop`, `--restart`, `--background`).
  - `.logs/` — Directory created and ignored in `.gitignore` for non-intrusive background service logs (`backend.log`, `frontend.log`).
* **Governance Compliance:** Preserves all frozen source code, models, and interfaces in `src/` and `fovea_lidar/` without architectural drift.

---

### [Release Baseline V1.0 Established] - 2026-09-29

* **Date:** 2026-09-29
* **Task:** Created `RELEASE_BASELINE.md`
* **Purpose:** Established V1.0 stable project checkpoint and canonical release baseline under DRDO PS 26053.
* **Release Artifacts Certified:**
  - `docs/RELEASE_BASELINE.md` — Level 3 authority document establishing verified capabilities, subsystem paths, known limitations, and future change policies.
  - Linked to Architecture Freeze V1.0 and Validation Protocol V1.0.

---

### [Architecture Freeze Audit Completed] - 2026-09-29

* **Date:** 2026-09-29
* **Task:** Architecture Freeze Audit Completed
* **Changes:** Validated `ARCHITECTURE_FREEZE.md` against governance documents (`PROJECT_CONSTITUTION.md`, `VALIDATION_PROTOCOL.md`). Added standardized V1.0 Architecture Status freeze header, integrated official DRDO PS 26053 identity metadata, and explicitly decoupled the core perception/mapping pipeline from downstream simulation testbed harnesses in data flow specifications.
* **Result:** Architecture baseline confirmed and frozen.

---

### [System Validation Protocol Baseline] - 2026-09-29

* **Date:** 2026-09-29
* **Task:** Created and refined `VALIDATION_PROTOCOL.md`
* **Purpose:** Established system verification, regression protection, and acceptance framework aligned strictly with DRDO PS 26053 perception and mapping boundaries.
* **Governance Enhancements:**
  - Established the 8-tier Validation Hierarchy (Level 0: Integrity, Level 1: Build, Level 2: Runtime, Level 3: Pipeline, Level 4: Architecture Compliance Gate, Level 5: Performance, Level 6: Regression, Level 7: Release Acceptance).
  - Enforced strict problem statement scoping: removed autonomous vehicle motion control/chassis actuators from core validation, replacing with System Integration Validation for downstream compatibility.
  - Made package/node names implementation-dependent while preserving architectural verification rules.
  - Refined foveation validation to focus on behavior, temporal stability, and graceful degradation, delegating concrete parameters to `ARCHITECTURE_FREEZE.md`.
  - Scoped semantic segmentation validation strictly to implemented classes.
  - Codified the mandatory Definition of Done (DoD) and Change Validation Record (CVR) workflow.
* **Files updated:**
  - `docs/VALIDATION_PROTOCOL.md` — Level 3 authority document.

---

### [Project Constitution & Primary Governance Layer] - 2026-09-29

* **Date:** 2026-09-29
* **Task:** Created and ratified `PROJECT_CONSTITUTION.md`
* **Purpose:** Established project governance, authority hierarchy, and formal alignment with DRDO Problem Statement ID: 26053 (*Adaptive Variable Resolution 2.5D LiDAR Mapping for Dynamic Environment Perception*).
* **Governance Enhancements:**
  - Codified the core 3D vs 2D LiDAR trade-off resolution.
  - Defined explicit positive scoping (Dynamic perception, 2.5D semantic mapping, adaptive spatial engine) and negative scoping (NOT a generic detector, flat mapper, or visualization tool).
  - Codified the 4 architectural pillars: Deep Learning Perception Pipeline, Variable Resolution 2.5D Mapping Engine, Real-Time Visualization Layer, and Performance Evaluation Framework.
  - Applied strict governance boundaries: no model hard-locking, no unverified numerical targets, no assumed deployment constraints, and strict separation between constitutional rules and implementation details.
* **Files updated:**
  - `docs/PROJECT_CONSTITUTION.md` — Level 1 authority document.

---

### [Architecture Freeze & Governance Baseline] - 2026-09-29

* **Date:** 2026-09-29
* **Task:** Architecture Freeze Documentation & Repository Governance Establishment
* **Files inspected:**
  - `fovea_lidar/package.xml`, `fovea_lidar/setup.py`, `fovea_lidar/launch/fovea.launch.py`, `fovea_lidar/config/params.yaml`
  - `fovea_lidar/fovea_lidar/node.py`, `grid_map.py`, `risk.py`, `uncertainty.py`, `foveation.py`, `fallback.py`, `hysteresis.py`, `preprocess.py`, `viz.py`, `benchmark.py`, `synthetic_publisher.py`
  - `src/types.py`, `src/config/settings.yaml`
  - `src/perception/foveated_grid.py`, `lane_detector.py`, `object_detector.py`, `perception_module.py`, `semantic_model.py`, `sensor_fusion.py`, `sensor_simulator.py`, `models/pointnet.py`
  - `src/planning/behavior_planner.py`, `global_planner.py`, `local_planner.py`, `planning_module.py`
  - `src/control/control_module.py`, `lateral_control.py`, `longitudinal_control.py`
  - `src/simulation/scenario.py`, `vehicle.py`, `websocket_server.py`, `world.py`
  - `src/visualization/visualizer.py`, `bird_eye_view.py`, `debug_panel.py`, `sensor_views.py`
  - `web-ui/src/App.jsx`, `web-ui/src/components/*`, `web-ui/src/store/*`, `web-ui/src/hooks/*`, `web-ui/vite.config.js`, `web-ui/package.json`
  - `FastDEM/`, `Offroad-Nav/`, `lidar_viewer/`, `claudedesignskills/`
  - `scripts/build_graph.py`, `scripts/query_graph.py`, `scripts/capture_screenshots.py`, `scripts/record_simulation_video.py`
  - `verify_simulation.py`, `watch_backend.py`, `main.py`, `run_project.bat`, `start_live.bat`, `rollback.bat`
* **Files created:**
  - `docs/ARCHITECTURE_FREEZE.md` — Single source of truth specifying complete frozen system architecture (Sections 1–15).
  - `docs/DECISIONS.md` — Architectural Decisions Record (ADR) documenting 7 key technical decisions.
  - `docs/DEVELOPMENT_RULES.md` — Mandatory agent rules and architectural governance standards.
  - `docs/CHANGELOG.md` — Historical ledger of repository governance events.
* **Changes made:**
  - Documented complete existing system architecture without altering any source code, configuration, ROS2 package, or algorithm.
  - Established frozen interface boundaries and non-negotiable architectural principles.
  - Confirmed zero implementation modifications performed.
