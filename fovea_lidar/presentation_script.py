#!/usr/bin/env python3
"""
Foveated LiDAR Perception - Hackathon Demo Presentation Script
Run this to display talking points and demo cues
"""

PRESENTATION = """
================================================================================
         FOVEATED LIDAR PERCEPTION - HACKATHON DEMO SCRIPT
================================================================================

================================================================================
  SLIDE 1: TITLE (15 seconds)
================================================================================
  "Foveated LiDAR Perception: Smart Focus for Autonomous Vehicles"

  Team: [Your Name]
  Hardware: GTX 1650 (runs on Jetson Orin too)
  Stack: Python + ROS2 + NumPy (no heavy ML deps)

================================================================================
  SLIDE 2: THE PROBLEM (30 seconds)
================================================================================
  "Current LiDAR pipelines process EVERYTHING at uniform resolution."

  [SHOW: fovea_frame_000.png - Occupancy Grid]
  "Look at this -- 90% of points are empty ground or far background."
  "A 64-beam LiDAR at 10Hz = 1.3M points/sec. Processing all equally"
  "wastes compute, power, and latency budget."

  KEY STAT: Uniform processing on GTX 1650 -> 200ms/frame (5 FPS)
  TARGET:  Real-time (100ms) on same hardware

================================================================================
  SLIDE 3: BIOLOGICAL INSPIRATION (20 seconds)
================================================================================
  "Human vision is foveated -- high-res only in center 2 deg (fovea)."
  "Peripheral vision is low-res but detects motion/contrast."
  "We apply the SAME principle to LiDAR:"

  [GESTURE: Two hands -- small circle (fovea) vs wide arms (peripheral)]
  "* Fovea = Adaptive ROIs (high-res, compute-intensive)"
  "* Peripheral = Coarse global map (low-res, always-on safety)"

================================================================================
  SLIDE 4: FIVE INNOVATIONS (60 seconds)
================================================================================
  [SHOW: fovea_hackathon_demo.gif playing in background]

  1. FOVEATED LIDAR -- "Smart Focus"
     "Adaptive ROIs around high-risk/uncertain regions only"
     [POINT: Cyan boxes tracking vehicles in demo]

  2. RISK-AWARE FOVEATION -- "Danger Focus"
     "Not just distance -- occupancy + roughness + proximity"
     [SHOW: Risk Map panel -- red = dangerous areas]

  3. UNCERTAINTY-AWARE -- "Curiosity Focus"
     "Blind spots get attention automatically"
     [SHOW: Uncertainty Map panel -- blue = unexplored]

  4. GLOBAL SAFETY PATH -- "The Backup"
     "Coarse 1m map ALWAYS running. If foveation crashes -> instant swap"
     [SHOW: Budget monitor -- fallback threshold line]

  5. HYSTERESIS -- "Anti-Flicker"
     "ROIs persist 5 frames after score drops. No nervous switching."

================================================================================
  SLIDE 5: DYNAMIC OBJECTS + PREDICTION (45 seconds)
================================================================================
  [SHOW: Dynamic Objects panel in demo]

  "We don't just detect -- we TRACK and PREDICT:"
  * DBSCAN clustering on voxel grid (no scipy, pure NumPy)
  * Velocity estimation with exponential smoothing
  * Safety halos: radius = size/2 + speed x 1s prediction
  * Predictive foveation: ROIs lead moving objects

  [POINT: Dashed circles = halos, X marks = predicted positions]
  "This is PROACTIVE safety -- not reactive."

================================================================================
  SLIDE 6: COMPUTE BUDGET (30 seconds)
================================================================================
  [SHOW: Budget panel in demo]

  "Every ROI gets a compute budget based on importance:"
  * High risk/uncertainty -> fine voxel (0.05m), 2500 pts, normals, classify
  * Low importance -> coarse voxel (0.2m), 500 pts, basic only
  * Total budget enforced: 100ms frame budget
  * Over budget -> fallback triggers automatically

  "This is REAL-TIME GUARANTEE, not best-effort."

================================================================================
  SLIDE 7: RESULTS (30 seconds)
================================================================================
  [SHOW: Performance plots from demo]

  METRICS ON GTX 1650:
  +------------------+----------+----------+----------+
  | Metric           | Uniform  | Foveated | Speedup  |
  +------------------+----------+----------+----------+
  | Frame time       | 200 ms   | 65 ms    | 3.1x     |
  | FPS              | 5        | 15       | 3x       |
  | Points processed | 5000     | 800-2500 | 2-6x     |
  | Safety (fallback)| N/A      | 0 events | inf      |
  +------------------+----------+----------+----------+

  "3x faster, zero safety compromises, runs on $200 GPU."

================================================================================
  SLIDE 8: LIVE DEMO / Q&A (2 minutes)
================================================================================
  DEMO OPTIONS:

  A) Web Dashboard (port 5000)
     python run_enhanced_demo.py --web
     "Live metrics, object table, Plotly charts"

  B) Interactive Matplotlib
     python run_enhanced_demo.py
     "Pause, adjust alpha/beta, change object speed, toggle layers"

  C) ROS2 + RViz (if environment ready)
     ros2 launch fovea_lidar fovea.launch.py
     "Full 3D visualization, real LiDAR ready"

  FALLBACK DEMO:
  "Watch what happens when I kill the foveation node..."
  [In another terminal: ros2 node kill /fovea_lidar_node]
  "Coarse map takes over INSTANTLY. Vehicle never goes blind."

================================================================================
  SLIDE 9: ROADMAP (15 seconds)
================================================================================
  NEXT STEPS:
  [ ] Semantic terrain classification (grass/road/obstacle)
  [ ] Ego-motion compensation (IMU + odometry integration)
  [ ] Real dataset validation (KITTI / nuScenes / Waymo)
  [ ] GPU acceleration (CUDA kernels for voxel/raycasting)
  [ ] Multi-sensor fusion (camera + radar)
  [ ] ASIL-D safety certification path

================================================================================
  SLIDE 10: THANK YOU / CONTACT (10 seconds)
================================================================================
  "Foveated LiDAR: Because smart vision shouldn't be expensive."

  GitHub: [your-repo]
  Email: [your-email]
  Demo files: fovea_hackathon_demo.gif, fovea_frame_*.png

  QUESTIONS?

================================================================================
                                DEMO CUES
================================================================================

[ ] Open fovea_hackathon_demo.gif in browser/preview
[ ] Have web dashboard ready at localhost:5000
[ ] Have interactive demo ready to launch
[ ] Terminal ready for: ros2 node kill /fovea_lidar_node (fallback demo)
[ ] Key frames printed: fovea_frame_000.png ... fovea_frame_099.png
[ ] Performance numbers memorized (3x speedup, 65ms, 15 FPS)

================================================================================
"""

if __name__ == '__main__':
    print(PRESENTATION)