import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

/**
 * 3D Realistic Animated Pedestrian with walking limbs and perception bounding box.
 */
export function Pedestrian({
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  isCrossing = false,
  walkSpeed = 1.4,
  jacketColor = '#ef4444',
  trouserColor = '#1e293b',
  label = 'Pedestrian'
}) {
  const leftLegRef = useRef()
  const rightLegRef = useRef()
  const leftArmRef = useRef()
  const rightArmRef = useRef()
  const torsoRef = useRef()
  const ringRef = useRef()

  const walkCycleRef = useRef(0)

  useFrame((_, delta) => {
    // Animate walking limbs only if moving
    const speed = Math.max(0.2, walkSpeed)
    walkCycleRef.current += delta * speed * 4.5

    const legAngle = Math.sin(walkCycleRef.current) * 0.48
    const armAngle = -Math.sin(walkCycleRef.current) * 0.38
    const torsoBob = Math.abs(Math.sin(walkCycleRef.current * 2)) * 0.04

    if (leftLegRef.current) leftLegRef.current.rotation.x = legAngle
    if (rightLegRef.current) rightLegRef.current.rotation.x = -legAngle
    if (leftArmRef.current) leftArmRef.current.rotation.x = armAngle
    if (rightArmRef.current) rightArmRef.current.rotation.x = -armAngle
    if (torsoRef.current) torsoRef.current.position.y = 0.88 + torsoBob

    // Pulse danger ring when crossing street
    if (ringRef.current) {
      ringRef.current.rotation.z += delta * 2.0
    }
  })

  // Bounding box color: warning rose/amber when crossing
  const bboxColor = isCrossing ? '#ff3b30' : '#0a84ff'

  return (
    <group position={position} rotation={rotation}>
      {/* 1. Autonomous Perception 3D Bounding Box */}
      <mesh position={[0, 0.95, 0]}>
        <boxGeometry args={[0.75, 1.9, 0.75]} />
        <meshBasicMaterial
          color={bboxColor}
          wireframe
          transparent
          opacity={isCrossing ? 0.75 : 0.4}
        />
      </mesh>

      {/* 2. Ground safety proximity ring */}
      <group position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <mesh ref={ringRef}>
          <ringGeometry args={[0.55, 0.68, 24]} />
          <meshBasicMaterial
            color={isCrossing ? '#ff453a' : '#30d158'}
            transparent
            opacity={0.65}
            side={THREE.DoubleSide}
          />
        </mesh>
      </group>

      {/* 3. Humanoid Body Hierarchy */}
      <group position={[0, 0, 0]}>
        {/* Left Leg (Hinged at hip Y = 0.82) */}
        <group ref={leftLegRef} position={[-0.14, 0.82, 0]}>
          <mesh position={[0, -0.4, 0]} castShadow>
            <cylinderGeometry args={[0.07, 0.06, 0.8, 12]} />
            <meshStandardMaterial color={trouserColor} roughness={0.7} />
          </mesh>
          {/* Shoe */}
          <mesh position={[0, -0.8, 0.05]} castShadow>
            <boxGeometry args={[0.12, 0.08, 0.22]} />
            <meshStandardMaterial color="#0f172a" roughness={0.8} />
          </mesh>
        </group>

        {/* Right Leg (Hinged at hip Y = 0.82) */}
        <group ref={rightLegRef} position={[0.14, 0.82, 0]}>
          <mesh position={[0, -0.4, 0]} castShadow>
            <cylinderGeometry args={[0.07, 0.06, 0.8, 12]} />
            <meshStandardMaterial color={trouserColor} roughness={0.7} />
          </mesh>
          {/* Shoe */}
          <mesh position={[0, -0.8, 0.05]} castShadow>
            <boxGeometry args={[0.12, 0.08, 0.22]} />
            <meshStandardMaterial color="#0f172a" roughness={0.8} />
          </mesh>
        </group>

        {/* Torso & Upper Body */}
        <group ref={torsoRef} position={[0, 0.88, 0]}>
          {/* Jacket / Shirt */}
          <mesh position={[0, 0.28, 0]} castShadow>
            <boxGeometry args={[0.42, 0.58, 0.26]} />
            <meshStandardMaterial color={jacketColor} roughness={0.5} />
          </mesh>

          {/* Urban Backpack */}
          <mesh position={[0, 0.28, -0.16]} castShadow>
            <boxGeometry args={[0.3, 0.42, 0.14]} />
            <meshStandardMaterial color="#090d16" roughness={0.8} />
          </mesh>

          {/* Neck */}
          <mesh position={[0, 0.61, 0]}>
            <cylinderGeometry args={[0.06, 0.07, 0.1, 10]} />
            <meshStandardMaterial color="#fcd34d" roughness={0.6} />
          </mesh>

          {/* Head */}
          <mesh position={[0, 0.76, 0]} castShadow>
            <sphereGeometry args={[0.13, 16, 16]} />
            <meshStandardMaterial color="#fed7aa" roughness={0.6} />
          </mesh>

          {/* Hair / Cap */}
          <mesh position={[0, 0.83, -0.02]} castShadow>
            <sphereGeometry args={[0.135, 16, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
            <meshStandardMaterial color="#1e293b" roughness={0.8} />
          </mesh>

          {/* Left Arm (Hinged at shoulder Y = 0.52) */}
          <group ref={leftArmRef} position={[-0.26, 0.52, 0]}>
            <mesh position={[0, -0.28, 0]} castShadow>
              <cylinderGeometry args={[0.05, 0.045, 0.56, 10]} />
              <meshStandardMaterial color={jacketColor} roughness={0.5} />
            </mesh>
            {/* Hand */}
            <mesh position={[0, -0.58, 0]}>
              <sphereGeometry args={[0.045, 10, 10]} />
              <meshStandardMaterial color="#fed7aa" />
            </mesh>
          </group>

          {/* Right Arm (Hinged at shoulder Y = 0.52) */}
          <group ref={rightArmRef} position={[0.26, 0.52, 0]}>
            <mesh position={[0, -0.28, 0]} castShadow>
              <cylinderGeometry args={[0.05, 0.045, 0.56, 10]} />
              <meshStandardMaterial color={jacketColor} roughness={0.5} />
            </mesh>
            {/* Hand */}
            <mesh position={[0, -0.58, 0]}>
              <sphereGeometry args={[0.045, 10, 10]} />
              <meshStandardMaterial color="#fed7aa" />
            </mesh>
          </group>
        </group>
      </group>
    </group>
  )
}
