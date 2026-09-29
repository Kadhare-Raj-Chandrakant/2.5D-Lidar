/**
 * Road Curvature Math & Geometry Utilities
 * Features a realistic city layout with a SHARP TURN starting right after 100 meters.
 * Exact arc-length parameterization ensures zero distortion of pavement markings.
 */
import * as THREE from 'three'

const CYCLE_LENGTH = 1200 // 1200m per city loop cycle

// Quintic smoothstep: C² continuous (smooth position, velocity, and curvature)
function quinticSmooth(t) {
  const c = Math.max(0, Math.min(1, t))
  return c * c * c * (c * (c * 6 - 15) + 10)
}

/**
 * Heading angle psi(s) in radians at distance s.
 * Designed with a dramatic, unmistakable SHARP TURN after 100 meters:
 * - 0m to 100m: Straight Avenue (psi = 0)
 * - 100m to 165m: SHARP RIGHT TURN (heading sweeps 62° to the right, R ~ 58m)
 * - 165m to 320m: Straight Angled Boulevard (psi = 62°)
 * - 320m to 385m: SHARP LEFT TURN (heading returns to 0°)
 * - 385m to 600m: Straight Central Avenue (psi = 0)
 * - 600m to 665m: SHARP LEFT TURN (heading sweeps -62° to the left)
 * - 665m to 820m: Straight Angled Boulevard (psi = -62°)
 * - 820m to 885m: SHARP RIGHT TURN (heading returns to 0°)
 * - 885m to 1200m: Straight Boulevard to complete the loop
 */
const SHARP_ANGLE = 7 * (Math.PI / 180) // Gentle 7-degree realistic highway sweep (natural real-world driving)

export function getRoadYaw(s) {
  const sMod = ((s % CYCLE_LENGTH) + CYCLE_LENGTH) % CYCLE_LENGTH

  // 1. Straight Avenue before turn (0m to 100m)
  if (sMod < 100) {
    return 0
  }
  // 2. SHARP RIGHT TURN (100m to 165m) - 65m turn radius ~ 58m
  if (sMod < 165) {
    const t = (sMod - 100) / 65
    return SHARP_ANGLE * quinticSmooth(t)
  }
  // 3. Straight Boulevard (165m to 320m)
  if (sMod < 320) {
    return SHARP_ANGLE
  }
  // 4. SHARP LEFT COUNTER-TURN (320m to 385m)
  if (sMod < 385) {
    const t = (sMod - 320) / 65
    return SHARP_ANGLE * (1 - quinticSmooth(t))
  }
  // 5. Straight Central Avenue (385m to 600m)
  if (sMod < 600) {
    return 0
  }
  // 6. SHARP LEFT TURN (600m to 665m)
  if (sMod < 665) {
    const t = (sMod - 600) / 65
    return -SHARP_ANGLE * quinticSmooth(t)
  }
  // 7. Straight Boulevard (665m to 820m)
  if (sMod < 820) {
    return -SHARP_ANGLE
  }
  // 8. SHARP RIGHT COUNTER-TURN (820m to 885m)
  if (sMod < 885) {
    const t = (sMod - 820) / 65
    return -SHARP_ANGLE * (1 - quinticSmooth(t))
  }
  // 9. Straight Boulevard (885m to 1200m)
  return 0
}

// Precomputed dense numerical integration of (X, Z) along road arc-length s
const TABLE_STEP = 1.0 // 1 meter resolution
const TABLE_MIN_S = -800
const TABLE_MAX_S = 6000
const NUM_ENTRIES = Math.ceil((TABLE_MAX_S - TABLE_MIN_S) / TABLE_STEP) + 1

const roadTableX = new Float32Array(NUM_ENTRIES)
const roadTableZ = new Float32Array(NUM_ENTRIES)
const roadTableYaw = new Float32Array(NUM_ENTRIES)

// Initialize road coordinate table at module load
;(function buildRoadTable() {
  // First integrate from 0 to TABLE_MAX_S
  const zeroIdx = Math.round((0 - TABLE_MIN_S) / TABLE_STEP)
  roadTableX[zeroIdx] = 0
  roadTableZ[zeroIdx] = 0
  roadTableYaw[zeroIdx] = 0

  // Forward integration from 0 to MAX_S
  let curX = 0
  let curZ = 0
  for (let s = 0; s < TABLE_MAX_S; s += TABLE_STEP) {
    const idx = Math.round((s - TABLE_MIN_S) / TABLE_STEP)
    const yaw = getRoadYaw(s)
    roadTableYaw[idx] = yaw

    const nextYaw = getRoadYaw(s + TABLE_STEP)
    const midYaw = (yaw + nextYaw) / 2
    curX += Math.sin(midYaw) * TABLE_STEP
    curZ += Math.cos(midYaw) * TABLE_STEP

    const nextIdx = idx + 1
    if (nextIdx < NUM_ENTRIES) {
      roadTableX[nextIdx] = curX
      roadTableZ[nextIdx] = curZ
    }
  }

  // Backward integration from 0 to MIN_S
  curX = 0
  curZ = 0
  for (let s = 0; s > TABLE_MIN_S; s -= TABLE_STEP) {
    const idx = Math.round((s - TABLE_MIN_S) / TABLE_STEP)
    const yaw = getRoadYaw(s)
    roadTableYaw[idx] = yaw

    const prevYaw = getRoadYaw(s - TABLE_STEP)
    const midYaw = (yaw + prevYaw) / 2
    curX -= Math.sin(midYaw) * TABLE_STEP
    curZ -= Math.cos(midYaw) * TABLE_STEP

    const prevIdx = idx - 1
    if (prevIdx >= 0) {
      roadTableX[prevIdx] = curX
      roadTableZ[prevIdx] = curZ
    }
  }
})()

/**
 * Computes exact 3D road frame at distance s with sub-millimeter interpolation.
 */
export function getRoadPoint(s) {
  const boundedS = Math.max(TABLE_MIN_S, Math.min(TABLE_MAX_S - TABLE_STEP, s))
  const floatIdx = (boundedS - TABLE_MIN_S) / TABLE_STEP
  const idx = Math.floor(floatIdx)
  const frac = floatIdx - idx

  const x0 = roadTableX[idx]
  const x1 = roadTableX[idx + 1]
  const z0 = roadTableZ[idx]
  const z1 = roadTableZ[idx + 1]
  const yaw0 = roadTableYaw[idx]
  const yaw1 = roadTableYaw[idx + 1]

  const x = (1 - frac) * x0 + frac * x1
  const z = (1 - frac) * z0 + frac * z1
  const yaw = (1 - frac) * yaw0 + frac * yaw1

  const cosYaw = Math.cos(yaw)
  const sinYaw = Math.sin(yaw)

  return {
    s,
    x,
    z,
    yaw,
    cosYaw,
    sinYaw,
    // Perpendicular normal vector pointing to right
    normalX: cosYaw,
    normalZ: -sinYaw,
    // Forward tangent vector
    tangentX: sinYaw,
    tangentZ: cosYaw,
  }
}

/**
 * Converts Frenet coordinates (s: distance along road, laneOffset: lateral offset)
 * to 3D world coordinates { worldX, worldZ, worldYaw }
 */
export function getLaneWorldPos(s, laneOffset = 0) {
  const pt = getRoadPoint(s)
  return {
    worldX: pt.x + laneOffset * pt.normalX,
    worldZ: pt.z + laneOffset * pt.normalZ,
    worldYaw: pt.yaw,
    s,
    laneOffset,
  }
}

/**
 * Generates an asphalt ribbon geometry between leftOffset and rightOffset.
 */
export function createCurvedRibbonGeometry(startS, endS, step, leftOffset, rightOffset, yElevation = 0) {
  const numSteps = Math.ceil((endS - startS) / step)
  const numVertices = (numSteps + 1) * 2
  const positions = new Float32Array(numVertices * 3)
  const normals = new Float32Array(numVertices * 3)
  const uvs = new Float32Array(numVertices * 2)
  const indices = []

  let vIdx = 0
  for (let i = 0; i <= numSteps; i++) {
    const s = Math.min(endS, startS + i * step)
    const pt = getRoadPoint(s)

    // Left vertex
    positions[vIdx * 3] = pt.x + leftOffset * pt.normalX
    positions[vIdx * 3 + 1] = yElevation
    positions[vIdx * 3 + 2] = pt.z + leftOffset * pt.normalZ

    normals[vIdx * 3] = 0
    normals[vIdx * 3 + 1] = 1
    normals[vIdx * 3 + 2] = 0

    uvs[vIdx * 2] = 0
    uvs[vIdx * 2 + 1] = (s - startS) / (endS - startS)

    // Right vertex
    positions[(vIdx + 1) * 3] = pt.x + rightOffset * pt.normalX
    positions[(vIdx + 1) * 3 + 1] = yElevation
    positions[(vIdx + 1) * 3 + 2] = pt.z + rightOffset * pt.normalZ

    normals[(vIdx + 1) * 3] = 0
    normals[(vIdx + 1) * 3 + 1] = 1
    normals[(vIdx + 1) * 3 + 2] = 0

    uvs[(vIdx + 1) * 2] = 1
    uvs[(vIdx + 1) * 2 + 1] = (s - startS) / (endS - startS)

    if (i < numSteps) {
      const a = vIdx
      const b = vIdx + 1
      const c = vIdx + 2
      const d = vIdx + 3
      // Counter-clockwise triangles facing UPWARDS (+Y):
      // Triangle 1: a -> c -> b
      // Triangle 2: b -> c -> d
      indices.push(a, c, b, b, c, d)
    }

    vIdx += 2
  }

  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3))
  geometry.setAttribute('uv', new THREE.BufferAttribute(uvs, 2))
  geometry.setIndex(indices)
  return geometry
}

/**
 * Generates perfectly aligned, non-slanted dashed lane divider markings.
 * Every dash is built directly with exact 4-corner vertices oriented along the road tangent,
 * completely eliminating any diagonal slanting or rotation distortion.
 */
export function createAlignedDashesGeometry(startS, endS, laneOffsets, dashLength = 4, gapLength = 6, width = 0.14) {
  const numDashes = Math.floor((endS - startS) / (dashLength + gapLength))
  const totalDashes = numDashes * laneOffsets.length
  const numVertices = totalDashes * 4
  const positions = new Float32Array(numVertices * 3)
  const normals = new Float32Array(numVertices * 3)
  const indices = []

  let vIdx = 0

  laneOffsets.forEach(laneOffset => {
    for (let d = 0; d < numDashes; d++) {
      const s = startS + d * (dashLength + gapLength) + dashLength / 2
      const pt = getRoadPoint(s)

      const cx = pt.x + laneOffset * pt.normalX
      const cz = pt.z + laneOffset * pt.normalZ

      const halfL = dashLength / 2
      const halfW = width / 2

      const tx = pt.tangentX
      const tz = pt.tangentZ
      const nx = pt.normalX
      const nz = pt.normalZ

      // 4 exact corners of the rectangular dash (zero slant):
      positions[vIdx * 3] = cx - halfL * tx - halfW * nx
      positions[vIdx * 3 + 1] = 0.022
      positions[vIdx * 3 + 2] = cz - halfL * tz - halfW * nz

      positions[(vIdx + 1) * 3] = cx - halfL * tx + halfW * nx
      positions[(vIdx + 1) * 3 + 1] = 0.022
      positions[(vIdx + 1) * 3 + 2] = cz - halfL * tz + halfW * nz

      positions[(vIdx + 2) * 3] = cx + halfL * tx - halfW * nx
      positions[(vIdx + 2) * 3 + 1] = 0.022
      positions[(vIdx + 2) * 3 + 2] = cz + halfL * tz - halfW * nz

      positions[(vIdx + 3) * 3] = cx + halfL * tx + halfW * nx
      positions[(vIdx + 3) * 3 + 1] = 0.022
      positions[(vIdx + 3) * 3 + 2] = cz + halfL * tz + halfW * nz

      for (let k = 0; k < 4; k++) {
        normals[(vIdx + k) * 3] = 0
        normals[(vIdx + k) * 3 + 1] = 1
        normals[(vIdx + k) * 3 + 2] = 0
      }

      // Counter-clockwise triangles facing UPWARDS (+Y):
      // Triangle 1: v0 -> v2 -> v1
      // Triangle 2: v1 -> v2 -> v3
      indices.push(vIdx, vIdx + 2, vIdx + 1, vIdx + 1, vIdx + 2, vIdx + 3)
      vIdx += 4
    }
  })

  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3))
  geometry.setIndex(indices)
  return geometry
}

/**
 * Generates pedestrian zebra crosswalk markings at city intersections.
 */
export function createCrosswalkGeometry(s) {
  const pt = getRoadPoint(s)
  const numBars = 19
  const barWidth = 0.52
  const barLength = 4.2
  const spacing = 0.82
  const startOffset = -7.4

  const positions = new Float32Array(numBars * 4 * 3)
  const normals = new Float32Array(numBars * 4 * 3)
  const indices = []

  let vIdx = 0
  for (let i = 0; i < numBars; i++) {
    const laneOffset = startOffset + i * spacing
    const cx = pt.x + laneOffset * pt.normalX
    const cz = pt.z + laneOffset * pt.normalZ

    const halfL = barLength / 2
    const halfW = barWidth / 2
    const tx = pt.tangentX
    const tz = pt.tangentZ
    const nx = pt.normalX
    const nz = pt.normalZ

    // 4 exact corners of crosswalk bar at elevation 0.025 (above asphalt)
    // v0: -tangent, -normal
    positions[vIdx * 3] = cx - halfL * tx - halfW * nx
    positions[vIdx * 3 + 1] = 0.025
    positions[vIdx * 3 + 2] = cz - halfL * tz - halfW * nz

    // v1: -tangent, +normal
    positions[(vIdx + 1) * 3] = cx - halfL * tx + halfW * nx
    positions[(vIdx + 1) * 3 + 1] = 0.025
    positions[(vIdx + 1) * 3 + 2] = cz - halfL * tz + halfW * nz

    // v2: +tangent, -normal
    positions[(vIdx + 2) * 3] = cx + halfL * tx - halfW * nx
    positions[(vIdx + 2) * 3 + 1] = 0.025
    positions[(vIdx + 2) * 3 + 2] = cz + halfL * tz - halfW * nz

    // v3: +tangent, +normal
    positions[(vIdx + 3) * 3] = cx + halfL * tx + halfW * nx
    positions[(vIdx + 3) * 3 + 1] = 0.025
    positions[(vIdx + 3) * 3 + 2] = cz + halfL * tz + halfW * nz

    for (let k = 0; k < 4; k++) {
      normals[(vIdx + k) * 3] = 0
      normals[(vIdx + k) * 3 + 1] = 1
      normals[(vIdx + k) * 3 + 2] = 0
    }

    // Counter-clockwise triangles facing UPWARDS (+Y):
    // Triangle 1: v0 -> v2 -> v1
    // Triangle 2: v1 -> v2 -> v3
    indices.push(vIdx, vIdx + 2, vIdx + 1, vIdx + 1, vIdx + 2, vIdx + 3)
    vIdx += 4
  }

  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3))
  geometry.setIndex(indices)
  return geometry
}

/**
 * Generates a solid white Stop Line across the roadway at distance s.
 */
export function createStopLineGeometry(s, leftOffset = -7.4, rightOffset = 7.4, lineWidth = 0.75) {
  const pt = getRoadPoint(s)
  const halfW = lineWidth / 2
  const tx = pt.tangentX
  const tz = pt.tangentZ
  const nx = pt.normalX
  const nz = pt.normalZ

  const leftX = pt.x + leftOffset * nx
  const leftZ = pt.z + leftOffset * nz
  const rightX = pt.x + rightOffset * nx
  const rightZ = pt.z + rightOffset * nz

  const positions = new Float32Array(4 * 3)
  const normals = new Float32Array(4 * 3)

  // 4 corners of stop bar at elevation 0.025 (above asphalt)
  positions[0] = leftX - halfW * tx
  positions[1] = 0.025
  positions[2] = leftZ - halfW * tz

  positions[3] = rightX - halfW * tx
  positions[4] = 0.025
  positions[5] = rightZ - halfW * tz

  positions[6] = leftX + halfW * tx
  positions[7] = 0.025
  positions[8] = leftZ + halfW * tz

  positions[9] = rightX + halfW * tx
  positions[10] = 0.025
  positions[11] = rightZ + halfW * tz

  for (let k = 0; k < 4; k++) {
    normals[k * 3] = 0
    normals[k * 3 + 1] = 1
    normals[k * 3 + 2] = 0
  }

  // Counter-clockwise triangles facing UPWARDS (+Y):
  const indices = [0, 2, 1, 1, 2, 3]

  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3))
  geometry.setIndex(indices)
  return geometry
}

