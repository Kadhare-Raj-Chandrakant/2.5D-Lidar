export function DebugPanel({ vehicleState, perception, trajectory, behavior }) {
  const showDebug = true

  if (!showDebug || !vehicleState) return null

  const objects = perception?.objects || []
  const trackedCount = objects.filter(o => o.track_id !== undefined).length

  return (
    <div style={styles.container}>
      <div style={styles.panel}>
        <div style={styles.header}>
          <span style={styles.title}>DEBUG PANEL</span>
          <span style={styles.badge}>LIVE</span>
        </div>

        <section style={styles.section}>
          <h4 style={styles.sectionTitle}>PERCEPTION</h4>
          <div style={styles.grid}>
            <div><span style={styles.label}>Objects:</span> <span style={styles.value}>{objects.length}</span></div>
            <div><span style={styles.label}>Tracked:</span> <span style={styles.value}>{trackedCount}</span></div>
            <div><span style={styles.label}>Lanes:</span> <span style={styles.value}>{perception?.lanes?.length || 0}</span></div>
            <div><span style={styles.label}>Free Space:</span> <span style={styles.value}>{perception?.free_space ? 'Yes' : 'No'}</span></div>
          </div>
          {objects.slice(0, 5).map((obj, i) => (
            <div key={i} style={styles.objectRow}>
              <span style={{...styles.objId, background: getClassColor(obj.class_name)}}>
                {obj.track_id !== undefined ? `ID:${obj.track_id}` : `OBJ:${obj.id}`}
              </span>
              <span style={styles.objClass}>{obj.class_name}</span>
              <span style={styles.objPos}>
                ({obj.bbox_3d?.x.toFixed(1)}, {obj.bbox_3d?.y.toFixed(1)})
              </span>
              <span style={styles.objConf}>{(obj.bbox_3d?.confidence * 100).toFixed(0)}%</span>
            </div>
          ))}
        </section>

        <section style={styles.section}>
          <h4 style={styles.sectionTitle}>PLANNING</h4>
          <div style={styles.grid}>
            <div><span style={styles.label}>Behavior:</span> <span style={styles.value}>{behavior?.state || 'N/A'}</span></div>
            <div><span style={styles.label}>Waypoints:</span> <span style={styles.value}>{trajectory?.waypoints?.length || 0}</span></div>
            <div><span style={styles.label}>Plan Time:</span> <span style={styles.value}>{(trajectory?.planning_time * 1000).toFixed(1)}ms</span></div>
            <div><span style={styles.label}>Valid:</span> <span style={{...styles.value, color: trajectory?.valid ? '#00ff88' : '#ff4444'}}>{trajectory?.valid ? 'Yes' : 'No'}</span></div>
          </div>
          {trajectory?.waypoints?.slice(0, 3).map((wp, i) => (
            <div key={i} style={styles.waypointRow}>
              <span style={styles.label}>WP {i * 5}:</span>
              <span style={styles.value}>
                ({wp.x.toFixed(1)}, {wp.y.toFixed(1)}) @ {(wp.speed * 3.6).toFixed(0)}km/h
              </span>
            </div>
          ))}
        </section>

        <section style={styles.section}>
          <h4 style={styles.sectionTitle}>CONTROL</h4>
          <div style={styles.grid}>
            <div><span style={styles.label}>Steer:</span> <span style={styles.value}>{vehicleState.steer_angle.toFixed(3)} rad</span></div>
            <div><span style={styles.label}>Throttle:</span> <span style={styles.value}>{(vehicleState.throttle * 100).toFixed(0)}%</span></div>
            <div><span style={styles.label}>Brake:</span> <span style={styles.value}>{(vehicleState.brake * 100).toFixed(0)}%</span></div>
          </div>
        </section>

        <section style={styles.section}>
          <h4 style={styles.sectionTitle}>VEHICLE STATE</h4>
          <div style={styles.grid}>
            <div><span style={styles.label}>Pos:</span> <span style={styles.value}>({vehicleState.x.toFixed(2)}, {vehicleState.y.toFixed(2)})</span></div>
            <div><span style={styles.label}>Yaw:</span> <span style={styles.value}>{vehicleState.yaw.toFixed(3)} rad</span></div>
            <div><span style={styles.label}>Speed:</span> <span style={styles.value}>{vehicleState.speed.toFixed(2)} m/s</span></div>
            <div><span style={styles.label}>Accel:</span> <span style={styles.value}>{vehicleState.acceleration.toFixed(2)} m/s²</span></div>
          </div>
        </section>
      </div>
    </div>
  )
}

function getClassColor(className) {
  const colors = {
    car: '#e84d1a',
    truck: '#b83d1a',
    bus: '#a83d1a',
    motorcycle: '#ff6b35',
    bicycle: '#ff8c42',
    person: '#ff3366',
  }
  return colors[className] || '#58a6ff'
}

const styles = {
  container: {
    position: 'fixed',
    top: 20,
    right: 20,
    zIndex: 100,
    pointerEvents: 'auto',
    maxHeight: '90vh',
    overflow: 'auto',
  },
  panel: {
    background: 'rgba(13, 17, 23, 0.98)',
    border: '1px solid #30363d',
    borderRadius: 8,
    padding: 16,
    minWidth: 380,
    maxWidth: 420,
    backdropFilter: 'blur(10px)',
    boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
    fontFamily: '"JetBrains Mono", "Fira Code", monospace',
    fontSize: '11px',
    lineHeight: 1.5,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    paddingBottom: 12,
    borderBottom: '1px solid #30363d',
  },
  title: {
    fontSize: '10px',
    fontWeight: 600,
    letterSpacing: '1px',
    color: '#8b949e',
    textTransform: 'uppercase',
  },
  badge: {
    background: '#00ff88',
    color: '#0d1117',
    fontSize: '9px',
    fontWeight: 700,
    padding: '2px 6px',
    borderRadius: 3,
  },
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: '10px',
    fontWeight: 600,
    letterSpacing: '0.5px',
    color: '#58a6ff',
    marginBottom: 8,
    textTransform: 'uppercase',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '4px 12px',
    marginBottom: 8,
  },
  label: {
    color: '#8b949e',
  },
  value: {
    color: '#e6edf3',
    fontWeight: 500,
    textAlign: 'right',
  },
  objectRow: {
    display: 'flex',
    gap: 8,
    padding: '4px 0',
    fontSize: '10px',
    borderBottom: '1px solid #1f2428',
  },
  objId: {
    background: '#58a6ff',
    color: '#0d1117',
    padding: '1px 4px',
    borderRadius: 2,
    fontWeight: 600,
    minWidth: 50,
    textAlign: 'center',
  },
  objClass: {
    color: '#e6edf3',
    minWidth: 70,
  },
  objPos: {
    color: '#8b949e',
    flex: 1,
  },
  objConf: {
    color: '#00ff88',
    fontWeight: 500,
  },
  waypointRow: {
    padding: '3px 0',
    fontSize: '10px',
    color: '#8b949e',
  },
}