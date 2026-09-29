import { useMemo } from 'react'
import * as THREE from 'three'
import {
  getRoadPoint,
  createCurvedRibbonGeometry,
  createAlignedDashesGeometry
} from '../utils/roadGeometry'
import { TrafficSignal } from './TrafficSignal'
import { CityBuildings } from './CityBuildings'

// Full static track bounds: -200m to 2600m (covers 2+ full city loop cycles without dynamic generation)
const STATIC_TRACK_START = -200
const STATIC_TRACK_END = 2600
const ROAD_WIDTH = 16

export function Environment({ signalState = 'green', activeSignalStation = 55 }) {
  // 1. Asphalt roadway ribbon (-8m to +8m, 16m total roadway)
  const roadGeo = useMemo(
    () => createCurvedRibbonGeometry(STATIC_TRACK_START, STATIC_TRACK_END, 4.5, -ROAD_WIDTH / 2, ROAD_WIDTH / 2, 0.005),
    []
  )

  // 2. Concrete Sidewalks (-12m to -8m on left, +8m to +12m on right)
  const leftSidewalkGeo = useMemo(
    () => createCurvedRibbonGeometry(STATIC_TRACK_START, STATIC_TRACK_END, 5.0, -12.0, -8.0, 0.02),
    []
  )
  const rightSidewalkGeo = useMemo(
    () => createCurvedRibbonGeometry(STATIC_TRACK_START, STATIC_TRACK_END, 5.0, 8.0, 12.0, 0.02),
    []
  )

  // 3. Elevated Curb Line Ribbons (-8.15m to -7.95m and +7.95m to +8.15m)
  const leftCurbGeo = useMemo(
    () => createCurvedRibbonGeometry(STATIC_TRACK_START, STATIC_TRACK_END, 5.0, -8.15, -7.95, 0.038),
    []
  )
  const rightCurbGeo = useMemo(
    () => createCurvedRibbonGeometry(STATIC_TRACK_START, STATIC_TRACK_END, 5.0, 7.95, 8.15, 0.038),
    []
  )


  // 6. Solid outer shoulder lines (crisp highway yellow)
  const leftSolidGeo = useMemo(
    () => createCurvedRibbonGeometry(STATIC_TRACK_START, STATIC_TRACK_END, 5, -7.2, -7.0, 0.016),
    []
  )
  const rightSolidGeo = useMemo(
    () => createCurvedRibbonGeometry(STATIC_TRACK_START, STATIC_TRACK_END, 5, 7.0, 7.2, 0.016),
    []
  )

  // 7. Non-slanted dashed white lane divider markings for 4 lanes
  const dashesGeo = useMemo(
    () => createAlignedDashesGeometry(STATIC_TRACK_START, STATIC_TRACK_END, [-3.5, 0.0, 3.5], 4.5, 6.5, 0.16),
    []
  )

  // 8. Static City Crosswalks and Stop Lines (Scheduled at 55m, 250m, 450m, 950m)
  const intersections = useMemo(() => {
    const BASE_STATIONS = [55, 250, 450, 950]
    const list = []
    for (let cycle = 0; cycle <= 2; cycle++) {
      for (const base of BASE_STATIONS) {
        const s = cycle * 1200 + base
        if (s >= STATIC_TRACK_START && s <= STATIC_TRACK_END) {
          list.push(s)
        }
      }
    }
    return list
  }, [])

  return (
    <group name="static-environment-world">
      {/* 1. Dark Urban Ground Foundation & Grid */}
      <mesh receiveShadow position={[0, -0.05, 1200]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[2800, 2800]} />
        <meshBasicMaterial color="#080d1a" />
      </mesh>
      <gridHelper args={[2600, 130, '#1e293b', '#0f172a']} position={[0, -0.02, 1200]} />

      {/* 2. Concrete Sidewalks flanking the roadway */}
      <mesh receiveShadow geometry={leftSidewalkGeo}>
        <meshStandardMaterial color="#2d3748" roughness={0.9} side={THREE.DoubleSide} />
      </mesh>
      <mesh receiveShadow geometry={rightSidewalkGeo}>
        <meshStandardMaterial color="#2d3748" roughness={0.9} side={THREE.DoubleSide} />
      </mesh>

      {/* 2b. Elevated Granite Curb Line Ribbons */}
      <mesh geometry={leftCurbGeo}>
        <meshStandardMaterial color="#4a5568" roughness={0.7} side={THREE.DoubleSide} />
      </mesh>
      <mesh geometry={rightCurbGeo}>
        <meshStandardMaterial color="#4a5568" roughness={0.7} side={THREE.DoubleSide} />
      </mesh>

      {/* 3. Main Asphalt Roadway Ribbon */}
      <mesh receiveShadow geometry={roadGeo}>
        <meshStandardMaterial
          color="#1a202c"
          roughness={0.85}
          metalness={0.1}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* 4. Solid Outer Edge Shoulder Markings (Vivid Golden Yellow) */}
      <mesh geometry={leftSolidGeo}>
        <meshBasicMaterial color="#f59e0b" side={THREE.DoubleSide} />
      </mesh>
      <mesh geometry={rightSolidGeo}>
        <meshBasicMaterial color="#f59e0b" side={THREE.DoubleSide} />
      </mesh>

      {/* 5. Crisp White Dashed Lane Dividers */}
      <mesh geometry={dashesGeo}>
        <meshBasicMaterial color="#ffffff" side={THREE.DoubleSide} />
      </mesh>

      {/* 6. Road Surface Directional Arrows (Crisp white lane indicators) */}
      <CurvedRoadArrows startS={STATIC_TRACK_START} endS={STATIC_TRACK_END} />

      {/* 7. Highway Street Lights along both shoulders (Warm glowing LED highway lighting) */}
      <CurvedStreetLights
        startS={STATIC_TRACK_START}
        endS={STATIC_TRACK_END}
        roadWidth={ROAD_WIDTH}
        intersections={intersections}
      />

      {/* 8. Pedestrian Zebra Crosswalks & Traffic Signals at Active Stations */}
      {intersections.map((stationS) => (
        <group key={`inter-${stationS}`}>
          <ZebraCrossingMarking s={stationS} />
          <StopLineMarking s={stationS - 7} roadWidth={15.0} />
          <TrafficSignal
            s={stationS}
            state={Math.abs(stationS - activeSignalStation) < 8 ? signalState : 'green'}
            roadWidth={ROAD_WIDTH}
          />
        </group>
      ))}

      {/* 9. City Skyline: Skyscrapers, Commercial Towers & Urban Greenery (Instanced GPU, < 120 KB RAM) */}
      <CityBuildings
        startS={STATIC_TRACK_START}
        endS={STATIC_TRACK_END}
        intersections={intersections}
      />
    </group>
  )
}

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
          <boxGeometry args={[0.54, 0.035, 4.5]} />
          <meshBasicMaterial color="#ffffff" toneMapped={false} />
        </mesh>
      ))}
    </group>
  )
}

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
  const arrowSpacing = 35
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
        <group key={i} position={[a.x, 0.024, a.z]} rotation={[0, a.yaw, 0]}>
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <planeGeometry args={[0.26, 2.8]} />
            <meshBasicMaterial color="#ffffff" side={THREE.DoubleSide} />
          </mesh>
          <mesh position={[-0.28, 0, 0.95]} rotation={[-Math.PI / 2, 0, Math.PI / 4.8]}>
            <planeGeometry args={[0.22, 1.2]} />
            <meshBasicMaterial color="#ffffff" side={THREE.DoubleSide} />
          </mesh>
          <mesh position={[0.28, 0, 0.95]} rotation={[-Math.PI / 2, 0, -Math.PI / 4.8]}>
            <planeGeometry args={[0.22, 1.2]} />
            <meshBasicMaterial color="#ffffff" side={THREE.DoubleSide} />
          </mesh>
        </group>
      ))}
    </group>
  )
}

function CurvedStreetLights({ startS, endS, roadWidth, intersections = [] }) {
  // Shared geometry instances for all street lights (zero redundant GPU allocations)
  const geometries = useMemo(() => ({
    base: new THREE.CylinderGeometry(0.32, 0.38, 0.3, 8),
    pole: new THREE.CylinderGeometry(0.08, 0.14, 7.2, 8),
    arm: new THREE.CylinderGeometry(0.06, 0.08, 2.5, 8),
    fixture: new THREE.BoxGeometry(0.75, 0.12, 0.32),
    emitter: new THREE.BoxGeometry(0.60, 0.04, 0.24),
    pool: new THREE.CircleGeometry(3.6, 16)
  }), [])

  // Shared material instances
  const materials = useMemo(() => ({
    base: new THREE.MeshStandardMaterial({ color: '#334155', roughness: 0.9 }),
    mast: new THREE.MeshStandardMaterial({ color: '#475569', roughness: 0.4, metalness: 0.7 }),
    fixture: new THREE.MeshStandardMaterial({ color: '#1e293b', roughness: 0.6, metalness: 0.5 }),
    emitter: new THREE.MeshBasicMaterial({ color: '#fef08a', toneMapped: false }),
    pool: new THREE.MeshBasicMaterial({
      color: '#fef08a',
      transparent: true,
      opacity: 0.13,
      depthWrite: false,
      side: THREE.DoubleSide
    })
  }), [])

  const lights = useMemo(() => {
    const list = []
    const spacing = 50 // 50m highway standard spacing
    const shoulderOffset = roadWidth / 2 + 1.8 // 9.8m from road centerline

    // Check if station is close to a traffic signal / crosswalk
    const isNearCrosswalk = (s) => intersections.some(interS => Math.abs(s - interS) < 16)

    // Staggered: Left side
    for (let s = startS + 15; s <= endS; s += spacing) {
      if (isNearCrosswalk(s)) continue
      const pt = getRoadPoint(s)
      list.push({
        id: `light-L-${Math.round(s)}`,
        x: pt.x - shoulderOffset * pt.normalX,
        z: pt.z - shoulderOffset * pt.normalZ,
        yaw: pt.yaw,
        side: 'left'
      })
    }

    // Staggered: Right side (offset by spacing / 2 = 25m)
    for (let s = startS + 15 + spacing / 2; s <= endS; s += spacing) {
      if (isNearCrosswalk(s)) continue
      const pt = getRoadPoint(s)
      list.push({
        id: `light-R-${Math.round(s)}`,
        x: pt.x + shoulderOffset * pt.normalX,
        z: pt.z + shoulderOffset * pt.normalZ,
        yaw: pt.yaw,
        side: 'right'
      })
    }

    return list
  }, [startS, endS, roadWidth, intersections])

  return (
    <group name="curved-street-lights">
      {lights.map(l => (
        <StreetLightPole
          key={l.id}
          light={l}
          geometries={geometries}
          materials={materials}
        />
      ))}
    </group>
  )
}

function StreetLightPole({ light, geometries, materials }) {
  const { x, z, yaw, side } = light
  const dir = side === 'left' ? 1 : -1 // Inward reach vector towards roadway

  return (
    <group position={[x, 0, z]} rotation={[0, yaw, 0]}>
      {/* Concrete foundation pad */}
      <mesh geometry={geometries.base} material={materials.base} position={[0, 0.15, 0]} />

      {/* Main vertical tapered steel mast */}
      <mesh geometry={geometries.pole} material={materials.mast} position={[0, 3.6, 0]} />

      {/* Outreach cantilever arm curving inward over road shoulder */}
      <mesh
        geometry={geometries.arm}
        material={materials.mast}
        position={[dir * 1.15, 7.35, 0]}
        rotation={[0, 0, -dir * 0.42]}
      />

      {/* Luminaire aerodynamic housing */}
      <mesh
        geometry={geometries.fixture}
        material={materials.fixture}
        position={[dir * 2.3, 7.72, 0]}
        rotation={[0, 0, -dir * 0.08]}
      />

      {/* Warm LED Luminaire light emitter (glowing lens) */}
      <mesh
        geometry={geometries.emitter}
        material={materials.emitter}
        position={[dir * 2.3, 7.64, 0]}
      />

      {/* Soft downward light pool on asphalt pavement */}
      <mesh
        geometry={geometries.pool}
        material={materials.pool}
        position={[dir * 2.3, 0.015, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
      />
    </group>
  )
}
