# Autonomous Vehicle Simulation - System Architecture

## Overview
Full-stack autonomous driving simulation with real-time visualization using Python (CARLA + pygame fallback).

## System Components

### 1. Perception Module
- **Sensor Simulation**: Camera, LiDAR, Radar (via CARLA or synthetic)
- **Object Detection**: 2D/3D bounding boxes, classification
- **Lane Detection**: Polynomial fitting, curvature estimation
- **Sensor Fusion**: Kalman filter for multi-sensor tracking
- **Output**: `PerceptionResult` with objects, lanes, free space

### 2. Planning Module
- **Global Planner**: A* / Dijkstra on road graph (CARLA waypoints)
- **Local Planner**: Frenet frame / Polynomial trajectory optimization
- **Behavior Planner**: FSM (Lane Follow, Lane Change, Stop, Emergency)
- **Output**: `Trajectory` (waypoints, velocities, accelerations)

### 3. Control Module
- **Lateral Control**: Pure Pursuit / Stanley / MPC
- **Longitudinal Control**: PID for speed tracking
- **Output**: `ControlCommand` (steer, throttle, brake)

### 4. Visualization Module
- **Bird's Eye View**: Top-down map with car, objects, planned path
- **Sensor Views**: Camera feed with detections, LiDAR point cloud
- **Debug Panels**: FSM state, control values, metrics
- **Real-time**: 30-60 FPS rendering

### 5. Simulation Core
- **World Manager**: CARLA client or pygame world
- **Vehicle Manager**: Spawn, control, sensor attachment
- **Scenario Manager**: Traffic, pedestrians, weather
- **Data Logger**: Record/replay for debugging

## Data Flow
```
Sensor Data → Perception → Planning → Control → Vehicle
                    ↓
            Visualization (parallel)
```

## Interfaces
```python
# Perception
class PerceptionModule:
    def process(sensor_data) -> PerceptionResult

# Planning
class PlanningModule:
    def plan(perception, vehicle_state, mission) -> Trajectory

# Control
class ControlModule:
    def compute(trajectory, vehicle_state) -> ControlCommand

# Visualization
class Visualizer:
    def render(world_state, perception, trajectory, control)
```

## Configuration
- YAML configs for each module
- Scenario definitions (JSON)
- Tunable parameters for PID, planner weights, etc.