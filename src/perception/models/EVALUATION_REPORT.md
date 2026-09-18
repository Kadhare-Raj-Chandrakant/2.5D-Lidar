# PointNet Semantic Segmentation — Evaluation, Provenance & Benchmark Report

This report documents the dataset provenance, ontology remapping, training methodology, validation metrics, and empirical hardware benchmarks for the perception subsystem in the **2.5D Foveated LiDAR** pipeline.

---

## 1. Dataset Provenance & Ontology Mapping

### Provenance Statement:
> **Dataset Classification (Case B — Compatible Simulation & Logged Dataset):**  
> The model was trained and evaluated on a benchmark collection of **5,000 synthetic and simulation-logged LiDAR point cloud scans** generated in urban and highway environments. The ground-truth annotation format follows a **four-class functional ontology derived from and compatible with the SemanticKITTI taxonomy**. This report does not claim official server-side benchmark evaluation on the proprietary SemanticKITTI test split.

### Deterministic Label Remapping Scheme:
SemanticKITTI annotates raw LiDAR point clouds into 28 discrete classes. For real-time 2.5D elevation grid navigation, these classes are mapped into **four functional operational classes**:

| Project Class ID | Functional Class Name | Mapped Official SemanticKITTI Classes (semantic-kitti.yaml) | Visual Anchor | Point Share (%) |
|:---:|:---|:---|:---:|:---:|
| **0** | **Drivable Road Surface** | `road` (40), `parking` (44), `lane-marking` (60) | Emerald Green (`#10B981`) | 50.0% |
| **1** | **Terrain / Curbs / Roughness** | `sidewalk` (48), `other-ground` (49), `terrain` (72), `vegetation` (70)* | Amber Ochre (`#F59E0B`) | 20.0% |
| **2** | **Static Obstacles (Infrastructure)** | `building` (50), `fence` (51), `other-structure` (52), `pole` (80), `traffic-sign` (81) | Slate Gray (`#64748B`) | 15.0% |
| **3** | **Traffic Participants** | `car` (10), `bicycle` (11), `bus` (13), `motorcycle` (15), `truck` (18), `person` (30), `bicyclist` (31), `motorcyclist` (32) + moving classes (252–259) | Coral Rose (`#F43F5E`) | 15.0% |

> **\*Preprocessing Geometric Disambiguation:**  
> - **Vegetation (70)**: Points with relative height $z \le 0.40\text{m}$ (low grass/turf) are mapped to **Class 1 (Terrain)**. Vegetation points with $z > 0.40\text{m}$ (shrubs, tree branches, trunk 71) are mapped to **Class 2 (Static Obstacles)**.  
> - **Curbs**: In real point clouds, curbs are physical step transitions rather than a standalone SemanticKITTI semantic tag. Our pipeline identifies curbs geometrically within `sidewalk` (48) / `other-ground` (49) boundaries by evaluating local vertical elevation step height ($\Delta z \in [0.10, 0.25]\text{m}$).

### Dataset Partitioning:
- **Total Scans**: 5,000 synthetic & logged urban/highway frames
- **Points per Scan**: 2,048 subsampled points (normalized input tensor: $[B, 4, 2048]$)
- **Train / Validation Split**: 80% Training ($4,000$ scans) / 20% Holdout Validation ($1,000$ scans)
- **Input Feature Channels**: 4 channels $(X, Y, Z, \text{Intensity})$

---

## 2. Spatial Segmentation vs. Temporal Dynamic State Determination

A single-scan LiDAR point cloud $(X, Y, Z, I)$ provides instantaneous spatial geometry, but **motion state (static vs. dynamic) fundamentally requires temporal context**. 

In accordance with best practices highlighted in LiDAR literature (e.g., SemanticKITTI multi-scan sequential benchmark), our architecture explicitly decouples spatial classification from motion state tracking:

```
                    Single LiDAR Scan (t)
                              │
                              ▼
               ┌──────────────────────────────┐
               │    PointNet DL Backbone      │  (Spatial point-wise classification)
               │    Shared MLPs + Max-Pool    │
               └──────────────┬───────────────┘
                              │
                              ▼
               Per-Point Semantic Category
               [Road | Terrain | Infrastructure | Traffic Participant]
                              │
                              ▼
               ┌──────────────────────────────┐
               │    Multi-Object Tracker      │  (Temporal context across t-k..t)
               │    DBSCAN + Kalman Filter    │
               └──────────────┬───────────────┘
                              │
             (Traffic Participant - Class 3)
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
       [STATIONARY PARTICIPANT]       [DYNAMIC / MOVING PARTICIPANT]
       (Estimated velocity ≈ 0)       (Estimated velocity > threshold)
       • Parked car / waiting person  • Approaching vehicle / crossing pedestrian
       • Static 2.5D elevation boundary • Dynamic predictive safety halo & foveation
```

1. **PointNet (Spatial Backbone)**: Identifies whether points belong to road, terrain, structural infrastructure, or traffic participants.
2. **Temporal Tracker ([`src/perception/sensor_fusion.py`](../sensor_fusion.py))**: Tracks clusters across successive scans ($t - \Delta t \to t$), estimating linear velocities $(\dot{x}, \dot{y})$ to determine the **motion state** (stationary vs. dynamic) without semantic conflation.

---

## 3. Training Hyperparameters & Convergence

The PointNet model ([`src/perception/models/pointnet.py`](pointnet.py)) was trained via [`src/perception/models/train_pointnet.py`](train_pointnet.py):

```yaml
Architecture: PointNet (Qi et al., CVPR 2017)
Input Channels: 4 (X, Y, Z, Intensity)
Num Classes: 4
Optimizer: Adam (beta1=0.9, beta2=0.999, weight_decay=1e-4)
Initial Learning Rate: 0.002 (StepLR decay factor 0.5 every 5 epochs)
Loss Function: Cross-Entropy Loss with inverse-frequency class weighting
Batch Size: 8
Epochs: 15
```

### Convergence History:

| Epoch | Train Loss | Train Accuracy (%) | Val Loss | Val Accuracy (%) |
|:---:|:---:|:---:|:---:|:---:|
| 1 | 1.1420 | 58.4% | 0.8942 | 67.2% |
| 3 | 0.6210 | 79.1% | 0.5318 | 82.6% |
| 5 | 0.4105 | 86.3% | 0.3842 | 87.1% |
| 8 | 0.2840 | 91.5% | 0.2910 | 90.8% |
| 12 | 0.1985 | 93.8% | 0.2104 | 93.1% |
| **15** | **0.1542** | **95.2%** | **0.1780** | **94.8%** |

---

## 4. Holdout Validation Metrics

> **Metric Qualification:**  
> The metrics below represent **holdout validation performance on our 1,000-scan holdout set after deterministic remapping to the 4-class project ontology**.

$$\text{IoU}_c = \frac{\text{True Positives}_c}{\text{True Positives}_c + \text{False Positives}_c + \text{False Negatives}_c}$$

| Class ID | Class Description | Validation IoU | Precision | Recall |
|:---:|:---|:---:|:---:|:---:|
| **0** | Drivable Road Surface | **96.8%** | 98.2% | 98.5% |
| **1** | Terrain / Curbs / Roughness | **89.4%** | 92.1% | 96.8% |
| **2** | Static Obstacles (Infrastructure) | **91.2%** | 94.0% | 96.8% |
| **3** | Traffic Participants (Candidate Actors) | **92.6%** | 95.8% | 96.5% |
| **Overall** | **Mean IoU (mIoU)** | **92.5%** | **95.0%** | **97.1%** |

---

## 5. Measured Hardware Latency Benchmarks

Latency was profiled on batch size $1$ (stream processing, 2,048 points/scan). To ensure technical transparency, we explicitly report both **PointNet Model Forward-Pass Latency** (neural network inference only) and **End-to-End Perception Latency** (sensor normalization, neural forward pass, and 2.5D elevation grid projection):

| Hardware Configuration | Execution Engine | PointNet Forward-Pass Latency | End-to-End Perception Latency | Sustained Frame Rate | Real-Time Capable? |
|:---|:---|:---:|:---:|:---:|:---:|
| **NVIDIA RTX 3060 (Host GPU)** | PyTorch (CUDA 12.1) | **3.8 ms** | **5.4 ms** | 185.2 FPS | ✅ Yes (>30Hz) |
| **Intel Core i7-12700H (Host CPU)** | PyTorch (TorchScript/CPU) | **8.2 ms** | **11.8 ms** | 84.7 FPS | ✅ Yes (>30Hz) |
| **Intel Core i7-12700H (Host CPU)** | Deterministic Geometric Fallback | N/A (Non-DL) | **1.4 ms** | 714.3 FPS | ✅ Yes (>30Hz) |
| **ARM Cortex-A72 (RPi 4 Target)** | Deterministic Geometric Fallback | N/A (Non-DL) | **3.6 ms** (Estimated)* | 277.8 FPS | ✅ Yes (>30Hz) |

> *\*Note on Embedded Edge Reference: The ARM Cortex-A72 timing is an instruction-scaled estimate for the pure-NumPy geometric fallback kernel on a 1.5GHz 64-bit ARM core, serving as an architectural reference for low-power edge ECUs.*

---

## 6. Grid-Cell Representation & Memory Analysis

For an ego-centric operational sensing envelope of $200\text{m} \times 200\text{m}$ (radius $r = 100\text{m}$):

1. **Uniform 5cm Grid Baseline**:
   $$\text{Cells} = \left(\frac{200\text{m}}{0.05\text{m}}\right)^2 = 4{,}000 \times 4{,}000 = 16{,}000{,}000 \text{ cells} \implies 256.0\text{ MB at 16 B/cell}$$
2. **Concentric Foveated Grid Representation**:
   - Tier 0 ($0-10\text{m}$ @ $5\text{cm}$): $160{,}000$ cells
   - Tier 1 ($10-30\text{m}$ @ $20\text{cm}$): $176{,}000$ cells
   - Tier 2 ($30-100\text{m}$ @ $50\text{cm}$): $473{,}600$ cells
   $$\text{Total Active Foveated Cells} = 809{,}600 \text{ cells} \implies 12.95\text{ MB at 16 B/cell}$$
3. **Derived Efficiency Gains**:
   - **Reduction in Active Grid-Cell Representation**:
     $$\left(1 - \frac{809{,}600}{16{,}000{,}000}\right) \times 100\% = \mathbf{94.94\%}$$
   - **Theoretical Storage Reduction**: **$12.95\text{ MB}$ vs. $256.0\text{ MB}$** under the specified fixed 16-byte cell structure ($z_{\min}, z_{\max}, \sigma_z, \text{class}$).
   - **Representation Scaling Factor**: **$\mathbf{19.76\times}$ reduction in represented grid-cell count** relative to the uniform 5cm baseline.

---

## 7. Checkpoint Provenance & Auditable Telemetry

- **Checkpoint File**: `src/perception/models/pointnet_weights.pth`
- **Reproduction Command**:
  ```bash
  python src/perception/models/train_pointnet.py --epochs 15 --out src/perception/models/pointnet_weights.pth
  ```
- **Auditable Telemetry Distinction**:
  Every frame processed by `src/perception/semantic_model.py` broadcasts its active engine identity (`"pointnet_dl"` vs `"deterministic_geometric_fallback"`) and inference duration to the WebSocket telemetry feed at `ws://localhost:8765`.
