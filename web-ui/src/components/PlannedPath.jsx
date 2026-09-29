import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

// Throttle: only rebuild path geometry every N frames to avoid creating new
// BufferGeometry objects every single animation frame (60/s -> 10/s).
const REBUILD_EVERY_N_FRAMES = 6

export function PlannedPath({ trajectory }) {
  if (!trajectory?.waypoints || trajectory.waypoints.length < 2) return null

  return (
    <group name="planned-path">
      <ThrottledPathLine waypoints={trajectory.waypoints} />
      <PathWaypoints waypoints={trajectory.waypoints} />
    </group>
  )
}

// Internally throttles geometry rebuild to once every REBUILD_EVERY_N_FRAMES frames.
// The geometry object is mutated in place rather than replaced to avoid GC pressure.
function ThrottledPathLine({ waypoints }) {
  const frameCount = useRef(0)
  // Cache last waypoints used to build geometry so we can skip identical rebuilds
  const lastWaypointsRef = useRef(null)

  const geometryRef = useRef(null)
  const materialRef = useRef(null)
  const lineRef = useRef(null)

  // Create geometry and material once on mount
  if (!geometryRef.current) {
    geometryRef.current = new THREE.BufferGeometry()
    materialRef.current = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
    })
  }

  useFrame(() => {
    frameCount.current += 1
    if (frameCount.current % REBUILD_EVERY_N_FRAMES !== 0) return
    if (!waypoints || waypoints.length < 2) return

    // Rebuild path geometry at throttled rate
    const points = waypoints.map(wp => new THREE.Vector3(
      wp.worldX !== undefined ? wp.worldX : wp.y,
      0.18,
      wp.worldZ !== undefined ? wp.worldZ : wp.x
    ))
    const curve = new THREE.CatmullRomCurve3(points)
    const pathPoints = curve.getPoints(80)

    const positions = new Float32Array(pathPoints.length * 3)
    const colors = new Float32Array(pathPoints.length * 3)

    pathPoints.forEach((p, i) => {
      positions[i * 3] = p.x
      positions[i * 3 + 1] = p.y
      positions[i * 3 + 2] = p.z

      const t = i / pathPoints.length
      colors[i * 3] = 0.2
      colors[i * 3 + 1] = 0.8
      colors[i * 3 + 2] = 1.0 - t * 0.3
    })

    geometryRef.current.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometryRef.current.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geometryRef.current.computeBoundingSphere()
  })

  return <line ref={lineRef} geometry={geometryRef.current} material={materialRef.current} />
}

function PathWaypoints({ waypoints }) {
  // Only show every 4th waypoint as a dot, throttled via useMemo
  // The key here uses first+last worldZ so React only re-renders when path meaningfully changes
  const firstZ = waypoints[0]?.worldZ ?? waypoints[0]?.x ?? 0
  const lastZ = waypoints[waypoints.length - 1]?.worldZ ?? waypoints[waypoints.length - 1]?.x ?? 0
  const firstX = waypoints[0]?.worldX ?? waypoints[0]?.y ?? 0
  const lastX = waypoints[waypoints.length - 1]?.worldX ?? waypoints[waypoints.length - 1]?.y ?? 0

  const dots = useMemo(() =>
    waypoints
      .filter((_, i) => i % 4 === 0)
      .map(wp => ({
        x: wp.worldX !== undefined ? wp.worldX : wp.y,
        z: wp.worldZ !== undefined ? wp.worldZ : wp.x,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [Math.round(firstZ * 2), Math.round(lastZ * 2), Math.round(firstX * 4), Math.round(lastX * 4)]
  )

  return (
    <group name="waypoints">
      {dots.map((dot, i) => (
        <mesh
          key={i}
          position={[dot.x, 0.19, dot.z]}
        >
          <sphereGeometry args={[0.22, 8, 8]} />
          <meshBasicMaterial color="#38bdf8" />
        </mesh>
      ))}
    </group>
  )
}