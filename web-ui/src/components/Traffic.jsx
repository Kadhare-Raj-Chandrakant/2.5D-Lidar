import { Html } from '@react-three/drei'
import { Pedestrian } from './Pedestrian'

export function Traffic({ vehicles = [] }) {
  if (!vehicles.length) return null

  // Deduplicate vehicles and pedestrians cleanly without dropping nearby pedestrians
  const uniqueVehicles = []
  vehicles.forEach((obj) => {
    if (!obj.bbox_3d) return
    const posX = obj.bbox_3d.worldX !== undefined ? obj.bbox_3d.worldX : obj.bbox_3d.y
    const posZ = obj.bbox_3d.worldZ !== undefined ? obj.bbox_3d.worldZ : obj.bbox_3d.x
    const isPed = (obj.class_name === 'pedestrian' || obj.bbox_3d.class_name === 'pedestrian')
    
    const isDuplicate = uniqueVehicles.some((u) => {
      if (u.id !== undefined && obj.id !== undefined && u.id === obj.id) return true
      const ux = u.bbox_3d.worldX !== undefined ? u.bbox_3d.worldX : u.bbox_3d.y
      const uz = u.bbox_3d.worldZ !== undefined ? u.bbox_3d.worldZ : u.bbox_3d.x
      const thresh = isPed ? 0.6 : 3.8
      return Math.hypot(posX - ux, posZ - uz) < thresh
    })

    if (!isDuplicate) {
      uniqueVehicles.push(obj)
    }
  })

  return (
    <group name="traffic">
      {uniqueVehicles.map((obj, i) => {
        if (!obj.bbox_3d) return null

        const { x, y, z, length, width, height, yaw = 0, class_name, track_id, worldX, worldZ, worldYaw, isCrossing } = obj.bbox_3d
        const speedKmh = obj.currentSpeed !== undefined ? Math.round(obj.currentSpeed * 3.6) : (obj.speed ? Math.round(obj.speed * 3.6) : 26)

        const posX = worldX !== undefined ? worldX : y
        const posZ = worldZ !== undefined ? worldZ : x
        const rotYaw = worldYaw !== undefined ? worldYaw : yaw

        if (class_name === 'pedestrian' || class_name === 'person') {
          return (
            <Pedestrian
              key={track_id || i}
              position={[posX, 0, posZ]}
              rotation={[0, rotYaw, 0]}
              isCrossing={isCrossing !== undefined ? isCrossing : Math.abs(y) < 7.5}
              walkSpeed={obj.speed || 1.4}
              jacketColor={obj.bbox_3d?.jacketColor || (track_id % 2 === 0 ? '#0284c7' : '#ef4444')}
              label={`Pedestrian #${track_id || i}`}
            />
          )
        }

        return (
          <OtherVehicle
            key={track_id || i}
            position={[posX, 0, posZ]}
            rotation={[0, rotYaw, 0]}
            dimensions={[width || 1.9, height || 1.5, length || 4.5]}
            className={class_name}
            trackId={track_id || i}
            speedKmh={speedKmh}
          />
        )
      })}
    </group>
  )
}

function getVehiclePalette(className, trackId = 0) {
  if (className === 'truck') {
    return { body: '#f97316', cabin: '#ea580c', roof: '#c2410c', name: 'Truck', icon: '🚚' }
  }
  if (className === 'bus') {
    return { body: '#eab308', cabin: '#ca8a04', roof: '#a16207', name: 'Bus', icon: '🚌' }
  }
  const carColors = [
    { body: '#ef4444', cabin: '#1e293b', roof: '#b91c1c', name: 'Sedan', icon: '🚗' },
    { body: '#06b6d4', cabin: '#0f172a', roof: '#0891b2', name: 'EV Sedan', icon: '🚙' },
    { body: '#facc15', cabin: '#1e293b', roof: '#ca8a04', name: 'Cab', icon: '🚕' },
    { body: '#f8fafc', cabin: '#0f172a', roof: '#cbd5e1', name: 'SUV', icon: '🚙' },
  ]
  return carColors[trackId % carColors.length]
}

function OtherVehicle({ position, rotation, dimensions, className, trackId, speedKmh }) {
  const [w, h, l] = dimensions
  const palette = getVehiclePalette(className, trackId)
  const isTruck = className === 'truck'

  const wheelRadius = isTruck ? 0.44 : 0.34
  const wheelThickness = isTruck ? 0.28 : 0.22
  const wheelY = wheelRadius
  const wheelOffsetZ = l * 0.32
  const wheelOffsetX = w * 0.48

  return (
    <group position={position} rotation={rotation}>
      {/* 3D Detection Bounding Wireframe (Autonomous Perception bounding box) */}
      <mesh position={[0, h / 2 + 0.1, 0]}>
        <boxGeometry args={[w * 1.15, h * 1.15, l * 1.1]} />
        <meshBasicMaterial color="#38bdf8" wireframe transparent opacity={0.45} />
      </mesh>

      {/* Floating 3D AR Perception Tag */}
      <Html position={[0, h + 0.75, 0]} center distanceFactor={14} zIndexRange={[100, 0]}>
        <div style={{
          background: 'rgba(15, 23, 42, 0.92)',
          border: '1.5px solid #38bdf8',
          boxShadow: '0 0 10px rgba(56, 189, 248, 0.5)',
          borderRadius: '16px',
          padding: '3px 9px',
          color: '#ffffff',
          fontFamily: 'Inter, system-ui, sans-serif',
          fontSize: '11px',
          fontWeight: '700',
          whiteSpace: 'nowrap',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          pointerEvents: 'none',
          userSelect: 'none'
        }}>
          <span>{palette.icon} {palette.name} #{trackId}</span>
          <span style={{ color: '#38bdf8' }}>|</span>
          <span style={{ color: '#4ade80' }}>{speedKmh} km/h</span>
        </div>
      </Html>

      {/* Main Body */}
      <mesh castShadow receiveShadow position={[0, wheelRadius + (h * 0.55) / 2, 0]}>
        <boxGeometry args={[w * 0.94, h * 0.55, l * 0.94]} />
        <meshStandardMaterial color={palette.body} metalness={0.4} roughness={0.3} />
      </mesh>

      {/* Cabin / Windows */}
      <mesh castShadow receiveShadow position={[0, wheelRadius + h * 0.55 + (h * 0.42) / 2, isTruck ? l * 0.22 : -l * 0.08]}>
        <boxGeometry args={[w * 0.86, h * 0.42, isTruck ? l * 0.44 : l * 0.52]} />
        <meshStandardMaterial color={palette.cabin} metalness={0.7} roughness={0.2} />
      </mesh>

      {/* Cargo Bed for Truck */}
      {isTruck && (
        <mesh castShadow receiveShadow position={[0, wheelRadius + h * 0.48 + 0.35, -l * 0.16]}>
          <boxGeometry args={[w * 0.92, h * 0.68, l * 0.6]} />
          <meshStandardMaterial color="#cbd5e1" metalness={0.2} roughness={0.5} />
        </mesh>
      )}

      {/* 4 Wheels */}
      {[-wheelOffsetX, wheelOffsetX].map((wx, xi) => (
        [-wheelOffsetZ, wheelOffsetZ].map((wz, zi) => (
          <group key={`${xi}-${zi}`} position={[wx, wheelY, wz]} rotation={[0, 0, Math.PI / 2]}>
            {/* Rubber Tire */}
            <mesh castShadow>
              <cylinderGeometry args={[wheelRadius, wheelRadius, wheelThickness, 14]} />
              <meshStandardMaterial color="#0f172a" roughness={0.9} />
            </mesh>
            {/* Metallic Wheel Rim */}
            <mesh position={[0, (xi === 0 ? -1 : 1) * (wheelThickness / 2 + 0.01), 0]}>
              <cylinderGeometry args={[wheelRadius * 0.58, wheelRadius * 0.58, 0.02, 12]} />
              <meshStandardMaterial color="#e2e8f0" metalness={0.9} roughness={0.15} />
            </mesh>
          </group>
        ))
      ))}

      {/* Front LED Headlights */}
      <mesh position={[w * 0.36, wheelRadius + 0.25, l * 0.47]}>
        <boxGeometry args={[0.22, 0.14, 0.05]} />
        <meshBasicMaterial color="#ffffff" toneMapped={false} />
      </mesh>
      <mesh position={[-w * 0.36, wheelRadius + 0.25, l * 0.47]}>
        <boxGeometry args={[0.22, 0.14, 0.05]} />
        <meshBasicMaterial color="#ffffff" toneMapped={false} />
      </mesh>

      {/* Rear Neon Taillights */}
      <mesh position={[w * 0.36, wheelRadius + 0.25, -l * 0.47]}>
        <boxGeometry args={[0.22, 0.14, 0.05]} />
        <meshBasicMaterial color="#ff2222" toneMapped={false} />
      </mesh>
      <mesh position={[-w * 0.36, wheelRadius + 0.25, -l * 0.47]}>
        <boxGeometry args={[0.22, 0.14, 0.05]} />
        <meshBasicMaterial color="#ff2222" toneMapped={false} />
      </mesh>
    </group>
  )
}