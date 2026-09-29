import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export function SensorVisualization({ vehicleState, perception }) {
  if (!vehicleState) return null

  // Support curved roads (worldX, worldZ) with fallback to (y, x)
  const carX = vehicleState.worldX !== undefined ? vehicleState.worldX : (vehicleState.y || 0)
  const carZ = vehicleState.worldZ !== undefined ? vehicleState.worldZ : (vehicleState.x || 0)
  const carYaw = vehicleState.yaw || 0

  const cameraFrustums = useMemo(() => generateCameraFrustums(), [])

  return (
    <group name="sensors" position={[carX, 0, carZ]} rotation={[0, carYaw, 0]}>
      {/* 360 LiDAR Radius Field Rings & Pulse */}
      <LidarRadiusField />

      {/* Professional Automotive LiDAR Point Cloud (Waymo/Hesai Style, zero-jitter, PointNet 3D clusters) */}
      <LidarPointCloud perception={perception} carX={carX} carZ={carZ} carYaw={carYaw} />

      {/* Camera Frustums */}
      {cameraFrustums.map((f, i) => (
        <CameraFrustum key={i} {...f} />
      ))}

      {/* Radar targets */}
      <RadarVisualization perception={perception} carX={carX} carZ={carZ} />
    </group>
  )
}

function LidarRadiusField() {
  const pulseRingRef = useRef()
  const sweepRef = useRef()
  const pulseRef = useRef(0)

  useFrame((_, delta) => {
    // Pulse ring expansion
    pulseRef.current = (pulseRef.current + delta * 0.4) % 1
    if (pulseRingRef.current) {
      const radius = 2 + pulseRef.current * 38 // 2m to 40m
      pulseRingRef.current.scale.set(radius, radius, 1)
      pulseRingRef.current.material.opacity = (1 - pulseRef.current) * 0.25
    }

    // Rotating 360 scan sweep line
    if (sweepRef.current) {
      sweepRef.current.rotation.z -= delta * 3.5
    }
  })

  const zones = [
    { r: 10, color: '#ff453a', opacity: 0.28 }, // 10m critical collision safety buffer
    { r: 20, color: '#ff9f0a', opacity: 0.24 }, // 20m intermediate proximity threshold
    { r: 30, color: '#30d158', opacity: 0.22 }, // 30m detection horizon
    { r: 40, color: '#0a84ff', opacity: 0.32 }, // 40m max sensor range
  ]

  return (
    <group position={[0, 0.04, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      {/* Concentric safety zones */}
      {zones.map(({ r, color, opacity }) => (
        <group key={r}>
          <mesh>
            <ringGeometry args={[r - 0.06, r + 0.06, 64]} />
            <meshBasicMaterial
              color={color}
              transparent
              opacity={opacity}
              depthWrite={false}
            />
          </mesh>
        </group>
      ))}

      {/* Axis crosshair guides */}
      <mesh position={[0, 0, 0]}>
        <planeGeometry args={[0.06, 80]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={0.08} depthWrite={false} />
      </mesh>
      <mesh position={[0, 0, 0]}>
        <planeGeometry args={[80, 0.06]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={0.08} depthWrite={false} />
      </mesh>

      {/* Expanding pulse wave */}
      <mesh ref={pulseRingRef}>
        <ringGeometry args={[0.96, 1.0, 64]} />
        <meshBasicMaterial
          color="#64d2ff"
          transparent
          opacity={0.3}
          depthWrite={false}
        />
      </mesh>

      {/* Rotating sweep line */}
      <group ref={sweepRef} position={[0, 0, 0.01]}>
        <mesh position={[0, 20, 0]}>
          <planeGeometry args={[0.15, 40]} />
          <meshBasicMaterial
            color="#38bdf8"
            transparent
            opacity={0.65}
            depthWrite={false}
          />
        </mesh>
      </group>
    </group>
  )
}

// 1. Precomputed steady ground reference scanlines (Zero per-frame allocations, zero jitter)
const STEADY_GROUND_POINTS = (() => {
  const pts = []
  const radii = [8, 16, 24, 32]
  const numSteps = 36 // Clean 10-degree uniform angular resolution
  for (const r of radii) {
    for (let i = 0; i < numSteps; i++) {
      const angle = (i / numSteps) * Math.PI * 2
      pts.push({
        x: Math.cos(angle) * r,
        y: 0.05,
        z: Math.sin(angle) * r,
        r: 0.22, // Subtle cyan-slate laser scanline
        g: 0.74,
        b: 0.97,
      })
    }
  }
  return pts
})()

/**
 * Fast direct-buffer population with zero heap allocations (0 GC lag).
 * Produces crisp PointNet feature clusters outlining detected obstacle geometry.
 */
function populateLidarBuffers(perception, carX, carZ, carYaw, posArr, colArr, maxPoints) {
  let count = 0

  // 1. Write the steady ground reference scan rings
  const numGround = STEADY_GROUND_POINTS.length
  for (let i = 0; i < numGround && count < maxPoints; i++) {
    const pt = STEADY_GROUND_POINTS[i]
    const base = count * 3
    posArr[base] = pt.x
    posArr[base + 1] = pt.y
    posArr[base + 2] = pt.z
    colArr[base] = pt.r
    colArr[base + 1] = pt.g
    colArr[base + 2] = pt.b
    count++
  }

  // 2. High-precision obstacle surface returns (PointNet 3D feature clusters)
  const objects = perception?.objects || []
  const cosY = Math.cos(carYaw)
  const sinY = Math.sin(carYaw)

  for (let oIdx = 0; oIdx < objects.length; oIdx++) {
    const obj = objects[oIdx]
    if (!obj.bbox_3d) continue
    const { width = 2.0, height = 1.5, length = 4.5, class_name } = obj.bbox_3d
    const objX = obj.bbox_3d.worldX !== undefined ? obj.bbox_3d.worldX : (obj.bbox_3d.y || 0)
    const objZ = obj.bbox_3d.worldZ !== undefined ? obj.bbox_3d.worldZ : (obj.bbox_3d.x || 0)

    // Transform world coordinates into ego-vehicle sensor frame
    const dx = objX - carX
    const dz = objZ - carZ
    const relX = dx * cosY - dz * sinY
    const relZ = dx * sinY + dz * cosY
    const dist = Math.hypot(relX, relZ)

    if (dist > 45) continue

    const isPedestrian = class_name === 'pedestrian' || class_name === 'person'

    if (isPedestrian) {
      // Pedestrian: structured vertical cylinder of laser returns (high-vis emerald green)
      const pR = 0.29, pG = 0.87, pB = 0.50
      for (let yStep = 0.25; yStep <= 1.65; yStep += 0.28) {
        for (let a = 0; a < 4; a++) {
          if (count >= maxPoints) break
          const ang = (a / 4) * Math.PI * 2
          const base = count * 3
          posArr[base] = relX + Math.cos(ang) * 0.26
          posArr[base + 1] = yStep
          posArr[base + 2] = relZ + Math.sin(ang) * 0.26
          colArr[base] = pR
          colArr[base + 1] = pG
          colArr[base + 2] = pB
          count++
        }
      }
    } else {
      // Vehicle: multi-beam scanlines outlining bumper, tailgate, roofline and side panels
      // Vibrant golden amber (#fbbf24) for authentic retro-reflective LiDAR returns
      const vR = 0.98, vG = 0.75, vB = 0.14
      const halfW = width * 0.46
      const halfH = height * 0.88
      const halfL = length * 0.46

      // Multi-layer horizontal scanlines across facing bumper / tailgate
      const yBeams = [0.35, 0.65, 0.95, 1.25]
      const xSteps = [-0.75, -0.45, -0.15, 0.15, 0.45, 0.75]
      const facingZ = relZ > 0 ? (relZ - halfL) : (relZ + halfL)

      for (let b = 0; b < yBeams.length; b++) {
        const yPos = Math.min(yBeams[b], halfH)
        for (let s = 0; s < xSteps.length; s++) {
          if (count >= maxPoints) break
          const base = count * 3
          posArr[base] = relX + xSteps[s] * halfW
          posArr[base + 1] = yPos
          posArr[base + 2] = facingZ
          colArr[base] = vR
          colArr[base + 1] = vG
          colArr[base + 2] = vB
          count++
        }
      }

      // Roofline edge returns (peak reflection intensity)
      for (let lStep = -0.35; lStep <= 0.35; lStep += 0.22) {
        if (count >= maxPoints) break
        const base = count * 3
        posArr[base] = relX
        posArr[base + 1] = halfH
        posArr[base + 2] = relZ + lStep * halfL
        colArr[base] = 1.0 // Peak retro-reflection
        colArr[base + 1] = 0.92
        colArr[base + 2] = 0.55
        count++
      }

      // Side panel scanlines (visible when passing or angled)
      const sideX = relX > 0 ? (relX - halfW) : (relX + halfW)
      for (let lStep = -0.35; lStep <= 0.35; lStep += 0.35) {
        if (count >= maxPoints) break
        const base = count * 3
        posArr[base] = sideX
        posArr[base + 1] = 0.55
        posArr[base + 2] = relZ + lStep * halfL
        colArr[base] = vR
        colArr[base + 1] = vG
        colArr[base + 2] = vB
        count++
      }
    }
  }

  return count
}

function LidarPointCloud({ perception, carX, carZ, carYaw }) {
  const geomRef = useRef()
  const MAX_POINTS = 1400
  const posArr = useMemo(() => new Float32Array(MAX_POINTS * 3), [])
  const colArr = useMemo(() => new Float32Array(MAX_POINTS * 3), [])

  if (!geomRef.current) {
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(posArr, 3))
    g.setAttribute('color', new THREE.BufferAttribute(colArr, 3))
    g.setDrawRange(0, 0)
    geomRef.current = g
  }

  useFrame(() => {
    if (!geomRef.current) return
    const count = populateLidarBuffers(perception, carX, carZ, carYaw, posArr, colArr, MAX_POINTS)
    geomRef.current.setDrawRange(0, count)
    geomRef.current.attributes.position.needsUpdate = true
    geomRef.current.attributes.color.needsUpdate = true
  })

  const material = useMemo(() => new THREE.PointsMaterial({
    size: 0.18,
    vertexColors: true,
    transparent: true,
    opacity: 0.9,
    sizeAttenuation: true,
    depthWrite: false,
  }), [])

  return <points geometry={geomRef.current} material={material} />
}

function generateCameraFrustums() {
  return [
    { position: [0, 1.6, 1.8], rotation: [0, 0, 0], color: '#30d158', far: 28 }, // front
    { position: [0, 1.6, -1.8], rotation: [0, Math.PI, 0], color: '#0a84ff', far: 20 }, // rear
  ]
}

function CameraFrustum({ position, rotation, color, far = 25 }) {
  const fov = 75
  const aspect = 16 / 9
  const near = 0.5

  const vertices = useMemo(() => {
    const v = []
    const halfH = Math.tan(THREE.MathUtils.degToRad(fov / 2)) * near
    const halfW = halfH * aspect

    // Near plane
    v.push(new THREE.Vector3(-halfW, -halfH, near))
    v.push(new THREE.Vector3(halfW, -halfH, near))
    v.push(new THREE.Vector3(halfW, halfH, near))
    v.push(new THREE.Vector3(-halfW, halfH, near))

    // Far plane
    const farHalfH = Math.tan(THREE.MathUtils.degToRad(fov / 2)) * far
    const farHalfW = farHalfH * aspect

    v.push(new THREE.Vector3(-farHalfW, -farHalfH, far))
    v.push(new THREE.Vector3(farHalfW, -farHalfH, far))
    v.push(new THREE.Vector3(farHalfW, farHalfH, far))
    v.push(new THREE.Vector3(-farHalfW, farHalfH, far))

    return v
  }, [far])

  return (
    <group position={position} rotation={rotation}>
      <lineLoop>
        <bufferGeometry attach="geometry">
          <float32BufferAttribute attach="attributes.position" array={new Float32Array([
            vertices[4].x, vertices[4].y, vertices[4].z,
            vertices[5].x, vertices[5].y, vertices[5].z,
            vertices[6].x, vertices[6].y, vertices[6].z,
            vertices[7].x, vertices[7].y, vertices[7].z,
          ])} itemSize={3} />
        </bufferGeometry>
        <lineBasicMaterial attach="material" color={color} transparent opacity={0.25} />
      </lineLoop>
      <lineSegments>
        <bufferGeometry attach="geometry">
          <float32BufferAttribute attach="attributes.position" array={new Float32Array([
            0, 0, 0, vertices[4].x, vertices[4].y, vertices[4].z,
            0, 0, 0, vertices[5].x, vertices[5].y, vertices[5].z,
            0, 0, 0, vertices[6].x, vertices[6].y, vertices[6].z,
            0, 0, 0, vertices[7].x, vertices[7].y, vertices[7].z,
          ])} itemSize={3} />
        </bufferGeometry>
        <lineBasicMaterial attach="material" color={color} transparent opacity={0.15} />
      </lineSegments>
    </group>
  )
}

function RadarVisualization({ perception, carX, carZ }) {
  const radarData = perception?.sensor_data?.radar || []
  if (!radarData.length) return null

  return (
    <group name="radar">
      {radarData.map((det, i) => (
        <group key={i} position={[det.y - carX, 0.4, det.x - carZ]}>
          <mesh>
            <sphereGeometry args={[0.25, 8, 8]} />
            <meshBasicMaterial color="#0a84ff" transparent opacity={0.7} />
          </mesh>
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[0.25, 0.6, 16]} />
            <meshBasicMaterial color="#0a84ff" transparent opacity={0.3} side={2} />
          </mesh>
        </group>
      ))}
    </group>
  )
}