import { useMemo } from 'react'
import * as THREE from 'three'

export function PlannedPath({ trajectory }) {
  if (!trajectory?.waypoints || trajectory.waypoints.length < 2) return null

  const pathData = useMemo(() => generatePathGeometry(trajectory.waypoints), [trajectory.waypoints])

  return (
    <group name="planned-path">
      <PathLine {...pathData} />
      <PathWaypoints waypoints={trajectory.waypoints} />
    </group>
  )
}

function generatePathGeometry(waypoints) {
  const points = waypoints.map(wp => new THREE.Vector3(
    wp.worldX !== undefined ? wp.worldX : wp.y,
    0.18,
    wp.worldZ !== undefined ? wp.worldZ : wp.x
  ))
  const curve = new THREE.CatmullRomCurve3(points)
  const pathPoints = curve.getPoints(120)

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

  return { positions, colors, count: pathPoints.length }
}

function PathLine({ positions, colors, count }) {
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    g.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    return g
  }, [positions, colors])

  const material = useMemo(() => new THREE.LineBasicMaterial({
    vertexColors: true,
    transparent: true,
    opacity: 0.85,
    linewidth: 3,
  }), [])

  return <line geometry={geometry} material={material} />
}

function PathWaypoints({ waypoints }) {
  return (
    <group name="waypoints">
      {waypoints.filter((_, i) => i % 4 === 0).map((wp, i) => (
        <mesh
          key={i}
          position={[
            wp.worldX !== undefined ? wp.worldX : wp.y,
            0.19,
            wp.worldZ !== undefined ? wp.worldZ : wp.x
          ]}
        >
          <sphereGeometry args={[0.22, 12, 12]} />
          <meshBasicMaterial color="#38bdf8" />
        </mesh>
      ))}
    </group>
  )
}