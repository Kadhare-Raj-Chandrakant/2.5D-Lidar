import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import * as THREE from 'three'

export function Vehicle({ state }) {
  const meshRef = useRef()
  const lidarPuckRef = useRef()
  const targetPos = useRef(new THREE.Vector3(0, 0, 0))
  const targetQuat = useRef(new THREE.Quaternion())

  useFrame((_, delta) => {
    // Spin the roof LiDAR sensor
    if (lidarPuckRef.current) {
      lidarPuckRef.current.rotation.y += delta * 12
    }

    if (!meshRef.current) return

    // Python state.y is lateral lane offset (Three.js X)
    // Support curved roads (worldX, worldZ) with fallback to (y, x)
    const posX = state?.worldX !== undefined ? state.worldX : (state?.y || 0)
    const posZ = state?.worldZ !== undefined ? state.worldZ : (state?.x || 0)
    const yaw = state?.yaw || 0

    targetPos.current.set(posX, 0.45, posZ)
    targetQuat.current.setFromEuler(new THREE.Euler(0, yaw, 0))

    meshRef.current.position.lerp(targetPos.current, Math.min(delta * 12, 1))
    meshRef.current.quaternion.slerp(targetQuat.current, Math.min(delta * 12, 1))
  })

  return (
    <group ref={meshRef} position={[state?.worldX ?? state?.y ?? 0, 0.45, state?.worldZ ?? state?.x ?? 0]}>
      <VehicleChassis />
      <CabinAndGlass />
      <Wheels steerAngle={state?.steer_angle || 0} />
      <Lighting />
      <SensorSuite puckRef={lidarPuckRef} />
    </group>
  )
}

function VehicleChassis() {
  return (
    <group name="chassis">
      {/* Lower aerodynamic body */}
      <mesh castShadow receiveShadow position={[0, 0.35, 0]}>
        <boxGeometry args={[2.0, 0.65, 4.6]} />
        <meshStandardMaterial
          color="#1e293b"
          metalness={0.8}
          roughness={0.25}
        />
      </mesh>

      {/* Front bumper and hood slope */}
      <mesh castShadow receiveShadow position={[0, 0.42, 1.6]} rotation={[0.15, 0, 0]}>
        <boxGeometry args={[1.96, 0.4, 1.4]} />
        <meshStandardMaterial color="#1e293b" metalness={0.8} roughness={0.25} />
      </mesh>

      {/* Rear bumper */}
      <mesh castShadow receiveShadow position={[0, 0.42, -1.6]} rotation={[-0.1, 0, 0]}>
        <boxGeometry args={[1.96, 0.42, 1.4]} />
        <meshStandardMaterial color="#1e293b" metalness={0.8} roughness={0.25} />
      </mesh>

      {/* Side skirts */}
      <mesh castShadow receiveShadow position={[1.02, 0.18, 0]}>
        <boxGeometry args={[0.08, 0.22, 3.8]} />
        <meshStandardMaterial color="#0f172a" roughness={0.7} />
      </mesh>
      <mesh castShadow receiveShadow position={[-1.02, 0.18, 0]}>
        <boxGeometry args={[0.08, 0.22, 3.8]} />
        <meshStandardMaterial color="#0f172a" roughness={0.7} />
      </mesh>
    </group>
  )
}

function CabinAndGlass() {
  return (
    <group name="cabin" position={[0, 0.95, -0.2]}>
      {/* Upper greenhouse / cabin frame */}
      <mesh castShadow receiveShadow position={[0, 0, 0]}>
        <boxGeometry args={[1.65, 0.65, 2.4]} />
        <meshStandardMaterial color="#0f172a" roughness={0.3} metalness={0.5} />
      </mesh>

      {/* Windshield */}
      <mesh position={[0, 0.05, 1.25]} rotation={[0.48, 0, 0]}>
        <planeGeometry args={[1.5, 0.75]} />
        <meshPhysicalMaterial
          color="#0f2027"
          roughness={0.1}
          metalness={0.1}
          transmission={0.85}
          transparent
          opacity={0.7}
          side={2}
        />
      </mesh>

      {/* Rear window */}
      <mesh position={[0, 0.05, -1.25]} rotation={[-0.42, 0, 0]}>
        <planeGeometry args={[1.5, 0.7]} />
        <meshPhysicalMaterial
          color="#0f2027"
          roughness={0.1}
          metalness={0.1}
          transmission={0.85}
          transparent
          opacity={0.7}
          side={2}
        />
      </mesh>

      {/* Panoramic glass roof */}
      <mesh position={[0, 0.33, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[1.4, 2.2]} />
        <meshPhysicalMaterial
          color="#0f2027"
          roughness={0.1}
          metalness={0.2}
          transmission={0.9}
          transparent
          opacity={0.85}
        />
      </mesh>
    </group>
  )
}

function Wheels({ steerAngle }) {
  const wheelRadius = 0.36
  const wheelWidth = 0.25

  return (
    <group name="wheels">
      {/* Front wheels with steering */}
      <group position={[-1.02, 0.2, 1.4]} rotation={[0, -steerAngle, 0]}>
        <WheelGeometry radius={wheelRadius} width={wheelWidth} />
      </group>
      <group position={[1.02, 0.2, 1.4]} rotation={[0, -steerAngle, 0]}>
        <WheelGeometry radius={wheelRadius} width={wheelWidth} isRight />
      </group>

      {/* Rear wheels */}
      <group position={[-1.02, 0.2, -1.4]}>
        <WheelGeometry radius={wheelRadius} width={wheelWidth} />
      </group>
      <group position={[1.02, 0.2, -1.4]}>
        <WheelGeometry radius={wheelRadius} width={wheelWidth} isRight />
      </group>
    </group>
  )
}

function WheelGeometry({ radius, width }) {
  return (
    <group rotation={[0, 0, Math.PI / 2]}>
      {/* Tire rubber */}
      <mesh castShadow receiveShadow>
        <cylinderGeometry args={[radius, radius, width, 24]} />
        <meshStandardMaterial color="#1a1c20" roughness={0.9} />
      </mesh>
      {/* Rim */}
      <mesh position={[0, width * 0.05, 0]}>
        <cylinderGeometry args={[radius * 0.65, radius * 0.65, width * 1.02, 16]} />
        <meshStandardMaterial color="#8e9ba9" metalness={0.8} roughness={0.2} />
      </mesh>
    </group>
  )
}

function Lighting() {
  return (
    <group name="lighting">
      {/* Dual front LED headlights */}
      <mesh position={[0.65, 0.45, 2.3]}>
        <boxGeometry args={[0.35, 0.12, 0.1]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
      <mesh position={[-0.65, 0.45, 2.3]}>
        <boxGeometry args={[0.35, 0.12, 0.1]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>

      {/* Rear LED light bar */}
      <mesh position={[0, 0.52, -2.3]}>
        <boxGeometry args={[1.7, 0.08, 0.1]} />
        <meshBasicMaterial color="#ff3b30" />
      </mesh>
    </group>
  )
}

function SensorSuite({ puckRef }) {
  return (
    <group name="sensor-suite" position={[0, 1.32, -0.1]}>
      {/* Roof rack mount */}
      <mesh castShadow position={[0, 0, 0]}>
        <boxGeometry args={[0.5, 0.06, 0.5]} />
        <meshStandardMaterial color="#1e293b" metalness={0.7} roughness={0.3} />
      </mesh>

      {/* Rotating LiDAR Puck */}
      <group ref={puckRef} position={[0, 0.12, 0]}>
        <mesh castShadow>
          <cylinderGeometry args={[0.16, 0.16, 0.18, 16]} />
          <meshStandardMaterial color="#0a84ff" metalness={0.5} roughness={0.3} />
        </mesh>
        {/* Optical window */}
        <mesh position={[0, 0.02, 0]}>
          <cylinderGeometry args={[0.165, 0.165, 0.08, 16]} />
          <meshBasicMaterial color="#111827" />
        </mesh>
        {/* Active sensor beacon */}
        <mesh position={[0.14, 0.02, 0]}>
          <sphereGeometry args={[0.03, 8, 8]} />
          <meshBasicMaterial color="#5ac8fa" />
        </mesh>
      </group>

      {/* Forward perception camera housing */}
      <mesh position={[0, -0.05, 0.45]} rotation={[0.2, 0, 0]}>
        <boxGeometry args={[0.3, 0.08, 0.15]} />
        <meshStandardMaterial color="#0f172a" />
      </mesh>
    </group>
  )
}