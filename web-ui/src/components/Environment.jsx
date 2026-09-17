import { useState, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import {
  getRoadPoint,
  createCurvedRibbonGeometry,
  createAlignedDashesGeometry
} from '../utils/roadGeometry'
import { TrafficSignal } from './TrafficSignal'

const CHUNK_LENGTH = 800
const NUM_CHUNKS = 3

export function Environment({ carZ = 0, signalState = 'green', activeSignalStation = 55 }) {
  // 3 sequential world chunks: behind, current, ahead
  const [chunkStarts, setChunkStarts] = useState([-CHUNK_LENGTH, 0, CHUNK_LENGTH])

  // Recycle chunk when car is 200m past its end (far in dark fog)
  useFrame(() => {
    setChunkStarts(prev => {
      let changed = false
      const next = prev.map(startS => {
        if (carZ > startS + CHUNK_LENGTH + 200) {
          changed = true
          return startS + NUM_CHUNKS * CHUNK_LENGTH
        }
        return startS
      })
      return changed ? next : prev
    })
  })

  return (
    <group name="environment-world">
      {chunkStarts.map((startS, idx) => (
        <HighwayChunk
          key={startS}
          startS={startS}
          chunkId={idx}
          signalState={signalState}
          activeSignalStation={activeSignalStation}
        />
      ))}
    </group>
  )
}

function HighwayChunk({ startS, chunkId, signalState = 'green', activeSignalStation = 55 }) {
  const endS = startS + CHUNK_LENGTH
  const roadWidth = 16

  // 1. Asphalt roadway ribbon
  const roadGeo = useMemo(
    () => createCurvedRibbonGeometry(startS, endS, 4, -roadWidth / 2, roadWidth / 2, 0),
    [startS, endS]
  )

  // 2. Surrounding terrain ground
  const groundGeo = useMemo(
    () => createCurvedRibbonGeometry(startS, endS, 10, -600, 600, -0.05),
    [startS, endS]
  )

  // 3. Concrete curbs
  const leftCurbGeo = useMemo(
    () => createCurvedRibbonGeometry(startS, endS, 4, -roadWidth / 2 - 0.8, -roadWidth / 2, 0.05),
    [startS, endS]
  )
  const rightCurbGeo = useMemo(
    () => createCurvedRibbonGeometry(startS, endS, 4, roadWidth / 2, roadWidth / 2 + 0.8, 0.05),
    [startS, endS]
  )

  // 4. Steel guardrails
  const leftRailGeo = useMemo(
    () => createCurvedRibbonGeometry(startS, endS, 4, -roadWidth / 2 - 1.3, -roadWidth / 2 - 1.1, 0.45),
    [startS, endS]
  )
  const rightRailGeo = useMemo(
    () => createCurvedRibbonGeometry(startS, endS, 4, roadWidth / 2 + 1.1, roadWidth / 2 + 1.3, 0.45),
    [startS, endS]
  )

  // 5. Solid outer yellow lane markings
  const leftSolidGeo = useMemo(
    () => createCurvedRibbonGeometry(startS, endS, 4, -7.09, -6.91, 0.015),
    [startS, endS]
  )
  const rightSolidGeo = useMemo(
    () => createCurvedRibbonGeometry(startS, endS, 4, 6.91, 7.09, 0.015),
    [startS, endS]
  )

  // 6. Non-slanted, perfectly aligned dashed white lane divider markings
  const dashesGeo = useMemo(
    () => createAlignedDashesGeometry(startS, endS, [-3.5, 0.0, 3.5], 4, 6, 0.14),
    [startS, endS]
  )

  // 7. City Crosswalks and Stop Lines at intersection locations
  const intersections = useMemo(() => {
    const BASE_STATIONS = [55, 240, 490, 740, 1000]
    const list = []
    const minCycle = Math.floor(startS / 1200) - 1
    const maxCycle = Math.floor(endS / 1200) + 1
    for (let cycle = minCycle; cycle <= maxCycle; cycle++) {
      for (const base of BASE_STATIONS) {
        const s = cycle * 1200 + base
        if (s >= startS && s < endS) {
          list.push(s)
        }
      }
    }
    return list
  }, [startS, endS])

  return (
    <group name={`chunk-${startS}`}>
      {/* Ground Terrain */}
      <mesh receiveShadow geometry={groundGeo}>
        <meshStandardMaterial color="#0a0c10" roughness={0.96} metalness={0.04} />
      </mesh>

      {/* Main Asphalt Road */}
      <mesh receiveShadow geometry={roadGeo}>
        <meshStandardMaterial color="#16181f" roughness={0.88} metalness={0.12} />
      </mesh>

      {/* Concrete Curbs */}
      <mesh receiveShadow geometry={leftCurbGeo}>
        <meshStandardMaterial color="#2b2f38" roughness={0.9} />
      </mesh>
      <mesh receiveShadow geometry={rightCurbGeo}>
        <meshStandardMaterial color="#2b2f38" roughness={0.9} />
      </mesh>

      {/* Steel Guardrails */}
      <mesh receiveShadow geometry={leftRailGeo}>
        <meshStandardMaterial color="#424752" metalness={0.7} roughness={0.35} />
      </mesh>
      <mesh receiveShadow geometry={rightRailGeo}>
        <meshStandardMaterial color="#424752" metalness={0.7} roughness={0.35} />
      </mesh>

      {/* Solid Yellow Outer Markings */}
      <mesh geometry={leftSolidGeo}>
        <meshBasicMaterial color="#d4af37" transparent opacity={0.95} />
      </mesh>
      <mesh geometry={rightSolidGeo}>
        <meshBasicMaterial color="#d4af37" transparent opacity={0.95} />
      </mesh>

      {/* Perfectly Aligned Dashed Dividers (Zero slant, perfectly parallel) */}
      <mesh geometry={dashesGeo}>
        <meshBasicMaterial color="#e2e8f0" transparent opacity={0.85} />
      </mesh>

      {/* Pedestrian Zebra Crosswalks at Intersections */}
      {intersections.map((stationS) => (
        <group key={`inter-${stationS}`}>
          {/* Bold 3D White Zebra Crossing Markings */}
          <ZebraCrossingMarking s={stationS} />
          {/* White Stop Bar Line (7m before crosswalk) */}
          <StopLineMarking s={stationS - 7} roadWidth={15.0} />
          {/* Overhead Cantilever Traffic Signal with Pedestrian Signal */}
          <TrafficSignal
            s={stationS}
            state={Math.abs(stationS - activeSignalStation) < 8 ? signalState : 'green'}
            roadWidth={roadWidth}
          />
        </group>
      ))}

      {/* Road Surface Directional Arrows (Zero slant) */}
      <CurvedRoadArrows startS={startS} endS={endS} />

      {/* Sharp Turn Warning Chevron Signs */}
      <SharpTurnChevrons startS={startS} endS={endS} roadWidth={roadWidth} />

      {/* Street Lighting along avenues and turns */}
      <CurvedStreetLights startS={startS} endS={endS} roadWidth={roadWidth} />

      {/* City Buildings lining the avenues and turns */}
      <CurvedSkyline startS={startS} endS={endS} roadWidth={roadWidth} chunkId={chunkId} />
    </group>
  )
}

/**
 * 3D High-Visibility Pedestrian Zebra Crossing
 * Renders 19 thick, solid white bars across the entire road surface.
 * Immune to backface culling, z-fighting, or shadow clipping.
 */
function ZebraCrossingMarking({ s }) {
  const roadFrame = useMemo(() => getRoadPoint(s), [s])
  const bars = useMemo(() => {
    const list = []
    const numBars = 19
    const spacing = 0.82
    const startOffset = -7.38
    for (let i = 0; i < numBars; i++) {
      const offset = startOffset + i * spacing
      list.push({
        x: roadFrame.x + offset * roadFrame.normalX,
        z: roadFrame.z + offset * roadFrame.normalZ,
      })
    }
    return list
  }, [roadFrame])

  return (
    <group name={`zebra-crossing-${s}`}>
      {bars.map((bar, idx) => (
        <mesh
          key={idx}
          position={[bar.x, 0.032, bar.z]}
          rotation={[0, roadFrame.yaw, 0]}
        >
          {/* Thick 3D bar: width 0.54m across road normal, height 0.035m, depth 4.5m along traffic */}
          <boxGeometry args={[0.54, 0.035, 4.5]} />
          <meshBasicMaterial color="#ffffff" toneMapped={false} />
        </mesh>
      ))}
    </group>
  )
}

/**
 * 3D Solid White Stop Bar Line across roadway (7m before crosswalk)
 */
function StopLineMarking({ s, roadWidth = 15.0 }) {
  const roadFrame = useMemo(() => getRoadPoint(s), [s])
  return (
    <mesh
      position={[roadFrame.x, 0.032, roadFrame.z]}
      rotation={[0, roadFrame.yaw, 0]}
    >
      <boxGeometry args={[roadWidth, 0.035, 0.75]} />
      <meshBasicMaterial color="#ffffff" toneMapped={false} />
    </mesh>
  )
}

function CurvedRoadArrows({ startS, endS }) {
  const arrowSpacing = 60
  const count = Math.floor((endS - startS) / arrowSpacing)
  const lanes = [-1.75, 1.75]

  const arrows = useMemo(() => {
    const list = []
    lanes.forEach(laneOffset => {
      for (let i = 0; i < count; i++) {
        const s = startS + i * arrowSpacing + 30
        const pt = getRoadPoint(s)
        list.push({
          x: pt.x + laneOffset * pt.normalX,
          z: pt.z + laneOffset * pt.normalZ,
          yaw: pt.yaw,
        })
      }
    })
    return list
  }, [startS, endS])

  return (
    <group name="curved-road-arrows">
      {arrows.map((a, i) => (
        <group key={i} position={[a.x, 0.018, a.z]} rotation={[0, a.yaw, 0]}>
          {/* Arrow stem */}
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <planeGeometry args={[0.24, 2.8]} />
            <meshBasicMaterial color="#e2e8f0" transparent opacity={0.65} />
          </mesh>
          {/* Left barb */}
          <mesh position={[-0.26, 0, 0.95]} rotation={[-Math.PI / 2, 0, Math.PI / 4.8]}>
            <planeGeometry args={[0.2, 1.2]} />
            <meshBasicMaterial color="#e2e8f0" transparent opacity={0.65} />
          </mesh>
          {/* Right barb */}
          <mesh position={[0.26, 0, 0.95]} rotation={[-Math.PI / 2, 0, -Math.PI / 4.8]}>
            <planeGeometry args={[0.2, 1.2]} />
            <meshBasicMaterial color="#e2e8f0" transparent opacity={0.65} />
          </mesh>
        </group>
      ))}
    </group>
  )
}

function SharpTurnChevrons({ startS, endS, roadWidth }) {
  // Place bright yellow warning chevron signs on the outside barrier of the sharp turns
  const chevrons = useMemo(() => {
    const list = []
    // Sharp turn 1 (100m to 165m) turns right -> chevrons on outer left barrier
    for (let s = 102; s <= 165; s += 10) {
      if (s >= startS && s <= endS) {
        const pt = getRoadPoint(s)
        list.push({
          x: pt.x - (roadWidth / 2 + 1.2) * pt.normalX,
          z: pt.z - (roadWidth / 2 + 1.2) * pt.normalZ,
          yaw: pt.yaw + 0.3, // Angled toward oncoming traffic
        })
      }
    }
    // Sharp counter-turn (320m to 385m) turns left -> chevrons on outer right barrier
    for (let s = 322; s <= 385; s += 10) {
      if (s >= startS && s <= endS) {
        const pt = getRoadPoint(s)
        list.push({
          x: pt.x + (roadWidth / 2 + 1.2) * pt.normalX,
          z: pt.z + (roadWidth / 2 + 1.2) * pt.normalZ,
          yaw: pt.yaw - 0.3,
        })
      }
    }
    return list
  }, [startS, endS, roadWidth])

  return (
    <group name="turn-chevrons">
      {chevrons.map((c, i) => (
        <group key={i} position={[c.x, 1.2, c.z]} rotation={[0, c.yaw, 0]}>
          {/* Sign board */}
          <mesh castShadow>
            <boxGeometry args={[1.2, 1.2, 0.06]} />
            <meshStandardMaterial color="#facc15" roughness={0.3} metalness={0.4} />
          </mesh>
          {/* Black chevron arrow border */}
          <mesh position={[0, 0, 0.035]}>
            <planeGeometry args={[0.9, 0.9]} />
            <meshBasicMaterial color="#0f172a" />
          </mesh>
          {/* Inner yellow arrow */}
          <mesh position={[-0.05, 0, 0.04]}>
            <planeGeometry args={[0.55, 0.55]} />
            <meshBasicMaterial color="#facc15" />
          </mesh>
          {/* Mounting pole */}
          <mesh position={[0, -0.9, 0]}>
            <cylinderGeometry args={[0.04, 0.04, 1.0]} />
            <meshStandardMaterial color="#64748b" metalness={0.8} />
          </mesh>
        </group>
      ))}
    </group>
  )
}

function CurvedStreetLights({ startS, endS, roadWidth }) {
  const lightSpacing = 80
  const count = Math.floor((endS - startS) / lightSpacing)

  const lights = useMemo(() => {
    const list = []
    for (let i = 0; i < count; i++) {
      const sLeft = startS + i * lightSpacing + 20
      const ptLeft = getRoadPoint(sLeft)
      list.push({
        x: ptLeft.x - (roadWidth / 2 + 2.5) * ptLeft.normalX,
        z: ptLeft.z - (roadWidth / 2 + 2.5) * ptLeft.normalZ,
        yaw: ptLeft.yaw,
        dir: 1, // Facing inward toward road
      })

      const sRight = startS + i * lightSpacing + 60
      const ptRight = getRoadPoint(sRight)
      list.push({
        x: ptRight.x + (roadWidth / 2 + 2.5) * ptRight.normalX,
        z: ptRight.z + (roadWidth / 2 + 2.5) * ptRight.normalZ,
        yaw: ptRight.yaw,
        dir: -1,
      })
    }
    return list
  }, [startS, endS, roadWidth])

  return (
    <group name="curved-street-lights">
      {lights.map((l, i) => (
        <group key={i} position={[l.x, 0, l.z]} rotation={[0, l.yaw, 0]}>
          {/* Pole */}
          <mesh castShadow position={[0, 4, 0]}>
            <cylinderGeometry args={[0.1, 0.16, 8, 8]} />
            <meshStandardMaterial color="#353942" metalness={0.6} roughness={0.4} />
          </mesh>
          {/* Arm */}
          <mesh position={[l.dir * 1.2, 7.8, 0]} rotation={[0, 0, -l.dir * 0.4]}>
            <boxGeometry args={[2.5, 0.12, 0.12]} />
            <meshStandardMaterial color="#353942" metalness={0.6} roughness={0.4} />
          </mesh>
          {/* Fixture */}
          <mesh position={[l.dir * 2.2, 7.5, 0]}>
            <boxGeometry args={[0.6, 0.15, 0.3]} />
            <meshStandardMaterial color="#1f2229" />
          </mesh>
          {/* Glowing lamp */}
          <mesh position={[l.dir * 2.2, 7.4, 0]}>
            <planeGeometry args={[0.5, 0.25]} />
            <meshBasicMaterial color="#ffdf99" />
          </mesh>
        </group>
      ))}
    </group>
  )
}

function CurvedSkyline({ startS, endS, roadWidth, chunkId }) {
  const buildings = useMemo(() => {
    const list = []
    const setback = 28
    const countPerSide = 20

    // Deterministic pseudo-random seed per chunk
    let seed = Math.abs(Math.floor(startS / 100)) * 9301 + 49297
    const random = () => {
      seed = (seed * 9301 + 49297) % 233280
      return seed / 233280
    }

    for (let side = -1; side <= 1; side += 2) {
      for (let i = 0; i < countPerSide; i++) {
        const s = startS + i * (CHUNK_LENGTH / countPerSide) + random() * 10
        const pt = getRoadPoint(s)

        const width = 14 + random() * 18
        const depth = 14 + random() * 18
        const height = 18 + random() * 52
        const distFromCenter = roadWidth / 2 + setback + width / 2 + random() * 20

        const x = pt.x + side * distFromCenter * pt.normalX
        const z = pt.z + side * distFromCenter * pt.normalZ
        const hue = 0.6 + (random() - 0.5) * 0.06
        const lightness = 0.07 + random() * 0.08

        list.push({ x, y: height / 2, z, width, height, depth, hue, lightness, yaw: pt.yaw })
      }
    }
    return list
  }, [startS, endS, roadWidth, chunkId])

  return (
    <group name="curved-skyline">
      {buildings.map((b, i) => (
        <mesh key={i} castShadow receiveShadow position={[b.x, b.y, b.z]} rotation={[0, b.yaw, 0]}>
          <boxGeometry args={[b.width, b.height, b.depth]} />
          <meshStandardMaterial
            color={new THREE.Color().setHSL(b.hue, 0.15, b.lightness)}
            roughness={0.8}
            metalness={0.2}
          />
        </mesh>
      ))}
    </group>
  )
}