import { useState, useRef, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, ContactShadows } from '@react-three/drei'
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
import { getLaneWorldPos } from './utils/roadGeometry'

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
      <color attach="background" args={['#090c12']} />
      <fog attach="fog" args={['#090c12', 30, 220]} />

      {/* Cinematic Lighting Setup that follows curved highway with the vehicle */}
      <ambientLight intensity={0.45} />
      <directionalLight
        position={[carWorldX + 35, 75, carWorldZ + 40]}
        intensity={1.8}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-left={-60}
        shadow-camera-right={60}
        shadow-camera-top={60}
        shadow-camera-bottom={-60}
      />
      <hemisphereLight groundColor="#0f172a" skyColor="#38bdf8" intensity={0.6} />

      {/* 3D Road and Environment with City Turns, Crosswalks and Traffic Signals */}
      <Environment
        carZ={vehicleState?.x || 0}
        signalState={trafficSignal || 'green'}
        activeSignalStation={activeSignalStation || 55}
      />

      {/* Traffic Obstacles */}
      <Traffic vehicles={perception?.objects || []} />

      {/* Ego Autonomous Vehicle */}
      <Vehicle state={vehicleState} />

      {/* LiDAR Radius Field & Sensor suite */}
      <SensorVisualization vehicleState={vehicleState} perception={perception} />

      {/* 2.5D Variable-Resolution Foveated Semantic Elevation Grid (Only active in 2.5D Grid view) */}
      {cameraMode === 'grid25d' && (
        <FoveatedGrid25D
          vehicleState={vehicleState}
          gridData={perception?.sensor_data?.foveated_grid}
        />
      )}

      {/* Planned Trajectory Path */}
      <PlannedPath trajectory={trajectory} />

      {/* Vehicle Ground Contact Shadow */}
      <ContactShadows
        opacity={0.4}
        scale={16}
        blur={2}
        far={4}
        position={[carWorldX, 0.02, carWorldZ]}
      />

      {/* Unified Camera & 3D Orbit Controls */}
      <SceneCamera cameraMode={cameraMode} vehicleState={vehicleState} />
    </>
  )
}

export default function App() {
  const [cameraMode, setCameraMode] = useState('chase') // 'chase' | 'topdown' | 'orbit' | 'grid25d'
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
    setActiveSignalStation 
  } = useSimulationStore()

  // Connect to Python WebSocket
  useWebSocket('ws://localhost:8765')

  // Smooth autonomous simulation & obstacle avoidance loop
  useEffect(() => {
    if (isConnected) return // when connected to Python, Python drives

    let animationFrameId
    let lastTime = performance.now()

    // Autonomous vehicle internal state (driving inside Lane 3, center at Y = 1.75)
    let egoX = vehicleState?.x || 0 // Longitudinal along road (Three.js Z)
    let egoY = vehicleState?.y !== undefined ? vehicleState.y : 1.75 // Lateral (centered between markings 0.0 and 3.5)
    let targetLaneY = 1.75 // Cruising lane center (between 0.0 and 3.5)
    let egoSpeed = 13.5 // ~49 km/h
    let currentBehaviorState = 'lane_follow'

    // Periodic Natural Pedestrian Crossing Schedule across the 1200m track loop
    // Spaced at ~450m intervals (~35s-40s apart) with green wave intersections in between!
    const CROSSING_SCHEDULE = [
      { baseS: 55, id: 90, name: 'Crosswalk #1' },
      { baseS: 490, id: 100, name: 'Crosswalk #2' },
      { baseS: 1000, id: 110, name: 'Crosswalk #3' },
    ]

    // Green wave bystander stations (standing safely on sidewalk, vehicle cruises past)
    const BYSTANDER_SCHEDULE = [
      { baseS: 240, y: -8.5, jacket: '#10b981', id: 81, name: 'Bystander #1' },
      { baseS: 740, y: 8.5, jacket: '#8b5cf6', id: 82, name: 'Bystander #2' },
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
        y: -9.8, // Slightly behind leader
        startY: -9.8,
        targetY: 8.8,
        dir: 1, // Left-to-right
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
        dir: -1, // Right-to-left
        speed: 1.55,
        jacket: '#f59e0b', // Amber jacket
        state: 'waiting',
      },
      {
        id: baseId + 4,
        name: 'Pedestrian #4',
        x: stationS - 0.5,
        y: 9.7, // Slightly behind leader
        startY: 9.7,
        targetY: -8.8,
        dir: -1, // Right-to-left
        speed: 1.35,
        jacket: '#10b981', // Emerald green
        state: 'waiting',
      },
    ]

    let currentCrossingS = 55
    let currentSignal = 'green'
    let pedestrians = createPedestrianGroup(55, 90)
    let groupClearTimer = 0

    // Traffic obstacles positioned across lanes, approaching and driving along the road
    let obstacles = [
      { id: 1, class_name: 'car', x: 38, y: 5.25, speed: 11.5, currentSpeed: 11.5, width: 1.9, height: 1.5, length: 4.5 }, // in right lane alongside ego car
      { id: 2, class_name: 'car', x: 26, y: -1.75, speed: 12.0, currentSpeed: 12.0, width: 1.9, height: 1.5, length: 4.5 }, // in left passing lane
      { id: 3, class_name: 'truck', x: 125, y: 1.75, speed: 4.5, currentSpeed: 4.5, width: 2.2, height: 2.6, length: 6.5 }, // truck down the road
      { id: 4, class_name: 'car', x: 175, y: 5.25, speed: 10.0, currentSpeed: 10.0, width: 1.9, height: 1.5, length: 4.6 }, // traffic down boulevard
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
        if (relDist > 38) {
          // Distant approach: Green light, pedestrians waiting on sidewalk
          currentSignal = 'green'
          pedestrians.forEach(p => {
            p.state = 'waiting'
            p.y = p.startY
          })
          groupClearTimer = 0
        } else if (relDist <= 38 && relDist > 28) {
          // Yellow warning phase
          currentSignal = 'yellow'
          pedestrians.forEach(p => {
            p.state = 'waiting'
          })
        } else if (relDist <= 28 && !isGroupCleared) {
          // Red phase: Group of pedestrians steps onto zebra crossing and walks across!
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

        setActiveSignalStation(activeCrossingConfig.s)
        setTrafficSignal(currentSignal)
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

        // If obstacle falls far behind ego car, respawn it smoothly ahead down the road
        if (newX < egoX - 55) {
          newX = egoX + 110 + Math.random() * 60
          // Avoid spawning obstacle directly on top of upcoming crosswalk
          if (Math.abs(newX - currentCrossingS) < 14) {
            newX += 24
          }
          newCurrentSpeed = obs.speed
        }

        return { ...obs, x: newX, currentSpeed: newCurrentSpeed }
      })

      // 3. Obstacle detection: find closest vehicle ahead in our lane
      const obstacleAhead = obstacles
        .filter(obs => obs.x > egoX && obs.x - egoX < 50 && Math.abs(obs.y - targetLaneY) < 1.4)
        .sort((a, b) => a.x - b.x)[0]

      const distToObstacle = obstacleAhead ? obstacleAhead.x - egoX : 999

      // Check passing lane clearance (Lane 2 center is Y = -1.75, between markings -3.5 and 0.0)
      const isPassingLaneClear = !obstacles.some(obs => Math.abs(obs.y - (-1.75)) < 1.4 && Math.abs(obs.x - egoX) < 28)

      // 4. Pedestrian and Traffic Light Yielding Decision
      const stopLineS = currentCrossingS - 7.0
      const stopTargetS = currentCrossingS - 8.5

      const isPedInRoad = pedestrians.some(p => Math.abs(p.y) < 7.6)
      const isRedSignal = currentSignal === 'red' || currentSignal === 'yellow'
      const isApproachingCrosswalk = egoX < stopLineS + 1.2 && egoX > stopLineS - 50

      const mustYield = isApproachingCrosswalk && (isRedSignal || isPedInRoad)
      const distToStop = stopTargetS - egoX

      // 5. Behavior planning state machine:
      if (mustYield) {
        currentBehaviorState = isPedInRoad ? 'pedestrian_yield' : 'traffic_light_stop'
      } else {
        if (currentBehaviorState === 'pedestrian_yield' || currentBehaviorState === 'traffic_light_stop') {
          currentBehaviorState = 'lane_follow'
        }

        // When approaching obstacle in Cruising Lane (Y = 1.75), transition into Passing Lane (Y = -1.75)
        if (distToObstacle < 34 && Math.abs(targetLaneY - 1.75) < 0.2) {
          if (isPassingLaneClear) {
            targetLaneY = -1.75
            currentBehaviorState = 'lane_change_left'
          } else {
            currentBehaviorState = 'lane_follow'
          }
        } else if (Math.abs(targetLaneY - (-1.75)) < 0.2) {
          const passedObstacle = obstacles.find(obs => Math.abs(obs.y - 1.75) < 1.0 && egoX > obs.x + 18 && egoX - obs.x < 80)
          const isCruisingLaneClear = !obstacles.some(obs => Math.abs(obs.y - 1.75) < 1.4 && Math.abs(obs.x - egoX) < 22)

          if (passedObstacle && isCruisingLaneClear) {
            targetLaneY = 1.75
            currentBehaviorState = 'lane_follow'
          }
        }
      }

      // 6. Vehicle dynamics: smooth steering and velocity update
      const laneError = targetLaneY - egoY
      const steer = Math.max(-0.07, Math.min(0.07, laneError * 0.05))
      egoY += laneError * Math.min(delta * 2.2, 1)
      const yaw = laneError * 0.035

      // Check sharp turns on 1200m track loop
      const sMod = ((egoX % 1200) + 1200) % 1200
      const isNearSharpTurn = 
        (sMod >= 85 && sMod <= 170) ||
        (sMod >= 305 && sMod <= 390) ||
        (sMod >= 585 && sMod <= 670) ||
        (sMod >= 805 && sMod <= 890)
      const corneringSpeed = 7.5 // ~27 km/h for the sharp turns

      if (mustYield) {
        // Progressive, smooth deceleration to complete stop safely before stop line
        if (distToStop > 0.4) {
          const reqDecel = Math.min(5.5, Math.max(2.6, (egoSpeed * egoSpeed) / (2 * Math.max(0.5, distToStop))))
          egoSpeed = Math.max(0, egoSpeed - reqDecel * delta)
          if (distToStop < 1.8 && egoSpeed < 1.2) {
            egoSpeed = 0
            egoX = Math.min(egoX, stopTargetS)
          }
        } else {
          egoSpeed = 0
          egoX = Math.min(egoX, stopTargetS)
        }
      } else if (distToObstacle < 18 && Math.abs(egoY - (obstacleAhead?.y || 0)) < 1.8) {
        egoSpeed = Math.max(3.5, egoSpeed - 6.0 * delta)
      } else if (isNearSharpTurn) {
        if (egoSpeed > corneringSpeed) {
          egoSpeed = Math.max(corneringSpeed, egoSpeed - 5.5 * delta)
        } else {
          egoSpeed = Math.min(corneringSpeed, egoSpeed + 2.0 * delta)
        }
      } else {
        // Smooth acceleration back up to cruising speed 50 km/h
        egoSpeed = Math.min(14.0, egoSpeed + 2.8 * delta)
      }

      // Continuous forward travel along the highway
      egoX += egoSpeed * delta

      // World coordinates of ego vehicle following road curvature and lane offset
      const egoPos = getLaneWorldPos(egoX, egoY)
      const totalYaw = egoPos.worldYaw + yaw
      const roadCurvatureSteer = egoPos.worldYaw * 0.28

      // 7. Update vehicle state in store
      setVehicleState({
        x: egoX,
        y: egoY,
        worldX: egoPos.worldX,
        worldZ: egoPos.worldZ,
        yaw: totalYaw,
        speed: egoSpeed,
        acceleration: mustYield ? -2.8 : (steer !== 0 ? 0.35 : (isNearSharpTurn ? -0.45 : 0.12)),
        steer_angle: steer + roadCurvatureSteer,
        timestamp: Date.now() / 1000,
      })

      // 8. Update behavior decision
      const activeState = mustYield 
        ? currentBehaviorState 
        : (currentBehaviorState !== 'lane_follow' 
            ? currentBehaviorState 
            : (isNearSharpTurn ? 'sharp_turn' : 'lane_follow'))

      setBehavior({
        state: activeState,
        target_speed: mustYield ? 0 : (isNearSharpTurn ? corneringSpeed : 13.88),
        target_lane: targetLaneY > 0 ? 3 : 2,
      })

      // 9. Update perception objects (including crossing pedestrians & green-wave bystanders)
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
            x: ped.x,
            y: ped.y,
            worldX: pedPos.worldX,
            worldZ: pedPos.worldZ,
            worldYaw: pedHeading,
            z: 0,
            width: 0.8,
            height: 1.8,
            length: 0.8,
            yaw: pedHeading,
            class_name: 'pedestrian',
            isCrossing: pedInRoad,
            jacketColor: ped.jacket,
          }
        }
      })

      // Bystanders waiting at green-wave intersections along the road
      const bystanderObjects = []
      BYSTANDER_SCHEDULE.forEach(b => {
        const s = currentCycle * 1200 + b.baseS
        if (Math.abs(s - egoX) < 70) {
          const bPos = getLaneWorldPos(s, b.y)
          bystanderObjects.push({
            id: b.id,
            track_id: b.id,
            confidence: 0.95,
            speed: 0,
            bbox_3d: {
              x: s,
              y: b.y,
              worldX: bPos.worldX,
              worldZ: bPos.worldZ,
              worldYaw: bPos.worldYaw + (b.y > 0 ? -Math.PI / 2 : Math.PI / 2),
              z: 0,
              width: 0.8,
              height: 1.8,
              length: 0.8,
              yaw: bPos.worldYaw + (b.y > 0 ? -Math.PI / 2 : Math.PI / 2),
              class_name: 'pedestrian',
              isCrossing: false,
              jacketColor: b.jacket,
            }
          })
        }
      })

      const allObstacleObjects = obstacles.map(obs => {
        const obsPos = getLaneWorldPos(obs.x, obs.y)
        return {
          id: obs.id,
          track_id: obs.id,
          confidence: 0.94,
          speed: obs.currentSpeed !== undefined ? obs.currentSpeed : obs.speed,
          bbox_3d: {
            x: obs.x,
            y: obs.y,
            worldX: obsPos.worldX,
            worldZ: obsPos.worldZ,
            worldYaw: obsPos.worldYaw,
            z: 0,
            width: obs.width,
            height: obs.height,
            length: obs.length,
            yaw: obsPos.worldYaw,
            class_name: obs.class_name,
          }
        }
      })

      // Include all active crossing pedestrians and bystanders in perception list
      const perceptionObjects = [...allObstacleObjects, ...pedObjects, ...bystanderObjects]

      // Radar points (including all crossing pedestrians)
      const radarDetections = obstacles.filter(obs => Math.abs(obs.x - egoX) < 55).map(obs => {
        const obsPos = getLaneWorldPos(obs.x, obs.y)
        return {
          x: obsPos.worldX,
          y: obsPos.worldZ,
          velocity: obs.currentSpeed !== undefined ? obs.currentSpeed : obs.speed,
        }
      })

      pedestrians.forEach(ped => {
        if (Math.abs(ped.x - egoX) < 55) {
          const pedPos = getLaneWorldPos(ped.x, ped.y)
          radarDetections.push({
            x: pedPos.worldX,
            y: pedPos.worldZ,
            velocity: ped.state === 'crossing' ? ped.speed : 0,
          })
        }
      })

      bystanderObjects.forEach(b => {
        if (Math.abs(b.bbox_3d.x - egoX) < 55) {
          radarDetections.push({
            x: b.bbox_3d.worldX,
            y: b.bbox_3d.worldZ,
            velocity: 0,
          })
        }
      })

      setPerception({
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
      })

      // 10. Generate smooth trajectory waypoints curving along the road
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

      setTrajectory({
        waypoints,
        valid: true,
        planning_time: 0.0034,
      })

      animationFrameId = requestAnimationFrame(loop)
    }

    animationFrameId = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(animationFrameId)
  }, [isConnected, setVehicleState, setTrajectory, setBehavior, setPerception, setTrafficSignal, setActiveSignalStation])

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