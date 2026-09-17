import { useMemo } from 'react'
import * as THREE from 'three'
import { getRoadPoint } from '../utils/roadGeometry'

/**
 * 3D Cantilever Overhead Traffic Signal with Pedestrian Signal at Crosswalks.
 * state: 'green' | 'yellow' | 'red'
 */
export function TrafficSignal({ s = 55, state = 'green', roadWidth = 16 }) {
  const roadFrame = useMemo(() => getRoadPoint(s), [s])

  // Signal lights configuration
  const isRed = state === 'red'
  const isYellow = state === 'yellow'
  const isGreen = state === 'green'

  const redColor = isRed ? '#ff1e1e' : '#3d0a0a'
  const redEmissive = isRed ? '#ff2a2a' : '#140000'
  const redIntensity = isRed ? 2.8 : 0.05

  const yellowColor = isYellow ? '#ffaa00' : '#3d2800'
  const yellowEmissive = isYellow ? '#ffaa00' : '#140d00'
  const yellowIntensity = isYellow ? 2.8 : 0.05

  const greenColor = isGreen ? '#10b981' : '#042a18'
  const greenEmissive = isGreen ? '#10b981' : '#01120a'
  const greenIntensity = isGreen ? 2.8 : 0.05

  // Active light color for ground glow
  const activeLightColor = isRed ? '#ff2a2a' : (isYellow ? '#ffaa00' : '#10b981')

  // Pole position on sidewalk (right side of road)
  const curbOffset = roadWidth / 2 + 1.4
  const poleX = roadFrame.x + curbOffset * roadFrame.normalX
  const poleZ = roadFrame.z + curbOffset * roadFrame.normalZ

  return (
    <group position={[poleX, 0, poleZ]} rotation={[0, roadFrame.yaw, 0]}>
      {/* 1. Main Vertical Steel Mast */}
      <mesh position={[0, 3.2, 0]} castShadow>
        <cylinderGeometry args={[0.18, 0.22, 6.4, 16]} />
        <meshStandardMaterial color="#2d3748" metalness={0.75} roughness={0.3} />
      </mesh>

      {/* Mast base plate & foundation */}
      <mesh position={[0, 0.1, 0]}>
        <cylinderGeometry args={[0.35, 0.4, 0.2, 16]} />
        <meshStandardMaterial color="#1a202c" metalness={0.8} roughness={0.4} />
      </mesh>

      {/* 2. Cantilever Horizontal Arm reaching out over the roadway */}
      {/* Extends laterally to the left across the roadway (negative normal direction) */}
      <mesh position={[-6.2, 6.1, 0]} rotation={[0, 0, Math.PI / 2]} castShadow>
        <cylinderGeometry args={[0.12, 0.16, 12.4, 16]} />
        <meshStandardMaterial color="#2d3748" metalness={0.75} roughness={0.3} />
      </mesh>

      {/* Arm diagonal support truss */}
      <mesh position={[-2.2, 5.2, 0]} rotation={[0, 0, Math.PI / 4]}>
        <cylinderGeometry args={[0.07, 0.07, 3.2, 12]} />
        <meshStandardMaterial color="#2d3748" metalness={0.75} roughness={0.3} />
      </mesh>

      {/* 3. Overhead Signal Head (Center of Road - facing oncoming traffic) */}
      <SignalHead
        position={[-curbOffset + 1.75, 5.2, 0]}
        redColor={redColor}
        redEmissive={redEmissive}
        redIntensity={redIntensity}
        yellowColor={yellowColor}
        yellowEmissive={yellowEmissive}
        yellowIntensity={yellowIntensity}
        greenColor={greenColor}
        greenEmissive={greenEmissive}
        greenIntensity={greenIntensity}
      />

      {/* 4. Second Overhead Signal Head (Left Lane) */}
      <SignalHead
        position={[-curbOffset - 1.75, 5.2, 0]}
        redColor={redColor}
        redEmissive={redEmissive}
        redIntensity={redIntensity}
        yellowColor={yellowColor}
        yellowEmissive={yellowEmissive}
        yellowIntensity={yellowIntensity}
        greenColor={greenColor}
        greenEmissive={greenEmissive}
        greenIntensity={greenIntensity}
      />

      {/* 5. Curbside Pedestrian Signal Box (facing the zebra crosswalk) */}
      <PedestrianSignalBox
        position={[-0.35, 2.5, 0]}
        isWalk={isRed} // Walk when vehicles have red light
      />

      {/* Dynamic ambient ground illumination from active signal */}
      <pointLight
        position={[-curbOffset, 4.8, -1.2]}
        color={activeLightColor}
        intensity={3.5}
        distance={16}
        decay={2}
      />
    </group>
  )
}

/**
 * 3-Aspect Traffic Light Head with Hoods
 */
function SignalHead({
  position,
  redColor,
  redEmissive,
  redIntensity,
  yellowColor,
  yellowEmissive,
  yellowIntensity,
  greenColor,
  greenEmissive,
  greenIntensity
}) {
  return (
    <group position={position}>
      {/* Vertical mounting bracket */}
      <mesh position={[0, 0.5, 0]}>
        <cylinderGeometry args={[0.04, 0.04, 1.0, 8]} />
        <meshStandardMaterial color="#1a202c" metalness={0.8} />
      </mesh>

      {/* Main black casing */}
      <mesh castShadow position={[0, 0, 0]}>
        <boxGeometry args={[0.55, 1.55, 0.35]} />
        <meshStandardMaterial color="#111827" roughness={0.6} metalness={0.3} />
      </mesh>

      {/* Yellow high-visibility backplate border */}
      <mesh position={[0, 0, 0.05]}>
        <boxGeometry args={[0.75, 1.75, 0.05]} />
        <meshStandardMaterial color="#eab308" roughness={0.4} />
      </mesh>

      {/* Backplate inner cutout */}
      <mesh position={[0, 0, 0.07]}>
        <boxGeometry args={[0.62, 1.62, 0.03]} />
        <meshStandardMaterial color="#111827" />
      </mesh>

      {/* Lenses facing oncoming traffic (-Z in road frame) */}
      {/* RED Lens */}
      <group position={[0, 0.46, -0.18]}>
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.18, 0.18, 0.06, 24]} />
          <meshStandardMaterial
            color={redColor}
            emissive={redEmissive}
            emissiveIntensity={redIntensity}
            roughness={0.1}
          />
        </mesh>
        {/* Visor hood */}
        <mesh position={[0, 0.12, -0.06]} rotation={[0.4, 0, 0]}>
          <boxGeometry args={[0.38, 0.04, 0.22]} />
          <meshStandardMaterial color="#111827" />
        </mesh>
      </group>

      {/* YELLOW Lens */}
      <group position={[0, 0, -0.18]}>
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.18, 0.18, 0.06, 24]} />
          <meshStandardMaterial
            color={yellowColor}
            emissive={yellowEmissive}
            emissiveIntensity={yellowIntensity}
            roughness={0.1}
          />
        </mesh>
        {/* Visor hood */}
        <mesh position={[0, 0.12, -0.06]} rotation={[0.4, 0, 0]}>
          <boxGeometry args={[0.38, 0.04, 0.22]} />
          <meshStandardMaterial color="#111827" />
        </mesh>
      </group>

      {/* GREEN Lens */}
      <group position={[0, -0.46, -0.18]}>
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.18, 0.18, 0.06, 24]} />
          <meshStandardMaterial
            color={greenColor}
            emissive={greenEmissive}
            emissiveIntensity={greenIntensity}
            roughness={0.1}
          />
        </mesh>
        {/* Visor hood */}
        <mesh position={[0, 0.12, -0.06]} rotation={[0.4, 0, 0]}>
          <boxGeometry args={[0.38, 0.04, 0.22]} />
          <meshStandardMaterial color="#111827" />
        </mesh>
      </group>
    </group>
  )
}

/**
 * Curbside Pedestrian Signal Box (WALK / DON'T WALK)
 */
function PedestrianSignalBox({ position, isWalk }) {
  return (
    <group position={position}>
      {/* Box casing */}
      <mesh castShadow>
        <boxGeometry args={[0.38, 0.72, 0.3]} />
        <meshStandardMaterial color="#111827" roughness={0.6} />
      </mesh>

      {/* Top section: DON'T WALK (Red Hand) */}
      <mesh position={[0, 0.16, -0.15]}>
        <planeGeometry args={[0.26, 0.26]} />
        <meshStandardMaterial
          color={!isWalk ? '#ff2222' : '#330808'}
          emissive={!isWalk ? '#ff2222' : '#0a0000'}
          emissiveIntensity={!isWalk ? 2.5 : 0.1}
        />
      </mesh>

      {/* Bottom section: WALK (White/Green Walking Person) */}
      <mesh position={[0, -0.16, -0.15]}>
        <planeGeometry args={[0.26, 0.26]} />
        <meshStandardMaterial
          color={isWalk ? '#ffffff' : '#112218'}
          emissive={isWalk ? '#38bdf8' : '#020d06'}
          emissiveIntensity={isWalk ? 3.0 : 0.1}
        />
      </mesh>
    </group>
  )
}
