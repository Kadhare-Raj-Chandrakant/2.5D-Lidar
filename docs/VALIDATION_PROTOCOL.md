# Validation Protocol & Verification Specification

**Project:** Adaptive Variable Resolution 2.5D LiDAR Mapping System  
**Problem Statement:** DRDO PS 26053 — *Adaptive Variable Resolution 2.5D LiDAR Mapping for Dynamic Environment Perception*  
**Document Authority:** Lead Verification and Validation Engineer  
**Classification:** Level 3 Authority (Verification and Acceptance Baseline)  
**Status:** ACTIVE & MANDATORY  
**Effective Date:** September 29, 2026  

---

## Core Principle

Validation does not prove that a new idea or algorithm is conceptually attractive. Validation proves that:

1. **The implemented system operates strictly as intended.**
2. **Existing functionality and stability are demonstrably preserved.**
3. **Architectural boundaries and frozen interfaces are respected.**
4. **Performance, efficiency, and accuracy claims are objectively measurable.**
5. **Experimental modifications and benchmarks are fully reproducible.**

---

## Authority Order

All verification and validation activities are bound by the project governance hierarchy:

$$\text{PROJECT\_CONSTITUTION.md} \longrightarrow \text{ARCHITECTURE\_FREEZE.md} \longrightarrow \text{VALIDATION\_PROTOCOL.md}$$

Validation cannot approve, certify, or merge any change that contains:
* Architecture violations or unapproved module redesigns.
* Undocumented parameter, algorithmic, or structural modifications.
* Broken or mutated ROS2 topics, message schemas, or communication contracts.
* Unverified performance claims or fabricated capabilities.

---

## 1. Validation Philosophy

The project enforces an **evidence-based engineering standard**. Subjective claims such as `"works"`, `"improved"`, `"faster"`, or `"more accurate"` are formally rejected unless backed by:
* **Quantifiable Measurements:** Timed execution logs, CPU/GPU profiling, or memory footprints.
* **Deterministic Test Logs:** Automated test execution runs with zero assertion errors.
* **Traceable Experimental Records:** Explicitly documented seeds, datasets, parameter manifests, and hardware specifications.
* **Reproducible Test Environments:** Independent re-execution yielding identical pass/fail conclusions.

---

## 2. Validation Scope

The validation framework strictly covers the perception, mapping, and representation boundaries established by DRDO Problem Statement 26053:

### 2.1 Software Environment Validation
* Compatibility verification across target platforms: ROS2 Humble / Iron and clean Linux (Ubuntu 22.04 LTS) environments.
* Verification of Python 3.10+ execution environments and C++ toolchain readiness.
* Workspace dependency resolution without unapproved, extraneous, or bloated external libraries.
* Workspace build reproducibility from version-controlled configuration and package manifests (`package.xml`, `setup.py`, `CMakeLists.txt`, `requirements.txt`).

### 2.2 Core Perception Pipeline Validation
* Verification of raw 3D LiDAR point cloud ingestion (`sensor_msgs/msg/PointCloud2`).
* Continuous execution of preprocessing (NaN/Inf stripping, range bounding, voxel downsampling) without pipeline stalls.
* Preservation of message headers, temporal synchronization, and coordinate frame consistency throughout perception stages.

### 2.3 2.5D Elevation Mapping System Validation
* Accurate spatial aggregation of 3D point clouds into 2.5D surface grids.
* Preservation of micro-terrain elevation, surface roughness, ground clearance, and occupancy states.
* Integration of semantic classification layers into grid coordinate cells.

### 2.4 Adaptive Resolution System Validation
* Distance-adaptive and hazard-adaptive spatial scaling (fine near-field resolution transitioning to coarse far-field resolution).
* Strict absence of spatial alignment errors, coordinate skew, or boundary discontinuities across resolution transition zones.
* Zero data loss or volumetric distortion during 3D-to-2.5D projection.

### 2.5 Semantic Perception Validation
* Deep learning semantic inference on point cloud structures.
* Separation of drivable terrain surfaces from non-drivable obstacles and negative hazards.
* Multi-class semantic consistency across implemented classes.

### 2.6 Dynamic Tracking & Lifecycle Validation (Conditional)
* *Applicability:* Enforced only if dynamic object tracking is part of the implemented pipeline.
* Verification of spatial clustering, data association, and state estimation.
* Stable lifecycle state transitions (initialization, confirmation, track maintenance, and pruning).
* Velocity prediction and dynamic hazard safety halo projection stability.

### 2.7 System Integration Validation (Downstream Compatibility)
* *Boundary Note:* The core scope of DRDO PS 26053 is perception and mapping; it does NOT mandate vehicle motion planning, behavior state machines, or low-level chassis actuators.
* Where downstream modules exist (such as autonomous trajectory planners, vehicle simulators, or visualization bridges), validation verifies solely the compatibility, frequency stability, and contract compliance of the perception/mapping outputs feeding them.

---

## 3. Validation Hierarchy (The 8 Validation Gates)

Verification progresses sequentially across eight hierarchical levels. A failure at any level halts validation and blocks task acceptance.

```
┌────────────────────────────────────────────────────────┐
│  LEVEL 0: Repository Integrity Validation              │
│  Files present, dependencies intact, git clean         │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  LEVEL 1: Build Validation                             │
│  ROS2 colcon build, CMake, setup.py clean              │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  LEVEL 2: ROS2 Runtime Validation                      │
│  Nodes initialize, topics publish, params load cleanly │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  LEVEL 3: Pipeline Validation                          │
│  End-to-end data flow produces expected outputs        │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  LEVEL 4: Architecture Compliance Gate                 │
│  Verify zero interface drift or boundary violations    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  LEVEL 5: Performance Validation                       │
│  Quantified latency, throughput, memory metrics        │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  LEVEL 6: Regression Validation                        │
│  All existing test assertions pass with zero failures  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  LEVEL 7: Release Acceptance                           │
│  Definition of Done complete; Changelog updated        │
└────────────────────────────────────────────────────────┘
```

### Level 0 — Repository Integrity Validation
Executed prior to introducing or reviewing any implementation change:
* Verify that the repository is in a known, stable git status (`git status`).
* Confirm all mandatory governance documents (`PROJECT_CONSTITUTION.md`, `ARCHITECTURE_FREEZE.md`, `DECISIONS.md`, `DEVELOPMENT_RULES.md`) exist and are unmodified.
* Verify dependency manifests (`package.xml`, `requirements.txt`) have no unauthorized modifications.

### Level 1 — Build Validation
The ROS2 workspace must compile successfully without errors:
* All declared packages build without failure.
* Package dependencies resolve cleanly.
* CMake compilation and Python setup scripts succeed without fatal warnings.
* All declared executables are generated.
* *Failure Rule:* Any build failure immediately blocks task acceptance.

### Level 2 — ROS2 Runtime Validation
Verify node instantiation and communication topology:
* All declared ROS2 nodes start and initialize without unhandled exceptions.
* Subscribed and published topics match the frozen specification (`ros2 topic list`).
* Expected messages flow at nominal publish rates (`ros2 topic hz`).
* Node parameters load completely from their respective configuration manifests.
* Coordinate transform trees (`tf2`) provide required frames without lookup timeouts.
* *Required Artifacts:* Launch execution logs, node list dumps, and topic verification outputs.

### Level 3 — Pipeline Validation
Validates complete end-to-end data flow:

$$\text{LiDAR Input} \longrightarrow \text{Preprocessing} \longrightarrow \text{Semantic Processing} \longrightarrow \text{2.5D Grid Generation} \longrightarrow \text{Adaptive Foveation} \longrightarrow \text{Visualization / Output}$$

* Every pipeline stage must receive valid inputs, execute within budget, and emit valid outputs.
* Output representations match expected spatial coordinate boundaries.

### Level 4 — Architecture Compliance Gate
Before accepting any code modification, the validator verifies:
* Does this change modify any ROS topic name, message type, or service signature?
* Does this change alter module boundaries, file locations, or ownership contracts?
* Does this change swap or replace an approved core algorithm?
* Does this change mutate shared data structures, schemas, or coordinate frames?
* Does this change introduce unapproved assumptions or scope creep?
* *Gate Rule:* If the answer to any question is **YES**, the task is rejected unless supported by an approved Architectural Decision Record (`docs/DECISIONS.md`) and pre-authorized revision to `docs/ARCHITECTURE_FREEZE.md`.

### Level 5 — Performance Validation
Quantified measurement of computational and perception metrics:
* Processing latency and throughput recorded under nominal and high-density point loads.
* CPU, GPU, and RAM/VRAM footprints measured.
* Memory efficiency documented relative to uniform high-resolution grids.
* Semantic accuracy evaluated on benchmark datasets.

### Level 6 — Regression Validation
Whenever any source file or configuration is modified:
* Existing functionality remains fully **Buildable**, **Runnable**, **Compatible**, **Observable**, and **Validated**.
* All automated regression test suites (including repository verification scripts) pass with 100% assertion success.
* No existing capability is disabled, bypassed, or mocked out.

### Level 7 — Release Acceptance
* Formal sign-off verifying that all seven prior gates have passed and the Definition of Done is fully satisfied.

---

## 4. Module-Specific Validation Protocols

### 4.1 LiDAR Pipeline Validation
* **Ingestion Integrity:** Point cloud streaming must ingest all incoming sensor channels without buffer overruns or dropped frames.
* **Coordinate Conventions:** Point coordinates must strictly follow the vehicle/sensor standard (Right-Handed Coordinate Frame: $+X$ forward, $+Y$ left, $+Z$ up).
* **Filtering Accuracy:** NaN, infinite values, and points outside physical sensor range gates must be cleanly stripped.
* **Timestamp Continuity:** Ingested message timestamps must strictly increase monotonically.

### 4.2 2.5D Grid Mapping Validation
* **Elevation Representation:** Grid cell elevation values must correctly reflect terrain height within discrete spatial bounds.
* **Occupancy Handling:** Obstacle presence must trigger occupied cell states only when exceeding configured density thresholds.
* **Roughness Quantification:** Surface roughness (elevation variance) must differentiate smooth surfaces from rugged terrain obstacles.
* **Spatial Consistency:** Projection from 3D world space to 2D grid coordinates must execute without spatial alignment errors, coordinate skew, or boundary wrap-around defects.

### 4.3 Foveation Logic Validation
* **Adaptive Resolution Behavior:** Resolution and processing focus must adapt dynamically according to distance and hazard priority.
* **Information Preservation:** Foveated spatial downsampling must never destroy safety-critical obstacles within the vehicle navigation corridor.
* **Temporal Stability:** Extracted Regions of Interest (ROIs) must maintain temporal persistence across consecutive frames, eliminating transient ROI dropping or flickering.
* **Degradation Under Constraints:** Under severe computational constraints or latency spikes, the system must execute graceful degradation to a coarse fallback safety representation without halting processing.
* *Note:* Concrete parameter values (hysteresis frame count, fallback map resolution, latency thresholds) are implementation-defined and frozen in `docs/ARCHITECTURE_FREEZE.md`.

### 4.4 Semantic Perception Validation
* **Semantic Label Generation:** The deep learning pipeline must generate valid class predictions matching the implemented semantic categories.
* **Classification Pipeline Execution:** Inference executes deterministically on identical point cloud inputs.
* **Class Scope Rule:** Validation checks implemented classes only. The protocol does not mandate or evaluate classes that are not part of the frozen implementation.

### 4.5 Tracking and Lifecycle Validation (Conditional)
* *Applicability:* Required only if object tracking is part of the frozen architecture.
* **Track Association:** Existing object tracks must maintain spatial continuity across successive sensor frames.
* **Kinematic Plausibility:** Object velocities must be smooth, physically feasible, and free from discontinuous position teleportation.
* **Lifecycle Management:** Object initialization, confirmation, and track removal/pruning upon sensor loss must execute cleanly without memory leaks.

---

## 5. Performance Validation Framework

All performance evaluations must be conducted under controlled, recorded conditions. Performance metrics fall into three categories:

### 5.1 Computational Performance Metrics
* **Processing Latency:** Per-frame computation time for preprocessing, mapping, semantic inference, and foveation scoring.
* **Frame Throughput (FPS):** System pipeline operating frequency under nominal and worst-case obstacle densities.
* **Resource Utilization:** CPU core load, GPU inference occupancy, and memory bandwidth consumption.
* **Memory Footprint:** Peak RAM and VRAM utilization; memory savings relative to uniform high-resolution 3D voxel grids must be quantitatively reported.

### 5.2 Perception Performance Metrics
* **Semantic Segmentation Accuracy:** Mean Intersection-over-Union (mIoU) and per-class classification accuracy.
* **Obstacle Detection Precision / Recall:** True positive versus false positive rates on detected obstacle boundaries.

### 5.3 Mapping Performance Metrics
* **Map Update Frequency:** Real-time refresh rate of the 2.5D elevation and occupancy layers.
* **Representation Efficiency:** Spatial coverage area versus memory byte consumption ratio.

---

## 6. Regression Testing Policy

Whenever code is modified, existing functionality must remain:

* **✓ Buildable:** Zero new compilation warnings or build failures.
* **✓ Runnable:** Nodes and executables launch and spin without unhandled runtime exceptions.
* **✓ Compatible:** Topic names, message definitions, parameters, and communication schemas remain strictly backwards compatible.
* **✓ Observable:** Visualization outputs accurately display pipeline states.
* **✓ Validated:** All automated regression checks pass $100\%$ of assertion tests.

---

## 7. Change Validation Requirement (CVR)

Every code commit, bug fix, or feature enhancement must include an explicit **Change Validation Record** in the task documentation or PR description:

```markdown
### Change Validation Record (CVR)
* **Change:** [Concise description of the specific modification]
* **Reason:** [Technical justification or defect report reference]
* **Affected Modules:** [Explicit list of modified files and downstream consumers]
* **Expected Behaviour:** [Concrete statement of intended outcome]
* **Validation Performed:** [Explicit description of tests run, e.g., regression suite, ROS launch]
* **Evidence:** [Terminal output log, assertion pass count, or benchmark metrics]
```

---

## 8. Experimental Validation & Research Protocol

To protect the integrity of defense research and prevent unverified algorithmic churn:
1. **Experiment Declaration:** Any research variant (e.g., evaluating alternative neural architectures or novel foveation formulas) must define an explicit experimental objective before running trials.
2. **Recorded Configuration:** All experimental runs must log sensor parameters, seed values, and dataset splits.
3. **Traceable Results:** Quantitative outcomes must be recorded and archived.
4. **No Unofficial Ingestion:** Experimental code must never be merged into the frozen core pipeline until it passes the complete Level 0–7 validation protocol and receives formal Architectural Decision Record (`docs/DECISIONS.md`) ratification.

---

## 9. Validation Failure Policy

If a task or modification fails validation at any level:

1. **Immediate Rejection:** The task cannot be marked completed or accepted into the baseline.
2. **Remediation Options:**
   * **Revert:** Revert the changes immediately to the last known stable checkpoint (`git reset` or rollback script).
   * **Correct:** Correct the defect within the scoped module boundaries and re-execute Level 0–7 validation from the beginning.
   * **Document as Unresolved:** If the issue represents an existing platform limitation, document it formally in Section 14 of `docs/ARCHITECTURE_FREEZE.md`.

---

## 10. Definition of Done (DoD)

A development task is officially considered **DONE** only when all of the following conditions are satisfied:

- [ ] **Implementation Complete:** Code strictly addresses the scoped task without collateral refactoring.
- [ ] **Build Successful:** Level 1 build checks pass with zero errors.
- [ ] **Runtime Verified:** Level 2 node lifecycle and topic publication confirmed.
- [ ] **Pipeline Validated:** Level 3 end-to-end data flow produces expected outputs.
- [ ] **Architecture Compliant:** Level 4 architecture gate confirms zero interface drift.
- [ ] **Performance Checked:** Level 5 computational and memory metrics satisfy requirements.
- [ ] **Regression Clean:** Level 6 regression checks pass with $100\%$ assertions.
- [ ] **Documentation Updated:** Governance documents (`ARCHITECTURE_FREEZE.md`, `DECISIONS.md`, etc.) synced if interfaces were touched.
- [ ] **Changelog Logged:** Detailed entry recorded in [`docs/CHANGELOG.md`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/docs/CHANGELOG.md).

---

## 11. Validation Ownership

* **Developer / AI Agent:** Responsible for writing clean code, preventing collateral modifications, and providing concrete terminal/measurement evidence of verification.
* **Architect:** Responsible for enforcing compliance with `docs/PROJECT_CONSTITUTION.md` and verifying interface immutability via Level 4 compliance checks.
* **Validator:** Responsible for independently evaluating evidence, running regression tests, and granting formal acceptance.

---

## 12. Final Declaration

The Adaptive Variable Resolution 2.5D LiDAR Mapping System follows evidence-based validation.

No implementation is considered complete without verification of correctness, stability, and compatibility with the frozen architecture.
