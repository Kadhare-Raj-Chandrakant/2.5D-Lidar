import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

/**
 * 2.5D Variable-Resolution Foveated Semantic Elevation Grid Visualizer
 *
 * Professional, clean autonomous perception overlay (similar to Waymo / Autoware / ROS RViz).
 * Only visible when "2.5D Grid" camera view is selected.
 *
 * Concentric multi-resolution tiers:
 *  - Tier 0 (0-10m):   5cm cells  (Dense safety zone: curbs & pedestrians)
 *  - Tier 1 (10-30m):  20cm cells (Intermediate road corridor)
 *  - Tier 2 (30-100m): 50cm cells (Coarse distant horizon)
 *
 * Uses clean, flat ground tiles and sleek concentric boundary rings
 * to keep the scene elegant, transparent, and uncluttered.
 */
export function FoveatedGrid25D({ vehicleState, gridData }) {
  if (!vehicleState) return null

  const carX = vehicleState.worldX !== undefined ? vehicleState.worldX : (vehicleState.y || 0)
  const carZ = vehicleState.worldZ !== undefined ? vehicleState.worldZ : (vehicleState.x || 0)
  const carYaw = vehicleState.yaw || 0

  const radarSweepRef = useRef()

  useFrame((_, delta) => {
    if (radarSweepRef.current) {
      radarSweepRef.current.rotation.z -= delta * 1.8
    }
  })

  // Semantic class colors matching PointNet++ classes
  const SEMANTIC_COLORS = useMemo(() => ({
    0: '#10b981', // Drivable Road (Emerald)
    1: '#f59e0b', // Curbs & Terrain (Amber)
    2: '#64748b', // Static Obstacles (Slate)
    3: '#f43f5e', // Dynamic Actors (Rose)
  }), [])

  // Generate structured, clean 2.5D grid tiles aligned with the road corridor
  const tiles = useMemo(() => {
    const list = []

    // 1. Tier 0: Fine 5cm resolution ground corridor (0 to 10m)
    // Structured grid across the roadway (-7.5m to +7.5m lateral, -10m to +10m longitudinal)
    for (let x = -7.0; x <= 7.0; x += 1.4) {
      for (let z = -9.0; z <= 9.0; z += 1.8) {
        const dist = Math.hypot(x, z)
        if (dist > 9.8) continue
        const isCurb = Math.abs(x) > 6.0
        const classId = isCurb ? 1 : 0

        list.push({
          x: round2(x),
          z: round2(z),
          class_id: classId,
          tier: 0,
          size: 1.1,
          opacity: isCurb ? 0.45 : 0.22,
        })
      }
    }

    // 2. Tier 1: Mid 20cm resolution ground corridor (10m to 30m)
    for (let x = -10.0; x <= 10.0; x += 3.2) {
      for (let z = 10.0; z <= 28.0; z += 3.6) {
        const dist = Math.hypot(x, z)
        if (dist < 10.2 || dist > 29.5) continue
        const isRoad = Math.abs(x) < 7.2

        list.push({
          x: round2(x),
          z: round2(z),
          class_id: isRoad ? 0 : 2,
          tier: 1,
          size: 2.8,
          opacity: isRoad ? 0.18 : 0.35,
        })
      }
    }

    // 3. Tier 2: Coarse 50cm resolution horizon corridor (30m to 65m)
    for (let x = -14.0; x <= 14.0; x += 7.0) {
      for (let z = 32.0; z <= 62.0; z += 7.5) {
        const dist = Math.hypot(x, z)
        if (dist < 30.5 || dist > 64.0) continue
        const isRoad = Math.abs(x) < 7.2

        list.push({
          x: round2(x),
          z: round2(z),
          class_id: isRoad ? 0 : 2,
          tier: 2,
          size: 5.5,
          opacity: 0.14,
        })
      }
    }

    return list
  }, [])

  return (
    <group name="foveated-2.5d-grid" position={[carX, 0.04, carZ]} rotation={[0, carYaw, 0]}>
      {/* 1. Sleek Concentric Foveation Tier Boundary Rings */}
      {/* Tier 0 Boundary: 10m Radius (5cm fine safety zone) */}
      <group rotation={[-Math.PI / 2, 0, 0]}>
        <mesh>
          <ringGeometry args={[9.92, 10.08, 64]} />
          <meshBasicMaterial color="#38bdf8" transparent opacity={0.6} side={THREE.DoubleSide} />
        </mesh>
      </group>

      {/* Tier 1 Boundary: 30m Radius (20cm mid corridor) */}
      <group rotation={[-Math.PI / 2, 0, 0]}>
        <mesh>
          <ringGeometry args={[29.88, 30.12, 64]} />
          <meshBasicMaterial color="#a855f7" transparent opacity={0.4} side={THREE.DoubleSide} />
        </mesh>
      </group>

      {/* Tier 2 Boundary: 70m Radius (50cm distant horizon) */}
      <group rotation={[-Math.PI / 2, 0, 0]}>
        <mesh>
          <ringGeometry args={[64.85, 65.15, 64]} />
          <meshBasicMaterial color="#64748b" transparent opacity={0.25} side={THREE.DoubleSide} />
        </mesh>
      </group>

      {/* Rotating Radar Sweep Line */}
      <group ref={radarSweepRef} rotation={[-Math.PI / 2, 0, 0]}>
        <mesh position={[0, 15, 0]}>
          <planeGeometry args={[0.08, 30]} />
          <meshBasicMaterial color="#38bdf8" transparent opacity={0.4} />
        </mesh>
      </group>

      {/* 2. Structured, Clean 2.5D Semantic Ground Tiles (Subtle & Flat, Zero Clutter) */}
      {tiles.map((tile, idx) => {
        const color = SEMANTIC_COLORS[tile.class_id] || '#10b981'

        return (
          <group key={idx} position={[tile.x, 0, tile.z]} rotation={[-Math.PI / 2, 0, 0]}>
            {/* Flat semi-transparent ground tile */}
            <mesh>
              <planeGeometry args={[tile.size * 0.88, tile.size * 0.88]} />
              <meshBasicMaterial
                color={color}
                transparent
                opacity={tile.opacity}
                side={THREE.DoubleSide}
                depthWrite={false}
              />
            </mesh>

            {/* Subtle high-tech grid wireframe outline */}
            <mesh>
              <planeGeometry args={[tile.size * 0.88, tile.size * 0.88]} />
              <meshBasicMaterial
                color={color}
                wireframe
                transparent
                opacity={tile.opacity * 0.75}
                side={THREE.DoubleSide}
                depthWrite={false}
              />
            </mesh>
          </group>
        )
      })}
    </group>
  )
}

function round2(v) {
  return Math.round(v * 100) / 100
}
