# Foveated LiDAR Perception - Project Specification

## Vision
Hackathon-winning foveated LiDAR perception: high-res fovea only where
risk/uncertainty demand it, coarse global fallback always on, 15+ FPS on GTX 1650.

## Features (all implemented)
1. Foveated LiDAR (adaptive ROIs) - DONE
2. Risk-aware foveation (occupancy+roughness+proximity) - DONE
3. Uncertainty-aware mapping (curiosity focus) - DONE
4. Global safety path (coarse map + watchdog fallback) - DONE
5. Hysteresis (anti-flicker, 5 frames) - DONE
6. Dynamic objects (DBSCAN + tracking + velocity) - DONE
7. Predictive foveation + safety halos - DONE
8. Compute budget allocation (per-ROI) - DONE

## External repos integrated
- FastDEM: fovea_lidar/fastdem_bridge.py (auto C++/python fallback) + fastdem_pybind/ scaffold
- Offroad-Nav: terrain design in generate_scenario() (hills/rocks/trees/ditches/grass)
- lidar_viewer: fovea_lidar/spectral_viz.py (spectral max/min/avg/density) + CSite*.txt real-data loader

## Entry points
- python run_hackathon_demo.py --mode synthetic|gif|interactive|web|real
- python generate_demo.py  (100-frame hackathon GIF)
- python run_enhanced_demo.py [--web]

## Verified
- All 12 core modules import OK
- Real LiDAR (CSite2/CSite3, 20k pts) runs through pipeline, 12-14 ROIs
- GIF regenerated with new terrain (44MB)
