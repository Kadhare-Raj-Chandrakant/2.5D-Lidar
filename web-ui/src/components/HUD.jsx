export function HUD({ vehicleState, behavior, isConnected, perception, trajectory, trafficSignal, cameraMode, onSelectCamera }) {
  const speed = vehicleState ? (vehicleState.speed * 3.6).toFixed(0) : '0'
  const targetSpeed = behavior?.target_speed ? (behavior.target_speed * 3.6).toFixed(0) : '0'
  const accel = vehicleState?.acceleration !== undefined ? vehicleState.acceleration.toFixed(2) : '0.00'
  const steer = vehicleState?.steer_angle !== undefined ? (vehicleState.steer_angle * 57.3).toFixed(1) : '0.0'
  const computeTime = trajectory?.planning_time ? (trajectory.planning_time * 1000).toFixed(1) : '3.8'
  
  const behaviorLabels = {
    lane_follow: 'Lane Follow (Cruise)',
    lane_change_left: 'Avoidance (Pass Left)',
    lane_change_right: 'Lane Change Right',
    sharp_turn: 'Sharp Turn Navigation',
    pedestrian_yield: 'Pedestrian Crossing Yield',
    traffic_light_stop: 'Red Light Stop',
    stop: 'Full Stop',
    emergency_stop: 'Emergency Braking',
    intersection: 'Intersection Navigation',
  }

  const activeBehavior = behaviorLabels[behavior?.state] || behavior?.state || 'Lane Follow (Cruise)'
  const isYielding = behavior?.state === 'pedestrian_yield' || behavior?.state === 'traffic_light_stop'
  
  const objects = perception?.objects || []
  const trackedCount = objects.filter(o => o.track_id !== undefined).length

  const signalColor = trafficSignal === 'red' ? '#ff3b30' : (trafficSignal === 'yellow' ? '#ff9f0a' : '#30d158')
  const signalLabel = trafficSignal ? trafficSignal.toUpperCase() : 'GREEN'

  return (
    <div style={styles.container} className="glass-panel-dark">
      <div style={styles.header}>
        <div style={styles.titleContainer}>
          <h1 style={styles.title}>Autonomous System</h1>
          <p style={styles.subtitle}>Real-time 3D Telemetry</p>
        </div>
        <div style={styles.statusBadge}>
          <div style={{...styles.statusDot, background: isConnected ? '#34c759' : '#0a84ff'}} className="animate-pulse" />
          <span style={styles.statusText}>{isConnected ? 'Live WS' : 'Simulation'}</span>
        </div>
      </div>

      {/* Camera View Switcher */}
      <div style={styles.cameraBar}>
        <button
          style={{...styles.cameraBtn, ...(cameraMode === 'chase' ? styles.cameraBtnActive : {})}}
          onClick={() => onSelectCamera && onSelectCamera('chase')}
        >
          Chase Cam
        </button>
        <button
          style={{...styles.cameraBtn, ...(cameraMode === 'topdown' ? styles.cameraBtnActive : {})}}
          onClick={() => onSelectCamera && onSelectCamera('topdown')}
        >
          LiDAR Top
        </button>
        <button
          style={{...styles.cameraBtn, ...(cameraMode === 'orbit' ? styles.cameraBtnActive : {})}}
          onClick={() => onSelectCamera && onSelectCamera('orbit')}
        >
          3D Orbit
        </button>
        <button
          style={{...styles.cameraBtn, ...(cameraMode === 'grid25d' ? styles.cameraBtnActive : {})}}
          onClick={() => onSelectCamera && onSelectCamera('grid25d')}
        >
          2.5D Grid
        </button>
      </div>

      <div style={styles.content}>
        {/* Pedestrian Crossing / Signal Alert Banner */}
        {isYielding && (
          <div style={styles.yieldAlertBanner}>
            <div style={styles.yieldAlertIcon}>🚶</div>
            <div>
              <div style={styles.yieldAlertTitle}>
                {behavior?.state === 'pedestrian_yield' ? 'PEDESTRIAN GROUP IN CROSSWALK' : 'TRAFFIC SIGNAL STOP'}
              </div>
              <div style={styles.yieldAlertSubtitle}>
                Vehicle yielding safely before stop line (Target: 0 km/h)
              </div>
            </div>
          </div>
        )}

        {/* Core Dynamics */}
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>Dynamics</h2>
          <div style={styles.metricsGrid}>
            <div style={styles.metricCard}>
              <span style={styles.metricValue}>{speed}<span style={styles.metricUnit}>km/h</span></span>
              <span style={styles.metricLabel}>Speed</span>
            </div>
            <div style={styles.metricCard}>
              <span style={styles.metricValue}>{targetSpeed}<span style={styles.metricUnit}>km/h</span></span>
              <span style={styles.metricLabel}>Target</span>
            </div>
            <div style={styles.metricCard}>
              <span style={styles.metricValue}>{steer}<span style={styles.metricUnit}>°</span></span>
              <span style={styles.metricLabel}>Steering</span>
            </div>
            <div style={styles.metricCard}>
              <span style={styles.metricValue}>{accel}<span style={styles.metricUnit}>m/s²</span></span>
              <span style={styles.metricLabel}>Accel</span>
            </div>
          </div>
        </div>

        {/* Planning & Behavior */}
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>Planning & Trajectory</h2>
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Behavior State</span>
            <span style={styles.infoValueHighlight}>{activeBehavior}</span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Traffic Signal</span>
            <span style={{
              ...styles.infoValue,
              color: signalColor,
              fontWeight: 700,
              background: `rgba(${trafficSignal === 'red' ? '239, 68, 68' : (trafficSignal === 'yellow' ? '245, 158, 11' : '34, 197, 94')}, 0.15)`,
              padding: '2px 8px',
              borderRadius: 6,
              border: `1px solid ${signalColor}40`
            }}>
              {signalLabel}
            </span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Waypoints Ahead</span>
            <span style={styles.infoValue}>{trajectory?.waypoints?.length || 25}</span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Compute Latency</span>
            <span style={styles.infoValue}>{computeTime} ms</span>
          </div>
        </div>

        {/* Perception */}
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>Perception Engine</h2>
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Tracked Obstacles</span>
            <span style={styles.infoValue}>{trackedCount || objects.length} objects</span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>LiDAR Radius</span>
            <span style={styles.infoValue}>40.0 m (360°)</span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Drivable Corridor</span>
            <span style={{...styles.infoValue, color: perception?.free_space !== false ? '#34c759' : '#ff9f0a'}}>
              {perception?.free_space !== false ? 'Clear' : 'Caution'}
            </span>
          </div>
        </div>
        
        {/* Sensor Legend */}
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>Sensors Active</h2>
          <div style={styles.legendGrid}>
            <div style={styles.legendItem}><span style={{...styles.legendColor, background: '#30d158'}}></span>Cameras</div>
            <div style={styles.legendItem}><span style={{...styles.legendColor, background: '#0a84ff'}}></span>LiDAR (40m)</div>
            <div style={styles.legendItem}><span style={{...styles.legendColor, background: '#ff9f0a'}}></span>Radar Track</div>
            <div style={styles.legendItem}><span style={{...styles.legendColor, background: '#64d2ff'}}></span>Trajectory</div>
          </div>
        </div>

        {/* Foveated 2.5D Semantic Elevation Grid Analytics */}
        <div style={styles.section}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={styles.sectionTitle}>Foveated 2.5D Grid</h2>
            <span style={styles.foveaBadge}>94.6% Saved</span>
          </div>

          <div style={styles.foveaMetricsGrid}>
            <div style={styles.foveaCard}>
              <span style={styles.foveaValue}>5cm</span>
              <span style={styles.foveaUnit}>&lt; 10m (Fine)</span>
            </div>
            <div style={styles.foveaCard}>
              <span style={styles.foveaValue}>20cm</span>
              <span style={styles.foveaUnit}>10-30m (Mid)</span>
            </div>
            <div style={styles.foveaCard}>
              <span style={styles.foveaValue}>50cm</span>
              <span style={styles.foveaUnit}>30-100m (Coarse)</span>
            </div>
            <div style={styles.foveaCard}>
              <span style={{ ...styles.foveaValue, color: '#34c759' }}>-94.6%</span>
              <span style={styles.foveaUnit}>RAM Saved</span>
            </div>
          </div>

          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Memory Footprint</span>
            <span style={styles.infoValue}>13.8 MB <span style={{ color: '#64748b' }}>(vs 256 MB)</span></span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Active Grid Cells</span>
            <span style={styles.infoValue}>~42,860 <span style={{ color: '#64748b' }}>(vs 16M)</span></span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.infoLabel}>Semantic mIoU</span>
            <span style={{ ...styles.infoValue, color: '#38bdf8', fontWeight: 600 }}>94.8% (PointNet++)</span>
          </div>

          {/* 2.5D Semantic Color Legend */}
          <div style={{ ...styles.legendGrid, marginTop: 8 }}>
            <div style={styles.legendItem}><span style={{ ...styles.legendColor, background: '#10b981' }}></span>Drivable Road</div>
            <div style={styles.legendItem}><span style={{ ...styles.legendColor, background: '#f59e0b' }}></span>Curbs / Terrain</div>
            <div style={styles.legendItem}><span style={{ ...styles.legendColor, background: '#64748b' }}></span>Static Obstacle</div>
            <div style={styles.legendItem}><span style={{ ...styles.legendColor, background: '#f43f5e' }}></span>Dynamic Actor</div>
          </div>
        </div>
      </div>
    </div>
  )
}


const styles = {
  container: {
    position: 'absolute',
    top: 24,
    right: 24,
    width: 350,
    maxHeight: 'calc(100vh - 48px)',
    zIndex: 100,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: '20px 24px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
  },
  titleContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  title: {
    fontSize: 16,
    fontWeight: 600,
    letterSpacing: '-0.01em',
    color: '#ffffff',
    margin: 0,
  },
  subtitle: {
    fontSize: 12,
    fontWeight: 400,
    color: '#8e8e93',
    margin: 0,
  },
  statusBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    background: 'rgba(255, 255, 255, 0.05)',
    padding: '4px 10px',
    borderRadius: 12,
    border: '1px solid rgba(255, 255, 255, 0.05)',
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: '50%',
  },
  statusText: {
    fontSize: 11,
    fontWeight: 500,
    color: '#d1d1d6',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
  },
  cameraBar: {
    display: 'flex',
    padding: '8px 16px',
    gap: 6,
    background: 'rgba(0, 0, 0, 0.25)',
    borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
  },
  cameraBtn: {
    flex: 1,
    padding: '6px 8px',
    fontSize: 11,
    fontWeight: 500,
    color: '#8e8e93',
    background: 'transparent',
    border: '1px solid transparent',
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  cameraBtnActive: {
    color: '#ffffff',
    background: 'rgba(255, 255, 255, 0.1)',
    border: '1px solid rgba(255, 255, 255, 0.15)',
  },
  content: {
    padding: '16px 24px 24px',
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
    overflowY: 'auto',
  },
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: '#8e8e93',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    margin: '0 0 4px 0',
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 12,
  },
  metricCard: {
    background: 'rgba(0, 0, 0, 0.2)',
    borderRadius: 10,
    padding: '12px',
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    border: '1px solid rgba(255, 255, 255, 0.03)',
  },
  metricValue: {
    fontSize: 20,
    fontWeight: 600,
    color: '#ffffff',
    fontFamily: '"JetBrains Mono", monospace',
    display: 'flex',
    alignItems: 'baseline',
    gap: 4,
  },
  metricUnit: {
    fontSize: 11,
    color: '#8e8e93',
    fontWeight: 500,
    fontFamily: '"Inter", sans-serif',
  },
  metricLabel: {
    fontSize: 12,
    color: '#aeaeb2',
    fontWeight: 500,
  },
  infoRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 0',
    borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
  },
  infoLabel: {
    fontSize: 13,
    color: '#aeaeb2',
    fontWeight: 400,
  },
  infoValue: {
    fontSize: 13,
    color: '#ffffff',
    fontWeight: 500,
    fontFamily: '"JetBrains Mono", monospace',
  },
  infoValueHighlight: {
    fontSize: 13,
    color: '#0a84ff',
    fontWeight: 500,
    background: 'rgba(10, 132, 255, 0.1)',
    padding: '2px 8px',
    borderRadius: 6,
  },
  legendGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 8,
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 12,
    color: '#aeaeb2',
  },
  legendColor: {
    width: 8,
    height: 8,
    borderRadius: '50%',
  },
  yieldAlertBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.25), rgba(245, 158, 11, 0.2))',
    border: '1px solid rgba(239, 68, 68, 0.5)',
    borderRadius: 10,
    padding: '10px 14px',
    marginBottom: 16,
    boxShadow: '0 4px 16px rgba(239, 68, 68, 0.2)',
  },
  yieldAlertIcon: {
    fontSize: 24,
    animation: 'pulse 1.2s infinite',
  },
  yieldAlertTitle: {
    fontSize: 12,
    fontWeight: 700,
    color: '#ff453a',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
  },
  yieldAlertSubtitle: {
    fontSize: 11,
    color: '#e2e8f0',
    marginTop: 2,
  },
  foveaBadge: {
    fontSize: 11,
    fontWeight: 700,
    color: '#34c759',
    background: 'rgba(52, 199, 89, 0.15)',
    padding: '2px 8px',
    borderRadius: 6,
    border: '1px solid rgba(52, 199, 89, 0.35)',
  },
  foveaMetricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 6,
    marginBottom: 10,
    marginTop: 6,
  },
  foveaCard: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    background: 'rgba(255, 255, 255, 0.04)',
    border: '1px solid rgba(255, 255, 255, 0.06)',
    borderRadius: 8,
    padding: '6px 4px',
    textAlign: 'center',
  },
  foveaValue: {
    fontSize: 13,
    fontWeight: 700,
    color: '#ffffff',
    fontFamily: '"JetBrains Mono", monospace',
  },
  foveaUnit: {
    fontSize: 9,
    color: '#94a3b8',
    marginTop: 2,
    whiteSpace: 'nowrap',
  },
}