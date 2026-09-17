import { Pedestrian } from './Pedestrian'

export function Traffic({ vehicles = [] }) {
  if (!vehicles.length) return null

  return (
    <group name="traffic">
      {vehicles.map((obj, i) => {
        if (!obj.bbox_3d) return null

        const { x, y, z, length, width, height, yaw = 0, class_name, track_id, worldX, worldZ, worldYaw, isCrossing } = obj.bbox_3d
        const color = getVehicleColor(class_name)

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
            position={[posX, height / 2 + 0.1, posZ]}
            rotation={[0, rotYaw, 0]}
            dimensions={[width, height, length]}
            color={color}
            className={class_name}
            trackId={track_id}
          />
        )
      })}
    </group>
  )
}

function getVehicleColor(className) {
  const colors = {
    car: '#3b82f6', // sleek dark sapphire
    truck: '#64748b', // slate
    bus: '#d97706', // amber
    motorcycle: '#06b6d4', // cyan
    bicycle: '#10b981', // emerald
    person: '#f43f5e', // rose
  }
  return colors[className] || '#3b82f6'
}

function OtherVehicle({ position, rotation, dimensions, color, className, trackId }) {
  const [w, h, l] = dimensions

  return (
    <group position={position} rotation={rotation}>
      {/* 3D Detection Bounding Wireframe (Autonomous Perception bounding box) */}
      <mesh>
        <boxGeometry args={[w * 1.05, h * 1.05, l * 1.05]} />
        <meshBasicMaterial color="#5ac8fa" wireframe transparent opacity={0.3} />
      </mesh>

      {/* Main body */}
      <mesh castShadow receiveShadow>
        <boxGeometry args={[w * 0.92, h * 0.65, l * 0.92]} />
        <meshStandardMaterial color={color} metalness={0.6} roughness={0.35} />
      </mesh>

      {/* Cabin */}
      <mesh castShadow receiveShadow position={[0, h * 0.45, -l * 0.1]}>
        <boxGeometry args={[w * 0.78, h * 0.48, l * 0.48]} />
        <meshStandardMaterial color="#0f172a" metalness={0.4} roughness={0.4} />
      </mesh>

      {/* Front and rear lights */}
      {className !== 'person' && className !== 'bicycle' && (
        <>
          <mesh position={[w * 0.38, 0.2, l * 0.46]}>
            <sphereGeometry args={[0.08, 8, 8]} />
            <meshBasicMaterial color="#ffffff" />
          </mesh>
          <mesh position={[-w * 0.38, 0.2, l * 0.46]}>
            <sphereGeometry args={[0.08, 8, 8]} />
            <meshBasicMaterial color="#ffffff" />
          </mesh>
          <mesh position={[w * 0.38, 0.2, -l * 0.46]}>
            <sphereGeometry args={[0.08, 8, 8]} />
            <meshBasicMaterial color="#ff3b30" />
          </mesh>
          <mesh position={[-w * 0.38, 0.2, -l * 0.46]}>
            <sphereGeometry args={[0.08, 8, 8]} />
            <meshBasicMaterial color="#ff3b30" />
          </mesh>
        </>
      )}
    </group>
  )
}