"""Core data types for the autonomous vehicle simulation."""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum
import numpy as np


class VehicleState:
    """Current vehicle state."""
    def __init__(self):
        self.x: float = 0.0
        self.y: float = 0.0
        self.yaw: float = 0.0
        self.speed: float = 0.0
        self.acceleration: float = 0.0
        self.steer_angle: float = 0.0
        self.timestamp: float = 0.0


@dataclass
class BoundingBox2D:
    """2D bounding box in image coordinates."""
    x: float
    y: float
    width: float
    height: float
    confidence: float
    class_id: int
    class_name: str


@dataclass
class BoundingBox3D:
    """3D bounding box in world coordinates."""
    x: float
    y: float
    z: float
    length: float
    width: float
    height: float
    yaw: float
    confidence: float
    class_id: int
    class_name: str
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class LaneMarking:
    """Lane marking representation."""
    points: np.ndarray  # N x 2 (x, y in world coords)
    color: str  # 'white', 'yellow'
    type: str   # 'solid', 'dashed', 'double'
    confidence: float


@dataclass
class DetectedObject:
    """Unified detected object from sensor fusion."""
    id: int
    bbox_3d: BoundingBox3D
    bbox_2d: Optional[BoundingBox2D] = None
    track_id: Optional[int] = None
    age: int = 0
    hits: int = 0


@dataclass
class PerceptionResult:
    """Output from perception module."""
    objects: List[DetectedObject] = field(default_factory=list)
    lanes: List[LaneMarking] = field(default_factory=list)
    free_space: Optional[np.ndarray] = None  # Occupancy grid
    timestamp: float = 0.0
    sensor_data: dict = field(default_factory=dict)


@dataclass
class Waypoint:
    """Single trajectory waypoint."""
    x: float
    y: float
    yaw: float
    speed: float
    curvature: float = 0.0
    s: float = 0.0  # Path length


@dataclass
class Trajectory:
    """Planned trajectory."""
    waypoints: List[Waypoint] = field(default_factory=list)
    timestamp: float = 0.0
    planning_time: float = 0.0
    valid: bool = True


class BehaviorState(Enum):
    """High-level behavior states."""
    LANE_FOLLOW = "lane_follow"
    LANE_CHANGE_LEFT = "lane_change_left"
    LANE_CHANGE_RIGHT = "lane_change_right"
    STOP = "stop"
    EMERGENCY_STOP = "emergency_stop"
    INTERSECTION = "intersection"
    PARKING = "parking"


@dataclass
class BehaviorDecision:
    """Behavior planner output."""
    state: BehaviorState
    target_lane: Optional[int] = None
    target_speed: float = 0.0
    stop_distance: float = 0.0
    reason: str = ""


@dataclass
class ControlCommand:
    """Vehicle control commands."""
    steer: float = 0.0      # [-1, 1]
    throttle: float = 0.0   # [0, 1]
    brake: float = 0.0      # [0, 1]
    hand_brake: bool = False
    reverse: bool = False
    timestamp: float = 0.0


@dataclass
class SensorData:
    """Raw sensor data container."""
    camera_front: Optional[np.ndarray] = None
    camera_rear: Optional[np.ndarray] = None
    camera_left: Optional[np.ndarray] = None
    camera_right: Optional[np.ndarray] = None
    lidar: Optional[np.ndarray] = None  # N x 4 (x, y, z, intensity)
    radar: Optional[List[dict]] = None
    gnss: Optional[Tuple[float, float, float]] = None
    imu: Optional[dict] = None
    timestamp: float = 0.0


@dataclass
class WorldState:
    """Complete world state for visualization."""
    vehicle: VehicleState
    perception: PerceptionResult
    trajectory: Trajectory
    behavior: BehaviorDecision
    control: ControlCommand
    timestamp: float