import { create } from 'zustand'
import { getLaneWorldPos } from '../utils/roadGeometry'

const initialVehicleState = {
  x: 0,
  y: 1.75, // Centered in Lane 3 between dashed line 0.0 and 3.5
  yaw: 0,
  speed: 13.5, // ~49 km/h
  acceleration: 0.12,
  steer_angle: 0.0,
  timestamp: Date.now() / 1000,
}

const initialBehavior = {
  state: 'lane_follow',
  target_speed: 13.88, // 50 km/h
  target_lane: 1,
}

const initialTrajectory = {
  waypoints: Array.from({ length: 24 }, (_, i) => ({
    x: (i + 1) * 2.5,
    y: 1.75,
    speed: 13.5,
  })),
  valid: true,
  planning_time: 0.0038,
}

const initialPerception = {
  objects: [
    {
      id: 1,
      track_id: 1,
      confidence: 0.95,
      speed: 4.0,
      bbox_3d: { x: 55, y: 1.75, z: 0, width: 2.2, height: 2.6, length: 6.5, yaw: 0, class_name: 'truck' }
    },
    {
      id: 2,
      track_id: 2,
      confidence: 0.92,
      speed: 10.5,
      bbox_3d: { x: 90, y: 5.25, z: 0, width: 1.9, height: 1.5, length: 4.5, yaw: 0, class_name: 'car' }
    },
    {
      id: 3,
      track_id: 3,
      confidence: 0.89,
      speed: 4.5,
      bbox_3d: { x: 165, y: 1.75, z: 0, width: 1.8, height: 1.4, length: 4.3, yaw: 0, class_name: 'car' }
    },
    {
      id: 4,
      track_id: 4,
      confidence: 0.84,
      speed: 10.0,
      bbox_3d: { x: -50, y: -5.25, z: 0, width: 1.9, height: 1.5, length: 4.6, yaw: 0, class_name: 'car' }
    }
  ],
  lanes: [
    { points: [[-7, -50], [-7, 500]], color: 'yellow', type: 'solid' },
    { points: [[-3.5, -50], [-3.5, 500]], color: 'white', type: 'dashed' },
    { points: [[0, -50], [0, 500]], color: 'white', type: 'dashed' },
    { points: [[3.5, -50], [3.5, 500]], color: 'white', type: 'dashed' },
    { points: [[7, -50], [7, 500]], color: 'yellow', type: 'solid' },
  ],
  free_space: true,
  sensor_data: {
    radar: [
      { x: 45, y: 0, z: 0.5, velocity: 4.5 },
      { x: 70, y: 3.5, z: 0.5, velocity: 11.5 },
    ],
    lidar: []
  }
}

export const useSimulationStore = create((set) => ({
  vehicleState: initialVehicleState,
  perception: initialPerception,
  trajectory: initialTrajectory,
  behavior: initialBehavior,
  trafficSignal: 'green', // 'green' | 'yellow' | 'red'
  activeSignalStation: 55, // s-position of currently active traffic signal
  control: { steer: 0.01, throttle: 0.35, brake: 0 },
  sensorData: null,
  isConnected: false,
  fps: 60,

  setVehicleState: (state) => set({ vehicleState: state }),
  setPerception: (perception) => set({ perception }),
  setTrajectory: (trajectory) => set({ trajectory }),
  setBehavior: (behavior) => set({ behavior }),
  setTrafficSignal: (trafficSignal) => set({ trafficSignal }),
  setActiveSignalStation: (activeSignalStation) => set({ activeSignalStation }),
  setControl: (control) => set({ control }),
  setSensorData: (sensorData) => set({ sensorData }),
  setConnected: (connected) => set({ isConnected: connected }),
  setFPS: (fps) => set({ fps }),
  setFrameData: (frame) => set((prev) => ({ ...prev, ...frame })),

  updateFromMessage: (data) => set((prev) => {
    let vehicleState = prev.vehicleState
    if (data.vehicle_state) {
      const vs = data.vehicle_state
      const egoPos = getLaneWorldPos(vs.x, vs.y)
      vehicleState = {
        ...vs,
        worldX: vs.worldX !== undefined ? vs.worldX : egoPos.worldX,
        worldZ: vs.worldZ !== undefined ? vs.worldZ : egoPos.worldZ,
        yaw: vs.yaw !== undefined ? egoPos.worldYaw + vs.yaw : egoPos.worldYaw,
      }
    }

    let perception = prev.perception
    if (data.perception) {
      perception = {
        ...data.perception,
        objects: (data.perception.objects || []).map((obj) => {
          if (!obj.bbox_3d) return obj
          const objPos = getLaneWorldPos(obj.bbox_3d.x, obj.bbox_3d.y)
          const cls = obj.class_name || obj.bbox_3d.class_name
          const isPed = cls === 'pedestrian' || cls === 'person'
          const pedHeading = isPed 
            ? (objPos.worldYaw + ((obj.bbox_3d.yaw && obj.bbox_3d.yaw > 2.0) ? -Math.PI / 2 : Math.PI / 2))
            : (objPos.worldYaw + (obj.bbox_3d.yaw || 0))
          return {
            ...obj,
            class_name: cls,
            bbox_3d: {
              ...obj.bbox_3d,
              worldX: obj.bbox_3d.worldX !== undefined ? obj.bbox_3d.worldX : objPos.worldX,
              worldZ: obj.bbox_3d.worldZ !== undefined ? obj.bbox_3d.worldZ : objPos.worldZ,
              worldYaw: obj.bbox_3d.worldYaw !== undefined ? obj.bbox_3d.worldYaw : pedHeading,
              isCrossing: obj.bbox_3d.isCrossing !== undefined ? obj.bbox_3d.isCrossing : Math.abs(obj.bbox_3d.y) < 7.5,
              jacketColor: obj.bbox_3d.jacketColor || (obj.id % 2 === 0 ? '#0284c7' : '#ef4444'),
            }
          }
        }),
        lanes: data.perception.lanes || (prev.perception?.lanes || []),
        sensor_data: data.perception.sensor_data || prev.perception?.sensor_data,
      }
    }

    let trajectory = prev.trajectory
    if (data.trajectory) {
      trajectory = {
        ...data.trajectory,
        waypoints: (data.trajectory.waypoints || []).map((wp) => {
          const wpPos = getLaneWorldPos(wp.x, wp.y)
          return {
            ...wp,
            worldX: wp.worldX !== undefined ? wp.worldX : wpPos.worldX,
            worldZ: wp.worldZ !== undefined ? wp.worldZ : wpPos.worldZ,
          }
        })
      }
    }

    return {
      vehicleState,
      perception,
      trajectory,
      trafficSignal: data.traffic_signal || prev.trafficSignal,
      activeSignalStation: data.active_signal_station !== undefined ? data.active_signal_station : prev.activeSignalStation,
      behavior: data.behavior || prev.behavior,
      control: data.control || prev.control,
      sensorData: data.sensor_data || prev.sensorData,
    }
  }),
}))

// Also export as useStore for backwards compatibility
export const useStore = useSimulationStore