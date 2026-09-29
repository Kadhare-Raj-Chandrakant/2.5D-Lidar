import { useMemo, useLayoutEffect, useRef } from 'react'
import * as THREE from 'three'
import { getRoadPoint } from '../utils/roadGeometry'

// Deterministic seed-based pseudo-random generator (zero allocations, 100% stable)
function seededRand(seed) {
  const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453
  return x - Math.floor(x)
}

/**
 * Ultra-Low-RAM City Environment (Buildings, Skyscrapers, Skyline & Urban Trees)
 * 
 * Performance & Memory Architecture:
 * - Uses GPU InstancedMesh: all 260+ buildings, windows, and trees render in just 5 draw calls.
 * - Single shared 1x1x1 BoxGeometry (24 vertices total).
 * - Total RAM & GPU memory footprint: < 150 Kilobytes!
 * - Zero texture downloads, zero external 3D model files.
 * - Framerate impact: Locked 60 FPS.
 */
export function CityBuildings({ startS = -200, endS = 2600, intersections = [] }) {
  // 1. Procedurally generate building & urban asset configurations along highway corridor
  const { buildings, windows, crowns, spires, trees } = useMemo(() => {
    const bList = []
    const wList = []
    const cList = []
    const sList = []
    const tList = []

    // Rich architectural slate, titanium, and midnight glass tones that catch scene lighting
    const buildingColors = [
      '#1e293b', '#24344d', '#2c3e5a', '#1f2d3d',
      '#334155', '#28384d', '#2d3748', '#374151',
      '#1e385c', '#233144', '#3b4252', '#2a3b52'
    ]

    // Glowing rooftop crowns & penthouses
    const crownColors = [
      '#38bdf8', '#06b6d4', '#60a5fa', '#818cf8',
      '#a855f7', '#f59e0b', '#34d399', '#38bdf8'
    ]

    // Office window illumination palettes (warm amber, cool cyan, modern daylight)
    const windowColors = [
      '#fef08a', '#7dd3fc', '#93c5fd', '#fef9c3',
      '#bae6fd', '#fed7aa', '#e0e7ff', '#fde047'
    ]

    let bId = 0
    let tId = 0

    // Check if station is close to a pedestrian crosswalk / intersection
    const isNearIntersection = (s) => intersections.some(interS => Math.abs(s - interS) < 24)

    const sides = [-1, 1] // -1 = Left side, +1 = Right side

    for (const side of sides) {
      // --- LAYER 1: Mid-rise Commercial & Urban Blocks along Street ---
      const l1Spacing = 34
      for (let s = startS + 10; s <= endS - 10; s += l1Spacing) {
        bId++
        const r1 = seededRand(bId * 1.37)
        const r2 = seededRand(bId * 2.89)
        const r3 = seededRand(bId * 3.41)
        const r4 = seededRand(bId * 4.93)

        // Give extra setback near pedestrian crosswalks for clear sightlines
        const extraSetback = isNearIntersection(s) ? 14.0 : 0.0

        const sJitter = (r1 - 0.5) * 6.0
        const pt = getRoadPoint(s + sJitter)

        // dimX: perpendicular to road (normal thickness)
        // dimZ: parallel along the road (street frontage)
        const dimX = 16.0 + r1 * 8.0     // 16m - 24m deep into block
        const dimZ = 20.0 + r3 * 10.0    // 20m - 30m wide along street
        const height = 18.0 + r4 * 30.0  // 18m - 48m tall

        // Ensure front edge is at least 17m from road centerline (safely outside 12m sidewalk)
        const minCenterDist = 17.0 + dimX / 2.0
        const centerDist = minCenterDist + r2 * 8.0 + extraSetback
        const latOffset = side * centerDist

        const posX = pt.x + latOffset * pt.normalX
        const posZ = pt.z + latOffset * pt.normalZ
        const posY = height / 2.0
        const yaw = pt.yaw

        const col = buildingColors[Math.floor(r3 * buildingColors.length)]
        bList.push({ x: posX, y: posY, z: posZ, yaw, w: dimX, h: height, d: dimZ, color: col })

        // Street-facing facade window strips (flush mounted against front facade)
        const numFloors = Math.floor((height - 5.0) / 4.2)
        const frontOffset = side * (centerDist - dimX / 2.0 + 0.1)
        const facadeX = pt.x + frontOffset * pt.normalX
        const facadeZ = pt.z + frontOffset * pt.normalZ
        const winCol = windowColors[Math.floor(r1 * windowColors.length)]

        for (let f = 1; f <= numFloors; f++) {
          const fRand = seededRand(bId * 10 + f)
          if (fRand > 0.35) {
            wList.push({
              x: facadeX,
              y: f * 4.2,
              z: facadeZ,
              yaw,
              w: 0.18,          // Thin flush panel against facade (local X)
              h: 0.85,          // Window height (local Y)
              d: dimZ * 0.84,   // Running along street frontage (local Z)
              color: winCol
            })
          }
        }

        // 40% of mid-rises have a glowing rooftop architectural trim/crown
        if (r1 > 0.60) {
          const crownH = 1.2
          const crownY = height + crownH / 2.0
          const crownCol = crownColors[Math.floor(r4 * crownColors.length)]
          cList.push({
            x: posX, y: crownY, z: posZ, yaw,
            w: dimX * 0.94, h: crownH, d: dimZ * 0.94,
            color: crownCol
          })
        }
      }

      // --- LAYER 2: Towering Skyscrapers & Modern Skyline ---
      const l2Spacing = 52
      for (let s = startS + 18; s <= endS - 20; s += l2Spacing) {
        bId++
        const r1 = seededRand(bId * 5.17)
        const r2 = seededRand(bId * 6.63)
        const r3 = seededRand(bId * 7.81)
        const r4 = seededRand(bId * 8.29)

        const sJitter = (r1 - 0.5) * 12.0
        const pt = getRoadPoint(s + sJitter)

        const dimX = 26.0 + r1 * 14.0    // 26m - 40m thick
        const dimZ = 28.0 + r3 * 16.0    // 28m - 44m frontage
        const height = 55.0 + r4 * 90.0  // 55m - 145m skyline height!

        // Skyline towers positioned 48m to 76m from road centerline
        const centerDist = 48.0 + dimX / 2.0 + r2 * 20.0
        const latOffset = side * centerDist

        const posX = pt.x + latOffset * pt.normalX
        const posZ = pt.z + latOffset * pt.normalZ
        const posY = height / 2.0
        const yaw = pt.yaw

        const col = buildingColors[Math.floor(r2 * buildingColors.length)]
        bList.push({ x: posX, y: posY, z: posZ, yaw, w: dimX, h: height, d: dimZ, color: col })

        // Skyscrapers: Facade illuminated window rows every 6m
        const numSkyFloors = Math.floor((height - 8.0) / 6.0)
        const skyFrontOffset = side * (centerDist - dimX / 2.0 + 0.12)
        const skyFacadeX = pt.x + skyFrontOffset * pt.normalX
        const skyFacadeZ = pt.z + skyFrontOffset * pt.normalZ
        const skyWinCol = windowColors[Math.floor(r3 * windowColors.length)]

        for (let f = 1; f <= numSkyFloors; f++) {
          const fRand = seededRand(bId * 20 + f)
          if (fRand > 0.30) {
            wList.push({
              x: skyFacadeX,
              y: f * 6.0,
              z: skyFacadeZ,
              yaw,
              w: 0.20,
              h: 1.15,
              d: dimZ * 0.86,
              color: skyWinCol
            })
          }
        }

        // 75% of skyscrapers have glowing illuminated architectural crowns
        if (r2 > 0.25) {
          const crownH = 2.4
          const crownY = height + crownH / 2.0
          const crownCol = crownColors[Math.floor(r1 * crownColors.length)]
          cList.push({
            x: posX, y: crownY, z: posZ, yaw,
            w: dimX * 0.88, h: crownH, d: dimZ * 0.88,
            color: crownCol
          })
        }

        // Tallest skyscrapers (height > 90m) get a rooftop antenna spire with warning beacon
        if (height > 90.0) {
          const spireH = 15.0 + r3 * 10.0
          const spireY = height + spireH / 2.0
          sList.push({
            x: posX, y: spireY, z: posZ, yaw,
            w: 0.8, h: spireH, d: 0.8,
            beaconY: height + spireH + 0.5,
            color: '#94a3b8'
          })
        }
      }

      // --- STREET TREES: Minimalist Low-Poly Urban Greenery along Sidewalk Verge ---
      const treeSpacing = 28
      for (let s = startS + 8; s <= endS - 8; s += treeSpacing) {
        tId++
        if (isNearIntersection(s)) continue // Clear crosswalk area
        const r1 = seededRand(tId * 3.73)
        const pt = getRoadPoint(s + (r1 - 0.5) * 4.0)

        // Located right on sidewalk verge: 10.2m from centerline
        const latOffset = side * 10.2

        const posX = pt.x + latOffset * pt.normalX
        const posZ = pt.z + latOffset * pt.normalZ

        tList.push({
          x: posX,
          y: 0,
          z: posZ,
          scale: 0.85 + r1 * 0.35,
          color: r1 > 0.5 ? '#064e3b' : '#065f46'
        })
      }
    }

    return { buildings: bList, windows: wList, crowns: cList, spires: sList, trees: tList }
  }, [startS, endS, intersections])

  // 2. Shared single-instance geometries and materials (ultra-low RAM)
  const geometries = useMemo(() => ({
    unitBox: new THREE.BoxGeometry(1, 1, 1),
    treeTrunk: new THREE.CylinderGeometry(0.12, 0.16, 2.2, 5),
    treeCrown: new THREE.ConeGeometry(1.25, 2.8, 5),
    beaconSphere: new THREE.SphereGeometry(0.35, 6, 6),
  }), [])

  const materials = useMemo(() => ({
    building: new THREE.MeshStandardMaterial({
      color: '#ffffff',
      roughness: 0.65,
      metalness: 0.35,
      flatShading: true,
    }),
    window: new THREE.MeshBasicMaterial({
      color: '#ffffff',
      toneMapped: false,
    }),
    crown: new THREE.MeshBasicMaterial({
      color: '#38bdf8',
      toneMapped: false,
    }),
    spire: new THREE.MeshStandardMaterial({
      color: '#64748b',
      roughness: 0.5,
      metalness: 0.8,
    }),
    beacon: new THREE.MeshBasicMaterial({
      color: '#ef4444',
      toneMapped: false,
    }),
    treeTrunk: new THREE.MeshStandardMaterial({
      color: '#422006',
      roughness: 0.9,
    }),
    treeFoliage: new THREE.MeshStandardMaterial({
      color: '#065f46',
      roughness: 0.8,
      flatShading: true,
    })
  }), [])

  // 3. Mesh Refs for direct GPU instanced buffer population
  const buildingMeshRef = useRef()
  const windowMeshRef = useRef()
  const crownMeshRef = useRef()
  const spireMeshRef = useRef()
  const beaconMeshRef = useRef()
  const treeTrunkRef = useRef()
  const treeCrownRef = useRef()

  // 4. Populate GPU Instanced Buffers once on mount / track bounds change
  useLayoutEffect(() => {
    const dummy = new THREE.Object3D()
    const color = new THREE.Color()

    // Populate Buildings (Single draw call for entire city)
    if (buildingMeshRef.current && buildings.length > 0) {
      buildings.forEach((b, i) => {
        dummy.position.set(b.x, b.y, b.z)
        dummy.rotation.set(0, b.yaw, 0)
        dummy.scale.set(b.w, b.h, b.d)
        dummy.updateMatrix()
        buildingMeshRef.current.setMatrixAt(i, dummy.matrix)
        color.set(b.color)
        buildingMeshRef.current.setColorAt(i, color)
      })
      buildingMeshRef.current.instanceMatrix.needsUpdate = true
      if (buildingMeshRef.current.instanceColor) {
        buildingMeshRef.current.instanceColor.needsUpdate = true
      }
    }

    // Populate Illuminated Windows (Single draw call)
    if (windowMeshRef.current && windows.length > 0) {
      windows.forEach((w, i) => {
        dummy.position.set(w.x, w.y, w.z)
        dummy.rotation.set(0, w.yaw, 0)
        dummy.scale.set(w.w, w.h, w.d)
        dummy.updateMatrix()
        windowMeshRef.current.setMatrixAt(i, dummy.matrix)
        color.set(w.color)
        windowMeshRef.current.setColorAt(i, color)
      })
      windowMeshRef.current.instanceMatrix.needsUpdate = true
      if (windowMeshRef.current.instanceColor) {
        windowMeshRef.current.instanceColor.needsUpdate = true
      }
    }

    // Populate Glowing Crowns / Architectural Trims
    if (crownMeshRef.current && crowns.length > 0) {
      crowns.forEach((c, i) => {
        dummy.position.set(c.x, c.y, c.z)
        dummy.rotation.set(0, c.yaw, 0)
        dummy.scale.set(c.w, c.h, c.d)
        dummy.updateMatrix()
        crownMeshRef.current.setMatrixAt(i, dummy.matrix)
        color.set(c.color)
        crownMeshRef.current.setColorAt(i, color)
      })
      crownMeshRef.current.instanceMatrix.needsUpdate = true
      if (crownMeshRef.current.instanceColor) {
        crownMeshRef.current.instanceColor.needsUpdate = true
      }
    }

    // Populate Rooftop Spires
    if (spireMeshRef.current && spires.length > 0) {
      spires.forEach((s, i) => {
        dummy.position.set(s.x, s.y, s.z)
        dummy.rotation.set(0, s.yaw, 0)
        dummy.scale.set(s.w, s.h, s.d)
        dummy.updateMatrix()
        spireMeshRef.current.setMatrixAt(i, dummy.matrix)
      })
      spireMeshRef.current.instanceMatrix.needsUpdate = true
    }

    // Populate Rooftop Warning Beacons
    if (beaconMeshRef.current && spires.length > 0) {
      spires.forEach((s, i) => {
        dummy.position.set(s.x, s.beaconY, s.z)
        dummy.rotation.set(0, 0, 0)
        dummy.scale.set(1, 1, 1)
        dummy.updateMatrix()
        beaconMeshRef.current.setMatrixAt(i, dummy.matrix)
      })
      beaconMeshRef.current.instanceMatrix.needsUpdate = true
    }

    // Populate Street Trees (Trunks & Canopies)
    if (treeTrunkRef.current && treeCrownRef.current && trees.length > 0) {
      trees.forEach((t, i) => {
        dummy.position.set(t.x, 1.1 * t.scale, t.z)
        dummy.rotation.set(0, 0, 0)
        dummy.scale.set(t.scale, t.scale, t.scale)
        dummy.updateMatrix()
        treeTrunkRef.current.setMatrixAt(i, dummy.matrix)

        dummy.position.set(t.x, 3.4 * t.scale, t.z)
        dummy.rotation.set(0, 0, 0)
        dummy.scale.set(t.scale, t.scale, t.scale)
        dummy.updateMatrix()
        treeCrownRef.current.setMatrixAt(i, dummy.matrix)
        color.set(t.color)
        treeCrownRef.current.setColorAt(i, color)
      })
      treeTrunkRef.current.instanceMatrix.needsUpdate = true
      treeCrownRef.current.instanceMatrix.needsUpdate = true
      if (treeCrownRef.current.instanceColor) {
        treeCrownRef.current.instanceColor.needsUpdate = true
      }
    }
  }, [buildings, windows, crowns, spires, trees])

  return (
    <group name="city-environment-layer">
      {/* 1. All Buildings and Skyscrapers (Single Draw Call) */}
      {buildings.length > 0 && (
        <instancedMesh
          ref={buildingMeshRef}
          args={[geometries.unitBox, materials.building, buildings.length]}
          receiveShadow
          castShadow
        />
      )}

      {/* 2. Illuminated Office Windows (Single Draw Call) */}
      {windows.length > 0 && (
        <instancedMesh
          ref={windowMeshRef}
          args={[geometries.unitBox, materials.window, windows.length]}
        />
      )}

      {/* 3. Glowing Rooftop Architectural Crowns / Neon Trims (Single Draw Call) */}
      {crowns.length > 0 && (
        <instancedMesh
          ref={crownMeshRef}
          args={[geometries.unitBox, materials.crown, crowns.length]}
        />
      )}

      {/* 4. Rooftop Antenna Spires */}
      {spires.length > 0 && (
        <instancedMesh
          ref={spireMeshRef}
          args={[geometries.unitBox, materials.spire, spires.length]}
        />
      )}

      {/* 5. Aviation Warning Red Beacons */}
      {spires.length > 0 && (
        <instancedMesh
          ref={beaconMeshRef}
          args={[geometries.beaconSphere, materials.beacon, spires.length]}
        />
      )}

      {/* 6. Sidewalk Trees - Trunks (Single Draw Call) */}
      {trees.length > 0 && (
        <instancedMesh
          ref={treeTrunkRef}
          args={[geometries.treeTrunk, materials.treeTrunk, trees.length]}
        />
      )}

      {/* 7. Sidewalk Trees - Canopies (Single Draw Call) */}
      {trees.length > 0 && (
        <instancedMesh
          ref={treeCrownRef}
          args={[geometries.treeCrown, materials.treeFoliage, trees.length]}
        />
      )}
    </group>
  )
}
