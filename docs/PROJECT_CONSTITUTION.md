# Project Constitution: Adaptive Variable Resolution 2.5D LiDAR Mapping System

**Document Authority:** Principal Robotics Systems Architect  
**Classification:** Level 1 Authority (Highest Governance Document)  
**Status:** RATIFIED & IN EFFECT  
**Effective Date:** September 29, 2026  

---

## Core Principle

All engineering and development activities in this repository strictly adhere to the following governance chain:

$$\text{Human Intent} \longrightarrow \text{Architecture Authority} \longrightarrow \text{Controlled Implementation} \longrightarrow \text{Validation} \longrightarrow \text{Release}$$

No autonomous agent, developer, script, or automated process may bypass, alter, or reorder any link in this chain.

---

## 1. Project Identity

### 1.1 Problem Statement Metadata
* **Problem Statement ID:** 26053
* **Title:** Adaptive Variable Resolution 2.5D LiDAR Mapping for Dynamic Environment Perception
* **Organization:** Defence Research and Development Organisation (DRDO)
* **Department:** Department of Defence R&D
* **Category:** Software
* **Theme:** Smart Vehicles

### 1.2 Purpose & Context
This project exists to develop a software framework that transforms raw 3D LiDAR point clouds into an adaptive variable-resolution semantic 2.5D representation for autonomous vehicle perception. It operates within the scope of smart vehicle navigation where computational efficiency and reliable spatial awareness must be achieved concurrently.

---

## 2. Core Mission

### 2.1 The Fundamental Trade-Off
Modern autonomous systems rely heavily on 3D LiDAR for rich spatial information. However, uniform point cloud processing imposes a fundamental engineering trade-off:

```
    High-Resolution 3D Mapping
    ├── High Spatial Accuracy
    └── High Computational & Memory Latency Cost

                   vs.

    Low-Resolution 2D Mapping
    ├── Low Computational Cost
    └── Severe Information Loss (Height, Curbs, Potholes, Overhangs, Terrain Slope)
```

### 2.2 Mission Objective
The core mission of the project is to solve this trade-off by developing a perception system that balances:
1. **Perception Accuracy:** Retaining critical elevation, obstacle boundaries, and semantic classifications.
2. **Computational Efficiency:** Reducing processing load through intelligent spatial prioritization.
3. **Memory Efficiency:** Eliminating uniform high-density volumetric overhead.
4. **Real-Time Operation:** Ensuring predictable, deterministic execution suitable for autonomous navigation.

This is achieved through:
* Semantic understanding of LiDAR point clouds.
* Adaptive spatial resolution scaling with distance and hazard relevance.
* Elevation-aware 2.5D mapping preserving terrain structure.
* Dynamic environment awareness separating static and moving entities.

---

## 3. System Philosophy

The system adopts a bio-inspired foveated perception philosophy modeled on human vision:

* **Near the Vehicle (Foveal Focus):**
  * High resolution.
  * Detailed elevation and surface slope information.
  * Precise obstacle and boundary understanding.
* **Far from the Vehicle (Peripheral Awareness):**
  * Reduced spatial resolution.
  * Substantially lower computational and memory overhead.
  * Preserved topological and scene awareness.

```
                  FAR DISTANCE
            [ Coarse Resolution Cells ]
            ├── Low Compute Footprint
            └── Scene Awareness Preserved

                   MID RANGE
            [ Intermediate Resolution ]
            └── Approaching Object Detection

                  NEAR VEHICLE
            [ Fine Resolution Cells ]
            ├── Detailed Elevation & Curbs
            └── Precise Hazard Understanding
```

*Note on Spatial Parameters:* Representative problem statement references cite fine near-field resolution and coarse far-field coverage. Specific grid bounds, cell dimensions, and transition thresholds are implementation-defined and officially recorded in `docs/ARCHITECTURE_FREEZE.md`.

---

## 4. What the Project Is

The project is explicitly defined as:
* **A Dynamic Environment Perception Framework:** Capable of separating static infrastructure from dynamic obstacles and managing risk in evolving scenes.
* **A Semantic 2.5D Mapping System:** Combining surface elevation, occupancy, class semantics, and observation uncertainty into a structured 2.5D representation.
* **An Adaptive Spatial Representation System:** Dynamically allocating spatial fidelity where perception accuracy is safety-critical.

---

## 5. What the Project Is Not

To prevent architectural drift and scope creep, the project is explicitly NOT:
* **NOT a Generic Object Detector:** The objective is not isolated 2D/3D bounding box generation disconnected from terrain elevation and spatial mapping.
* **NOT a Conventional Flat 2D Occupancy Grid Mapper:** The system strictly rejects flat binary grids that discard elevation, ground clearance, and 3D surface features.
* **NOT a Pure LiDAR Visualization Tool:** The system is an active algorithmic perception engine; visualization exists solely to inspect and verify internal semantic states.
* **NOT a Simple Point Cloud Classifier:** Point labeling is an intermediate step feeding the adaptive 2.5D map, not the terminal output of the system.

---

## 6. Architectural Pillars

The project architecture is organized around four core pillars. The constitution defines their purpose; specific algorithmic and model selections are governed by `docs/ARCHITECTURE_FREEZE.md`.

### Pillar 1: Deep Learning Perception Pipeline
* **Purpose:** Convert raw 3D LiDAR point clouds into semantic information.
* **Scope:** Point cloud feature extraction, semantic segmentation, and terrain/object classification (drivable surface, non-drivable obstacles, static structures, dynamic entities).
* **Governance Boundary:** The constitution mandates a deep learning based semantic perception capability. Specific model architectures (e.g., PointNet, PointNet++, Sparse CNNs) are implementation choices specified in the frozen architecture.

### Pillar 2: Variable Resolution 2.5D Mapping Engine
* **Purpose:** Generate and maintain the adaptive 2.5D spatial representation.
* **Scope:** Multi-resolution spatial indexing where cell resolution adapts with distance and hazard priority; projection of 3D semantic points into elevation surfaces preserving height, occupancy, semantics, and uncertainty.
* **Governance Boundary:** The mapping engine must implement distance-varying resolution. Concrete ring geometries, data structures, and memory layouts are frozen in `docs/ARCHITECTURE_FREEZE.md`.

### Pillar 3: Real-Time Visualization Layer
* **Purpose:** Provide clear, real-time inspection of the internal state.
* **Scope:** Visual demonstration of semantic elevation layers, drivable versus non-drivable terrain separation, dynamic object states, and adaptive resolution behavior.
* **Governance Boundary:** The layer must reflect actual pipeline outputs. Specific visualization technologies (desktop GUI, WebGL, or ROS2 tools) are defined at implementation level.

### Pillar 4: Performance Evaluation Framework
* **Purpose:** Provide objective, quantitative measurement of system efficiency.
* **Scope:** Systematic benchmarking of:
  * Processing latency.
  * Frame throughput.
  * Memory footprint and reduction relative to uniform grids.
  * Semantic segmentation and classification accuracy.
* **Governance Boundary:** Specific numerical targets and pass/fail thresholds are defined in validation documentation (`docs/VALIDATION_PROTOCOL.md`).

---

## 7. System Authority Hierarchy

A strict five-tier authority hierarchy governs this repository. Lower levels may not silently, implicitly, or unilaterally contradict higher levels:

```
┌────────────────────────────────────────────────────────┐
│  LEVEL 1: PROJECT_CONSTITUTION.md                      │
│  Defines: Mission, boundaries, pillars, governance     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  LEVEL 2: ARCHITECTURE_FREEZE.md                       │
│  Defines: Frozen architecture, interfaces, algorithms  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  LEVEL 3: DECISIONS.md                                 │
│  Defines: Approved Architectural Decision Records(ADRs)│
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  LEVEL 4: Task Specifications                          │
│  Defines: Scoped, authorized implementation tasks      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  LEVEL 5: Code Implementation                          │
│  Defines: Source files, configs, scripts, tests        │
└────────────────────────────────────────────────────────┘
```

* **Resolution Rule:** If code (Level 5) conflicts with the frozen architecture (Level 2) or constitution (Level 1), the code is defective by definition.

---

## 8. Development Governance & Workflow

Every engineering task—regardless of scope—must execute through the following six sequential steps:

```
Step 1: Task Definition
        │ (Define explicit scope, inputs, expected outputs)
        ▼
Step 2: Architecture Impact Check
        │ (Verify compliance with ARCHITECTURE_FREEZE.md & CONSTITUTION)
        ▼
Step 3: Implementation
        │ (Apply minimal necessary changes to target files)
        ▼
Step 4: Testing & Verification
        │ (Execute regression suites and record deterministic proof)
        ▼
Step 5: Documentation Update
        │ (Sync relevant markdown specifications)
        ▼
Step 6: Changelog Entry
          (Record task, files touched, and verification outcome in CHANGELOG.md)
```

---

## 9. Agent Operating Philosophy

Artificial Intelligence (AI) agents operating within this repository are designated strictly as **Implementation Assistants**.

### Boundaries
* AI agents are **NOT**:
  * System Architects.
  * Product Owners.
  * Research Directors.
* **Agents May:**
  * Implement clearly specified, pre-approved tasks.
  * Diagnose and repair verified bugs within existing module boundaries.
  * Add unit tests, integration tests, and validation benchmarks.
  * Update documentation to reflect verified implementations.
* **Agents May NOT:**
  * Redesign system architecture.
  * Invent new unapproved packages, modules, or abstractions.
  * Remove existing working functionality or test assertions.
  * Change project direction, scope, or methodology.

---

## 10. Architecture Change Policy

Any proposed change to an interface, topic name, data structure, or module boundary must follow the formal five-step Architecture Change Protocol:

1. **Written Justification:** Document the technical failure, performance bottleneck, or new operational requirement that cannot be satisfied within the existing architecture.
2. **Impact Analysis:** Enumerate all affected ROS2 nodes, Python modules, visualization components, and data structures.
3. **Documentation Update:** Draft proposed revisions to `docs/ARCHITECTURE_FREEZE.md` and record an Architectural Decision Record in `docs/DECISIONS.md`.
4. **Validation Plan:** Define the deterministic benchmarks and regression suites required to prove the modification.
5. **Approval Before Implementation:** Formal authorization must be established prior to committing any code modifications.

---

## 11. Code Ownership & Forbidden Actions

### Code Ownership Rules
All subsystems possess defined architectural boundaries. Any engineer or agent modifying a module must possess complete comprehension of:
* **Inputs:** Data contracts, types, coordinate frames, and message frequencies.
* **Outputs:** Downstream consumers, rate requirements, and error states.
* **Dependencies:** Internal packages, external libraries, and hardware interfaces.
* **Downstream Effects:** Impact on perception latency, mapping accuracy, and system stability.

### Explicitly Forbidden Actions
1. **Random Refactoring:** Cosmetic restructuring, renaming variables across files, or formatting changes that obscure git history.
2. **Dead-Code Guessing:** Deleting code, classes, or functions merely because they appear unused without verifiable proof and architectural clearance.
3. **Interface Mutations:** Modifying ROS2 topic names, message fields, communication schemas, or dataclass definitions without Architectural Review.
4. **Algorithmic Swapping:** Replacing implemented algorithms without formal authorization.
5. **Dependency Bloat:** Introducing unapproved external packages, heavy pip libraries, or unverified runtime binaries.
6. **Duplicate Implementations:** Creating parallel implementations of existing modules rather than maintaining the canonical version.
7. **Debugging Drift:** Modifying overarching architectural patterns or disabling test assertions to make an isolated bug disappear.

---

## 12. Research Integrity Rules

To guarantee scientific rigor and defense-grade engineering standards:
* **Reproducibility:** All algorithmic benchmarks, synthetic datasets, and simulation scenarios must be deterministically reproducible from version-controlled assets.
* **Documented Experiments:** Simulation parameters, seeds, vehicle physical coefficients, and sensor noise models must be recorded explicitly.
* **Traceable Decisions:** All technical tradeoffs must be documented in `docs/DECISIONS.md`.
* **Honest Evaluation:** Performance metrics (FPS, compute latency, obstacle detection accuracy, memory reduction) must reflect actual code execution. Fabricating, exaggerating, or selectively smoothing performance data is strictly forbidden.

---

## 13. Documentation Law

The documentation suite forms an integral part of the engineering system. The following seven documents constitute the official project governance library:

| Document | Authority Level | Mandatory Purpose |
| :--- | :--- | :--- |
| [`docs/PROJECT_CONSTITUTION.md`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/docs/PROJECT_CONSTITUTION.md) | Level 1 | Master project governance, authority hierarchy, and operational rules |
| [`docs/ARCHITECTURE_FREEZE.md`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/docs/ARCHITECTURE_FREEZE.md) | Level 2 | Complete frozen architectural specification and interface contracts |
| [`docs/DECISIONS.md`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/docs/DECISIONS.md) | Level 3 | Architectural Decisions Record (ADR) capturing approved technical choices |
| [`docs/DEVELOPMENT_RULES.md`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/docs/DEVELOPMENT_RULES.md) | Level 3 | Operational rules governing agent and engineer execution |
| `docs/VALIDATION_PROTOCOL.md` | Level 3 | Mandatory test execution protocols, benchmark suites, and thresholds |
| `docs/RELEASE_BASELINE.md` | Level 3 | Official verified software and package baseline releases |
| [`docs/CHANGELOG.md`](file:///c:/Users/Kirito/OneDrive/Desktop/2.5.1/docs/CHANGELOG.md) | Level 3 | Historical chronological audit ledger of all repository modifications |

---

## 14. Future Evolution Policy

The project evolves strictly through:
* **Controlled Improvements:** Optimizing algorithmic efficiency within frozen interface boundaries.
* **Validated Extensions:** Introducing new scenarios, unit tests, or hardware drivers through the formal Architecture Change Protocol.
* **Documented Research Changes:** Transitioning novel perception models into the pipeline with complete comparative benchmarking against existing baselines.

Evolution must always preserve systemic reproducibility, architectural transparency, and backwards compatibility.

---

## 15. Final Declaration

The Adaptive Variable Resolution 2.5D LiDAR Mapping System follows controlled engineering development.

No agent, developer, or automated process may modify the project's architecture, objectives, or core methodology without explicit authorization and documentation.
