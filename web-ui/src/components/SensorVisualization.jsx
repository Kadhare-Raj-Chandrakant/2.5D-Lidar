import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export function SensorVisualization({ vehicleState, perception }) {
  if (!vehicleState) return null

  // Support curved roads (worldX, worldZ) with fallback to (y, x)
  const carX = vehicleState.worldX !== undefined ? vehicleState.worldX : (vehicleState.y || 0)
  const carZ = vehicleState.worldZ !== undefined ? vehicleState.worldZ : (vehicleState.x || 0)
  const carYaw = vehicleState.yaw || 0

  const lidarPoints = useMemo(() => generateLidarPoints(perception, carX, carZ), [perception, carX, carZ])
  const cameraFrustums = useMemo(() => generateCameraFrustums(), [])

  return (
    <group name="sensors" position={[carX, 0, carZ]} rotation={[0, carYaw, 0]}>
      {/* 360 LiDAR Radius Field Rings & Pulse */}
      <LidarRadiusField />

      {/* Point Cloud */}
      <LidarPointCloud points={lidarPoints} />

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
      <group ref={sweepRef}>
        <mesh position={[0, 20, 0]}>
          <planeGeometry args={[0.08, 40]} />
          <meshBasicMaterial
            color="#0a84ff"
            transparent
            opacity={0.3}
            depthWrite={false}
          />
        </mesh>
      </group>
    </group>
  )
}

function generateLidarPoints(perception, carX, carZ) {
  // If backend provided points
  if (perception?.sensor_data?.lidar && perception.sensor_data.lidar.length > 0) {
    const raw = perception.sensor_data.lidar
    return raw.filter((_, i) => i % 4 === 0).map(p => ({
      x: p[0],
      y: p[2] || 0.3,
      z: p[1],
      intensity: p[3] || 0.8,
    }))
  }

  // Standalone realistic LiDAR returns reflecting surroundings
  const points = []
  const objects = perception?.objects || []

  // Hits on obstacles
  objects.forEach(obj => {
    if (!obj.bbox_3d) return
    const { x, y, width = 2, height = 1.5, length = 4.5 } = obj.bbox_3d
    const relX = y - carX // lateral offset
    const relZ = x - carZ // longitudinal distance ahead
    const dist = Math.sqrt(relX * relX + relZ * relZ)

    if (dist < 45) {
      for (let i = 0; i < 28; i++) {
        points.push({
          x: relX + (Math.random() - 0.5) * width,
          y: Math.random() * height,
          z: relZ + (Math.random() - 0.5) * length,
          intensity: 0.9,
        })
      }
    }
  })

  // Ground scan rings
  for (let angle = 0; angle < Math.PI * 2; angle += 0.1) {
    for (const r of [8, 16, 24, 32]) {
      const noise = (Math.random() - 0.5) * 0.3
      points.push({
        x: Math.cos(angle) * (r + noise),
        y: 0.08,
        z: Math.sin(angle) * (r + noise),
        intensity: 0.4,
      })
    }
  }

  return points
}

function LidarPointCloud({ points }) {
  const positions = useMemo(() => {
    const arr = new Float32Array(points.length * 3)
    points.forEach((p, i) => {
      arr[i * 3] = p.x
      arr[i * 3 + 1] = p.y
      arr[i * 3 + 2] = p.z
    })
    return arr
  }, [points])

  const colors = useMemo(() => {
    const arr = new Float32Array(points.length * 3)
    const color = new THREE.Color()
    points.forEach((p, i) => {
      // Clean cyan/blue gradient based on height and intensity
      color.setHSL(0.55 + p.y * 0.05, 0.8, 0.5 + p.intensity * 0.3)
      arr[i * 3] = color.r
      arr[i * 3 + 1] = color.g
      arr[i * 3 + 2] = color.b
    })
    return arr
  }, [points])

  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    g.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    return g
  }, [positions, colors])

  const material = useMemo(() => new THREE.PointsMaterial({
    size: 0.16,
    vertexColors: true,
    transparent: true,
    opacity: 0.8,
    sizeAttenuation: true,
    depthWrite: false,
  }), [])

  return <points geometry={geometry} material={material} />
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