import { useState, useRef, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import { useSimulationStore } from './store/useSimulationStore'
import { Vehicle } from './components/Vehicle'
import { Environment } from './components/Environment'
import { Traffic } from './components/Traffic'
import { SensorVisualization } from './components/SensorVisualization'
import { PlannedPath } from './components/PlannedPath'
import { FoveatedGrid25D } from './components/FoveatedGrid25D'
import { HUD } from './components/HUD'
import { useWebSocket } from './hooks/useWebSocket'
import { getLaneWorldPos, getRoadPoint } from './utils/roadGeometry'

function SceneCamera({ cameraMode, vehicleState }) {
  const { camera } = useThree()
  const controlsRef = useRef()
  const lastCarPos = useRef({ x: 0, z: 0 })
  const initializedOrbit = useRef(false)
  const lookTarget = useRef(new THREE.Vector3(0, 1.2, 0))

  useFrame((_, delta) => {
    // 3D World coordinates of vehicle along curved highway
    const carX = vehicleState?.worldX !== undefined ? vehicleState.worldX : (vehicleState?.y || 0)
    const carZ = vehicleState?.worldZ !== undefined ? vehicleState.worldZ : (vehicleState?.x || 0)
    const carYaw = vehicleState?.yaw || 0

    if (cameraMode === 'chase') {
      initializedOrbit.current = false
      const distBehind = 14
      const height = 5.2
      const forwardX = Math.sin(carYaw)
      const forwardZ = Math.cos(carYaw)

      const targetX = carX - forwardX * distBehind
      const targetY = height
      const targetZ = carZ - forwardZ * distBehind

      // Butter-smooth camera movement and lookAt tracking curving into turns
      camera.position.lerp(new THREE.Vector3(targetX, targetY, targetZ), Math.min(delta * 6, 1))
      lookTarget.current.lerp(new THREE.Vector3(carX + forwardX * 10, 1.2, carZ + forwardZ * 10), Math.min(delta * 8, 1))
      camera.lookAt(lookTarget.current)

      lastCarPos.current = { x: carX, z: carZ }
    } else if (cameraMode === 'topdown') {
      initializedOrbit.current = false
      // Elevated overhead view centered ahead of vehicle for optimal LiDAR radius visibility
      camera.position.lerp(new THREE.Vector3(carX, 42, carZ + 6), Math.min(delta * 6, 1))
      lookTarget.current.lerp(new THREE.Vector3(carX, 0, carZ + 10), Math.min(delta * 8, 1))
      camera.lookAt(lookTarget.current)

      lastCarPos.current = { x: carX, z: carZ }
    } else if (cameraMode === 'grid25d') {
      initializedOrbit.current = false
      // Isometric 50-degree elevated perspective centered on vehicle and 2.5D foveated grid
      const forwardX = Math.sin(carYaw)
      const forwardZ = Math.cos(carYaw)
      const rightX = Math.cos(carYaw)
      const rightZ = -Math.sin(carYaw)

      const targetX = carX - forwardX * 18 - rightX * 8
      const targetY = 22
      const targetZ = carZ - forwardZ * 18 - rightZ * 8

      camera.position.lerp(new THREE.Vector3(targetX, targetY, targetZ), Math.min(delta * 6, 1))
      lookTarget.current.lerp(new THREE.Vector3(carX + forwardX * 8, 0, carZ + forwardZ * 8), Math.min(delta * 8, 1))
      camera.lookAt(lookTarget.current)

      lastCarPos.current = { x: carX, z: carZ }
    } else if (cameraMode === 'orbit') {
      if (controlsRef.current) {
        if (!initializedOrbit.current) {
          // Immediately anchor orbit view on the car
          controlsRef.current.target.set(carX, 0.8, carZ)
          camera.position.set(carX - 8, 6, carZ - 12)
          controlsRef.current.update()
          initializedOrbit.current = true
        } else {
          // Keep orbit controls locked and traveling with the car around turns
          const dx = carX - lastCarPos.current.x
          const dz = carZ - lastCarPos.current.z

          controlsRef.current.target.x = carX
          controlsRef.current.target.y = 0.8
          controlsRef.current.target.z = carZ

          camera.position.x += dx
          camera.position.z += dz

          controlsRef.current.update()
        }
        lastCarPos.current = { x: carX, z: carZ }
      }
    }
  })

  return (
    <OrbitControls
      ref={controlsRef}
      enabled={cameraMode === 'orbit'}
      enableDamping
      dampingFactor={0.08}
      maxDistance={80}
      minDistance={2.5}
      maxPolarAngle={Math.PI / 2 - 0.05}
    />
  )
}

function SceneContent({ cameraMode }) {
  const { vehicleState, perception, trajectory, trafficSignal, activeSignalStation } = useSimulationStore()
  const carWorldX = vehicleState?.worldX !== undefined ? vehicleState.worldX : (vehicleState?.y || 0)
  const carWorldZ = vehicleState?.worldZ !== undefined ? vehicleState.worldZ : (vehicleState?.x || 0)

  return (
    <>
      <color attach="background" args={['#0c1222']} />
      <fog attach="fog" args={['#0c1222', 60, 280]} />

      {/* Cinematic Lighting Setup that follows curved highway with the vehicle */}
      <ambientLight intensity={0.7} />
      <directionalLight
        position={[carWorldX + 35, 80, carWorldZ + 40]}
        intensity={2.2}
        color="#f8fafc"
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
        shadow-camera-left={-70}
        shadow-camera-right={70}
        shadow-camera-top={70}
        shadow-camera-bottom={-70}
      />
      <hemisphereLight groundColor="#1e293b" skyColor="#38bdf8" intensity={0.7} />

      {/* 3D Road and Environment with City Turns, Crosswalks and Traffic Signals (100% Static Track) */}
      <Environment
        signalState={trafficSignal || 'green'}
        activeSignalStation={activeSignalStation || 450}
      />

      {/* Traffic Obstacles */}
      <Traffic vehicles={perception?.objects || []} />

      {/* Ego Autonomous Vehicle */}
      <Vehicle state={vehicleState} />

      {/* LiDAR Radius Field & Sensor suite */}
      <SensorVisualization vehicleState={vehicleState} perception={perception} />

      {/* 2.5D Variable-Resolution Foveated Semantic Elevation Grid & In-Scene Autonomous Corridor */}
      <FoveatedGrid25D
        vehicleState={vehicleState}
        perception={perception}
        cameraMode={cameraMode}
      />

      {/* Planned Trajectory Path */}
      <PlannedPath trajectory={trajectory} />

      {/* Lightweight car shadow — simple blurred ellipse, no framebuffer cost */}
      <mesh position={[carWorldX, 0.03, carWorldZ]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[3.2, 5.5]} />
        <meshBasicMaterial color="#000000" transparent opacity={0.28} />
      </mesh>

      {/* Unified Camera & 3D Orbit Controls */}
      <SceneCamera cameraMode={cameraMode} vehicleState={vehicleState} />
    </>
  )
}

export default function App() {
  const urlParams = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '')
  const initialCam = urlParams.get('cam') || 'chase'

  const [cameraMode, setCameraMode] = useState(initialCam) // 'chase' | 'topdown' | 'orbit' | 'grid25d'

  const { 
    vehicleState, 
    behavior, 
    trafficSignal,
    activeSignalStation,
    isConnected, 
    perception, 
    trajectory, 
    setVehicleState, 
    setTrajectory, 
    setBehavior, 
    setPerception,
    setTrafficSignal,
    setActiveSignalStation,
    setFrameData
  } = useSimulationStore()

  // Connect to Python WebSocket (VITE_WS_URL set in production; localhost fallback for local dev)
  useWebSocket(import.meta.env.VITE_WS_URL || 'ws://localhost:8765')

  // Smooth autonomous simulation & obstacle avoidance loop
  useEffect(() => {
    if (isConnected) return // when connected to Python, Python drives

    let animationFrameId
    let lastTime = performance.now()

    // Autonomous vehicle internal state (driving inside Lane 3, center at Y = 1.75)
    let egoX = vehicleState?.x || 0 // Longitudinal along road (Three.js Z)
    let egoY = vehicleState?.y !== undefined ? vehicleState.y : 1.75 // Lateral (centered between markings 0.0 and 3.5)
    let prevEgoY = egoY  // Track previous lateral position for smooth yaw computation
    let smoothYaw = 0    // Low-pass filtered yaw — natural real-world heading
    let targetLaneY = 1.75 // Cruising lane center (between 0.0 and 3.5)
    const CRUISE_SPEED = 15.5 // 55.8 km/h (~56 km/h brisk, smooth cruising speed)
    let egoSpeed = CRUISE_SPEED
    let currentBehaviorState = 'lane_follow'
    // Hysteresis: prevent lane changes more often than every 4 seconds
    let laneChangeCooldown = 0

    // Periodic Natural Pedestrian Crossing Schedule across the 1200m track loop
    // Scheduled at 55m, 250m, 450m, 950m
    const CROSSING_SCHEDULE = [
      { baseS: 55, id: 90, name: 'Crosswalk #1' },
      { baseS: 250, id: 95, name: 'Crosswalk #2' },
      { baseS: 450, id: 100, name: 'Crosswalk #3' },
      { baseS: 950, id: 110, name: 'Crosswalk #4' },
    ]

    // Green wave bystander stations (standing safely on sidewalk, vehicle cruises past)
    const BYSTANDER_SCHEDULE = [
      { baseS: 200, y: -8.5, jacket: '#10b981', id: 81, name: 'Bystander #1' },
      { baseS: 650, y: 8.5, jacket: '#8b5cf6', id: 82, name: 'Bystander #2' },
    ]

    // Generates a group of 4 pedestrians crossing simultaneously from both sidewalks
    const createPedestrianGroup = (stationS, baseId = 90) => [
      {
        id: baseId + 1,
        name: 'Pedestrian #1',
        x: stationS - 1.1,
        y: -8.8,
        startY: -8.8,
        targetY: 8.8,
        dir: 1, // Left-to-right
        speed: 1.45,
        jacket: '#ef4444', // Red jacket
        state: 'waiting', // 'waiting' | 'crossing' | 'cleared'
      },
      {
        id: baseId + 2,
        name: 'Pedestrian #2',
        x: stationS + 0.7,
        y: -9.8,
        startY: -9.8,
        targetY: 8.8,
        dir: 1,
        speed: 1.25,
        jacket: '#0284c7', // Vibrant blue
        state: 'waiting',
      },
      {
        id: baseId + 3,
        name: 'Pedestrian #3',
        x: stationS + 1.4,
        y: 8.8,
        startY: 8.8,
        targetY: -8.8,
        dir: -1,
        speed: 1.55,
        jacket: '#f59e0b', // Amber jacket
        state: 'waiting',
      },
      {
        id: baseId + 4,
        name: 'Pedestrian #4',
        x: stationS - 0.5,
        y: 9.7,
        startY: 9.7,
        targetY: -8.8,
        dir: -1,
        speed: 1.35,
        jacket: '#10b981', // Emerald green
        state: 'waiting',
      },
    ]

    let currentCrossingS = 55
    let currentSignal = 'green'
    let pedestrians = createPedestrianGroup(55, 90)
    let groupClearTimer = 0

    // Multi-vehicle fleet ahead on the road for active overtaking & decision making showcase:
    let obstacles = [
      { id: 1, class_name: 'truck', x:  95, y:  1.75, speed:  6.0, currentSpeed:  6.0, width: 2.2, height: 2.5, length: 6.2 }, // Slower commercial truck (21 km/h) in cruising lane — 1st overtake!
      { id: 2, class_name: 'car',   x: 145, y: -1.75, speed: 17.0, currentSpeed: 17.0, width: 1.9, height: 1.5, length: 4.5 }, // Passing lane car (61 km/h), ahead with open gap
      { id: 3, class_name: 'car',   x: 195, y:  1.75, speed:  7.5, currentSpeed:  7.5, width: 1.9, height: 1.5, length: 4.5 }, // Cruising lane sedan (27 km/h) — 2nd overtake!
      { id: 4, class_name: 'car',   x:  70, y:  5.25, speed: 11.5, currentSpeed: 11.5, width: 1.9, height: 1.5, length: 4.6 }, // Outer lane companion car (41 km/h)
      { id: 5, class_name: 'car',   x: 240, y:  1.75, speed:  8.5, currentSpeed:  8.5, width: 1.9, height: 1.5, length: 4.5 }, // Ahead before intersection
    ]

    const loop = (time) => {
      const delta = Math.min((time - lastTime) / 1000, 0.05)
      lastTime = time

      // 1. Determine active crossing station ahead of vehicle
      const currentCycle = Math.floor(egoX / 1200)
      let activeCrossingConfig = null
      let minAheadDist = 999999

      for (let c = currentCycle; c <= currentCycle + 1; c++) {
        for (const item of CROSSING_SCHEDULE) {
          const s = c * 1200 + item.baseS
          const distFromCar = s - egoX
          // Active if car is approaching it or within 22m past it
          if (distFromCar > -22 && distFromCar < minAheadDist) {
            minAheadDist = distFromCar
            activeCrossingConfig = { ...item, s, cycle: c }
          }
        }
      }

      if (activeCrossingConfig) {
        // If switched to a new crossing station, initialize new pedestrian group
        if (currentCrossingS !== activeCrossingConfig.s) {
          currentCrossingS = activeCrossingConfig.s
          pedestrians = createPedestrianGroup(activeCrossingConfig.s, activeCrossingConfig.id)
          currentSignal = 'green'
          groupClearTimer = 0
        }

        const relDist = activeCrossingConfig.s - egoX
        const isGroupCleared = pedestrians.every(p => p.state === 'cleared')
        const isAnyPedInRoad = pedestrians.some(p => Math.abs(p.y) < 7.6)

        // Traffic Light & Multi-Pedestrian Phase progression:
        if (relDist > 65) {
          // Distant approach: Green light, pedestrians waiting on sidewalk
          currentSignal = 'green'
          pedestrians.forEach(p => {
            p.state = 'waiting'
            p.y = p.startY
          })
          groupClearTimer = 0
        } else if (relDist <= 65 && relDist > 46) {
          // Yellow early warning phase (giving ample time to prepare smooth deceleration)
          currentSignal = 'yellow'
          pedestrians.forEach(p => {
            p.state = 'waiting'
          })
        } else if (relDist <= 46 && !isGroupCleared) {
          // Red phase: Smooth deceleration runway of 40m, group crosses zebra
          currentSignal = 'red'
          pedestrians.forEach(p => {
            p.state = 'crossing'
            p.y += p.dir * p.speed * delta

            const reachedTarget = p.dir > 0 
              ? p.y >= p.targetY 
              : p.y <= p.targetY

            if (reachedTarget) {
              p.state = 'cleared'
            }
          })
        } else if (isGroupCleared) {
          // Clearance phase: keep RED for 1.4s safety buffer after ALL pedestrians reach sidewalk, then switch to GREEN
          groupClearTimer += delta
          if (groupClearTimer < 1.4) {
            currentSignal = 'red'
          } else {
            currentSignal = 'green'
          }
        }
      }

      // 2. Move other traffic obstacles along the road with Intelligent Driver spacing & Traffic Signal obedience
      obstacles = obstacles.map(obs => {
        let desiredSpeed = obs.speed
        let currentSpd = obs.currentSpeed !== undefined ? obs.currentSpeed : obs.speed

        // A. Check if there is a vehicle ahead in the same lane
        const leader = obstacles.find(other => 
          other.id !== obs.id && 
          Math.abs(other.y - obs.y) < 1.4 && 
          other.x > obs.x && 
          other.x - obs.x < 28
        )

        // Also check if ego vehicle is ahead in the same lane
        const isEgoLeader = Math.abs(egoY - obs.y) < 1.4 && egoX > obs.x && egoX - obs.x < 28

        // B. Traffic Signal & Crosswalk Stop Line Obedience for this obstacle
        const distToSignal = currentCrossingS - obs.x
        const isGroupCrossingInRoad = pedestrians.some(p => Math.abs(p.y) < 7.6)
        const isSignalStopping = currentSignal === 'red' || currentSignal === 'yellow' || isGroupCrossingInRoad

        let signalStopSpeed = 999
        if (isSignalStopping && distToSignal > 6.5 && distToSignal < 65) {
          // Stop line is 7m before crosswalk, target stop is 8.5m before crosswalk
          let targetStopX = currentCrossingS - 8.5

          // If there is already a vehicle stopped ahead before the signal in our lane, queue behind it
          if (leader && leader.x < currentCrossingS && leader.x > obs.x) {
            targetStopX = Math.min(targetStopX, leader.x - 7.5)
          }
          if (isEgoLeader && egoX < currentCrossingS && egoX > obs.x) {
            targetStopX = Math.min(targetStopX, egoX - 7.5)
          }

          const distToStop = targetStopX - obs.x
          if (distToStop > 0.4) {
            signalStopSpeed = Math.min(desiredSpeed, Math.sqrt(Math.max(0, 2 * 3.6 * distToStop)) * 0.9)
            if (distToStop < 1.6 && currentSpd < 1.2) {
              signalStopSpeed = 0
            }
          } else {
            signalStopSpeed = 0
          }
        }

        // C. Combine spacing constraints: leader, ego car, and traffic signal
        if (leader) {
          const leaderSpeed = leader.currentSpeed !== undefined ? leader.currentSpeed : leader.speed
          const gap = leader.x - obs.x - (leader.length || 4.5) / 2 - (obs.length || 4.5) / 2
          if (gap < 2.0) {
            desiredSpeed = 0
          } else {
            desiredSpeed = Math.min(desiredSpeed, leaderSpeed * 0.92, Math.max(0, gap * 0.7))
          }
        }

        if (isEgoLeader) {
          const gap = egoX - obs.x - 4.5
          if (gap < 2.0) {
            desiredSpeed = 0
          } else {
            desiredSpeed = Math.min(desiredSpeed, egoSpeed * 0.92, Math.max(0, gap * 0.7))
          }
        }

        // Apply traffic signal stopping limit
        desiredSpeed = Math.min(desiredSpeed, signalStopSpeed)

        // D. Smooth acceleration / deceleration dynamics for realistic vehicle movement
        let newCurrentSpeed = currentSpd
        if (desiredSpeed < currentSpd) {
          // Smooth braking
          newCurrentSpeed = Math.max(desiredSpeed, currentSpd - 5.5 * delta)
        } else {
          // Smooth accelerating
          newCurrentSpeed = Math.min(desiredSpeed, currentSpd + 2.8 * delta)
        }

        if (desiredSpeed === 0 && (distToSignal > 6.5 && distToSignal < 65 || (leader && (leader.currentSpeed || 0) === 0))) {
          if (newCurrentSpeed < 0.6) newCurrentSpeed = 0
        }

        let newX = obs.x + newCurrentSpeed * delta

        // Respawn obstacle 85-150m ahead once passed so highway is always populated with traffic
        if (newX < egoX - 18) {
          newX = egoX + 85 + (obs.id * 20)
          // Avoid landing directly on a crosswalk stop-line
          if (Math.abs(newX - currentCrossingS) < 22) {
            newX += 35
          }
          newCurrentSpeed = obs.speed
        }

        return { ...obs, x: newX, currentSpeed: newCurrentSpeed }
      })

      // 3. Obstacle detection: find closest vehicle ahead in our lane (look 80m ahead)
      const obstacleAhead = obstacles
        .filter(obs => obs.x > egoX && obs.x - egoX < 80 && Math.abs(obs.y - targetLaneY) < 1.6)
        .sort((a, b) => a.x - b.x)[0]

      const distToObstacle = obstacleAhead ? obstacleAhead.x - egoX : 999
      const obstacleSpeed = obstacleAhead?.currentSpeed ?? obstacleAhead?.speed ?? 0

      // Passing lane clearance: require a safe gap relative to passing lane vehicles
      const safeGapBehind = 16.0
      const safeGapAhead  = 32.0
      const isPassingLaneClear = !obstacles.some(obs => {
        if (Math.abs(obs.y - (-1.75)) > 1.6) return false  // not in passing lane
        const relPos = obs.x - egoX
        if (relPos > 0 && relPos < safeGapAhead)  return true // car ahead in gap
        if (relPos < 0 && relPos > -safeGapBehind) return true // car behind in gap
        return false
      })

      // 4. Pedestrian and Traffic Light Yielding Decision
      const stopLineS = currentCrossingS - 7.0
      const stopTargetS = currentCrossingS - 10.0 // Full stop 3 meters behind white line, 10m before pedestrians

      const isPedInRoad = pedestrians.some(p => Math.abs(p.y) < 7.6)
      const isRedSignal = currentSignal === 'red' || currentSignal === 'yellow'
      const isNearCrosswalk = egoX > currentCrossingS - 65 && egoX < currentCrossingS + 8.0

      // Must yield stays firmly active as long as signal is red/yellow or pedestrians are crossing
      const mustYield = isNearCrosswalk && (isRedSignal || isPedInRoad || (egoX < currentCrossingS - 8.0 && currentSignal !== 'green'))
      const distToStop = stopTargetS - egoX

      // 5. Behavior planning state machine:
      // Tick down lane-change cooldown timer each frame
      laneChangeCooldown = Math.max(0, laneChangeCooldown - delta)

      if (mustYield) {
        currentBehaviorState = isPedInRoad ? 'pedestrian_yield' : 'traffic_light_stop'
      } else {
        if (currentBehaviorState === 'pedestrian_yield' || currentBehaviorState === 'traffic_light_stop') {
          currentBehaviorState = 'lane_follow'
        }

        // Initiate overtake when slower lead obstacle is within 42m in cruising lane
        const isLeadSlow = obstacleAhead && obstacleSpeed < CRUISE_SPEED * 0.85
        if (distToObstacle < 42 && isLeadSlow && targetLaneY === 1.75 && laneChangeCooldown === 0) {
          if (isPassingLaneClear) {
            targetLaneY = -1.75
            currentBehaviorState = 'overtaking'
            laneChangeCooldown = 4.0
          } else {
            currentBehaviorState = 'lane_follow'
          }
        } else if (targetLaneY === -1.75 && laneChangeCooldown === 0) {
          // Return to cruising lane once we've passed the obstacle by 16m
          const passedObstacle = obstacles.find(obs =>
            Math.abs(obs.y - 1.75) < 1.6 && egoX > obs.x + 16 && egoX - obs.x < 90
          )
          const isCruisingLaneClear = !obstacles.some(obs =>
            Math.abs(obs.y - 1.75) < 1.6 && obs.x > egoX - 12 && obs.x - egoX < 32
          )

          if (passedObstacle && isCruisingLaneClear) {
            targetLaneY = 1.75
            currentBehaviorState = 'merge_back'
            laneChangeCooldown = 4.0
          }
        }
      }

      // 6. Natural Autonomous Vehicle Kinematics (Zero crab-walk, zero snapping)
      const laneError = targetLaneY - egoY
      // Smooth lateral translation over ~3.0s (natural real-world lane change)
      prevEgoY = egoY
      egoY += laneError * Math.min(delta * 1.35, 1.0)

      // Heading offset relative to road is directly proportional to lane error, strictly capped at ±3.2 degrees (0.055 rad)
      // Completely eliminates the 70-degree swing and sudden straightening!
      const targetYaw = Math.max(-0.055, Math.min(0.055, laneError * 0.022))
      smoothYaw += (targetYaw - smoothYaw) * Math.min(delta * 4.5, 1.0)

      // Realistic Ackerman front-wheel steering angle (max ±3.5 degrees)
      const steer = Math.max(-0.06, Math.min(0.06, smoothYaw * 0.85))

      // Check sharp turns on 1200m track loop
      const sMod = ((egoX % 1200) + 1200) % 1200
      const isNearSharpTurn = 
        (sMod >= 85 && sMod <= 170) ||
        (sMod >= 305 && sMod <= 390) ||
        (sMod >= 585 && sMod <= 670) ||
        (sMod >= 805 && sMod <= 890)
      const corneringSpeed = 9.5 // ~34 km/h for the highway curves
 
      if (mustYield) {
        // Guaranteed safe deceleration: smoothly stops at stopTargetS (3m behind white line)
        if (distToStop > 0.4) {
          const targetSpd = Math.sqrt(Math.max(0, 2 * 2.0 * Math.max(0, distToStop - 0.2)))
          if (egoSpeed > targetSpd) {
            egoSpeed = Math.max(targetSpd, egoSpeed - 3.2 * delta)
          } else {
            egoSpeed = Math.min(targetSpd, egoSpeed)
          }
          if (distToStop < 1.0 && egoSpeed < 1.2) {
            egoSpeed = 0
            egoX = stopTargetS
          }
        } else {
          // Full stop safely before the line — zero overshoot
          egoSpeed = 0
          egoX = stopTargetS
        }
      } else if (distToObstacle < 24 && Math.abs(egoY - (obstacleAhead?.y || 99)) < 1.8) {
        // Close-range spacing: match obstacle speed safely
        const targetFollowSpeed = Math.max(obstacleSpeed, 4.0)
        egoSpeed = Math.max(targetFollowSpeed, egoSpeed - 2.5 * delta)
      } else if (isNearSharpTurn) {
        if (egoSpeed > corneringSpeed) {
          egoSpeed = Math.max(corneringSpeed, egoSpeed - 2.5 * delta)
        } else {
          egoSpeed = Math.min(corneringSpeed, egoSpeed + 2.2 * delta)
        }
      } else {
        // Free road / Exiting traffic signal — crisp, smooth acceleration to cruise speed
        egoSpeed = Math.min(CRUISE_SPEED, egoSpeed + 2.5 * delta)
      }

      // Autonomous Emergency Braking (AEB) safeguard: guarantees vehicle NEVER touches a pedestrian
      const pedThreat = pedestrians.find(p => 
        p.x > egoX - 1.0 && 
        p.x - egoX < 16.0 && 
        Math.abs(p.y - egoY) < 3.2 && 
        p.state !== 'cleared'
      )
      if (pedThreat) {
        currentBehaviorState = 'pedestrian_yield'
        egoSpeed = 0
        egoX = Math.min(egoX, pedThreat.x - 6.0)
      }

      // Continuous forward travel along the highway
      egoX += egoSpeed * delta

      // World coordinates of ego vehicle following road curvature and lane offset
      const egoPos = getLaneWorldPos(egoX, egoY)
      // Combine road curvature yaw with our smooth body-roll yaw from lateral movement
      const totalYaw = egoPos.worldYaw + smoothYaw

      // 7. Build perception objects for HUD and sensor visualisation
      const pedObjects = pedestrians.map(ped => {
        const pedPos = getLaneWorldPos(ped.x, ped.y)
        const pedHeading = pedPos.worldYaw + (ped.dir > 0 ? Math.PI / 2 : -Math.PI / 2)
        const pedInRoad = Math.abs(ped.y) < 7.6
        return {
          id: ped.id,
          track_id: ped.id,
          confidence: 0.98,
          speed: ped.state === 'crossing' ? ped.speed : 0,
          bbox_3d: {
            x: ped.x, y: ped.y,
            worldX: pedPos.worldX, worldZ: pedPos.worldZ, worldYaw: pedHeading,
            z: 0, width: 0.8, height: 1.8, length: 0.8, yaw: pedHeading,
            class_name: 'pedestrian', isCrossing: pedInRoad, jacketColor: ped.jacket,
          }
        }
      })

      const bystanderObjects = []
      BYSTANDER_SCHEDULE.forEach(b => {
        const s = currentCycle * 1200 + b.baseS
        if (Math.abs(s - egoX) < 70) {
          const bPos = getLaneWorldPos(s, b.y)
          bystanderObjects.push({
            id: b.id, track_id: b.id, confidence: 0.95, speed: 0,
            bbox_3d: {
              x: s, y: b.y,
              worldX: bPos.worldX, worldZ: bPos.worldZ,
              worldYaw: bPos.worldYaw + (b.y > 0 ? -Math.PI / 2 : Math.PI / 2),
              z: 0, width: 0.8, height: 1.8, length: 0.8,
              yaw: bPos.worldYaw + (b.y > 0 ? -Math.PI / 2 : Math.PI / 2),
              class_name: 'pedestrian', isCrossing: false, jacketColor: b.jacket,
            }
          })
        }
      })

      const allObstacleObjects = obstacles.map(obs => {
        const obsPos = getLaneWorldPos(obs.x, obs.y)
        return {
          id: obs.id, track_id: obs.id, confidence: 0.94,
          speed: obs.currentSpeed !== undefined ? obs.currentSpeed : obs.speed,
          bbox_3d: {
            x: obs.x, y: obs.y,
            worldX: obsPos.worldX, worldZ: obsPos.worldZ, worldYaw: obsPos.worldYaw,
            z: 0, width: obs.width, height: obs.height, length: obs.length,
            yaw: obsPos.worldYaw, class_name: obs.class_name,
          }
        }
      })

      const perceptionObjects = [...allObstacleObjects, ...pedObjects, ...bystanderObjects]

      // Radar detections (vehicles + pedestrians within 55m)
      const radarDetections = obstacles
        .filter(obs => Math.abs(obs.x - egoX) < 55)
        .map(obs => {
          const obsPos = getLaneWorldPos(obs.x, obs.y)
          return { x: obsPos.worldX, y: obsPos.worldZ, velocity: obs.currentSpeed ?? obs.speed }
        })
      pedestrians.forEach(ped => {
        if (Math.abs(ped.x - egoX) < 55) {
          const pedPos = getLaneWorldPos(ped.x, ped.y)
          radarDetections.push({ x: pedPos.worldX, y: pedPos.worldZ, velocity: ped.state === 'crossing' ? ped.speed : 0 })
        }
      })
      bystanderObjects.forEach(b => {
        if (Math.abs(b.bbox_3d.x - egoX) < 55) {
          radarDetections.push({ x: b.bbox_3d.worldX, y: b.bbox_3d.worldZ, velocity: 0 })
        }
      })

      // 8. Generate smooth trajectory waypoints curving along the road
      const maxPathDist = mustYield ? Math.min(stopTargetS, egoX + 32) : egoX + 60
      const waypoints = Array.from({ length: 24 }, (_, i) => {
        const wpDist = Math.min(maxPathDist, egoX + (i + 1) * 2.5)
        // S-curve interpolation between current egoY and targetLaneY
        const progress = Math.min(1, Math.max(0, (wpDist - egoX) / 28))
        const smoothProgress = progress * progress * (3 - 2 * progress)
        const wpY = egoY + (targetLaneY - egoY) * smoothProgress

        const wpPos = getLaneWorldPos(wpDist, wpY)

        return {
          x: wpDist, // longitudinal
          y: wpY,    // lateral
          worldX: wpPos.worldX,
          worldZ: wpPos.worldZ,
          worldYaw: wpPos.worldYaw,
          speed: mustYield ? 0 : egoSpeed,
        }
      })

      // 9. Determine behavior state
      const activeState = mustYield 
        ? currentBehaviorState 
        : (currentBehaviorState !== 'lane_follow' 
            ? currentBehaviorState 
            : (isNearSharpTurn ? 'sharp_turn' : 'lane_follow'))

      // 10. Single batched state dispatch to avoid 6 separate React dispatches per frame (60 FPS locked)
      setFrameData({
        trafficSignal: currentSignal,
        activeSignalStation: activeCrossingConfig ? activeCrossingConfig.s : 450,
        vehicleState: {
          x: egoX,
          y: egoY,
          worldX: egoPos.worldX,
          worldZ: egoPos.worldZ,
          yaw: totalYaw,
          speed: egoSpeed,
          acceleration: mustYield ? -2.8 : (steer !== 0 ? 0.35 : (isNearSharpTurn ? -0.45 : 0.12)),
          steer_angle: steer,
          timestamp: Date.now() / 1000,
        },
        behavior: {
          state: activeState,
          target_speed: mustYield ? 0 : (isNearSharpTurn ? corneringSpeed : CRUISE_SPEED),
          target_lane: targetLaneY > 0 ? 3 : 2,
        },
        perception: {
          objects: perceptionObjects,
          free_space: !mustYield && distToObstacle > 18,
          lanes: [
            { points: [[-7, egoX - 60], [-7, egoX + 160]], color: 'yellow', type: 'solid' },
            { points: [[-3.5, egoX - 60], [-3.5, egoX + 160]], color: 'white', type: 'dashed' },
            { points: [[0, egoX - 60], [0, egoX + 160]], color: 'white', type: 'dashed' },
            { points: [[3.5, egoX - 60], [3.5, egoX + 160]], color: 'white', type: 'dashed' },
            { points: [[7, egoX - 60], [7, egoX + 160]], color: 'yellow', type: 'solid' },
          ],
          sensor_data: {
            radar: radarDetections,
            lidar: [],
            foveated_grid: {
              memory_benchmark: {
                uniform_3d_mb: 256.0,
                foveated_25d_mb: 13.8,
                reduction_pct: 94.6,
                uniform_cells: 16000000,
                foveated_cells: 42860
              },
              tier_metrics: [
                { tier: 0, name: 'Inner Safety (0-10m)', res_m: 0.05, count: 12560 },
                { tier: 1, name: 'Mid Corridor (10-30m)', res_m: 0.20, count: 18450 },
                { tier: 2, name: 'Outer Horizon (30-100m)', res_m: 0.50, count: 11850 },
              ],
              semantic_metrics: {
                mIoU: 0.948,
                fps: 61.2,
                inference_time_ms: 16.3
              }
            }
          }
        },
        trajectory: {
          waypoints,
          valid: true,
          planning_time: 0.0034,
        }
      })

      animationFrameId = requestAnimationFrame(loop)
    }

    animationFrameId = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(animationFrameId)
  }, [isConnected, setFrameData])

  return (
    <div style={{ position: 'relative', width: '100vw', height: '100vh', overflow: 'hidden' }}>
      {/* 3D WebGL Canvas */}
      <Canvas
        camera={{ position: [0, 8, -14], fov: 55 }}
        style={{ width: '100%', height: '100%' }}
        shadows
        gl={{ antialias: true, alpha: false, powerPreference: 'high-performance' }}
      >
        <SceneContent cameraMode={cameraMode} />
      </Canvas>

      {/* Modern Glassmorphic Top-Right Dashboard Overlay */}
      <HUD
        vehicleState={vehicleState}
        behavior={behavior}
        isConnected={isConnected}
        perception={perception}
        trajectory={trajectory}
        trafficSignal={trafficSignal}
        cameraMode={cameraMode}
        onSelectCamera={setCameraMode}
      />
    </div>
  )
}