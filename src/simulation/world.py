"""World management with realistic traffic, crossing pedestrians, and signal state."""
import numpy as np
from typing import List, Optional, Tuple
from ..types import VehicleState, DetectedObject, BoundingBox3D
from ..utils.config import config


class WorldManager:
    """Manages the simulation world including dynamic traffic and pedestrians."""

    def __init__(self):
        self.vehicles: List[DetectedObject] = []
        self.pedestrians: List[DetectedObject] = []
        self.static_objects: List[DetectedObject] = []
        self.dt = config.get('simulation.dt', 0.033)
        self.time = 0.0
        self.traffic_signal = "green"
        self.active_signal_station = 55.0

        self.CROSSING_SCHEDULE = [
            {"base_s": 55.0, "id": 90, "name": "Crosswalk #1"},
            {"base_s": 490.0, "id": 100, "name": "Crosswalk #2"},
            {"base_s": 1000.0, "id": 110, "name": "Crosswalk #3"},
        ]
        self.BYSTANDER_SCHEDULE = [
            {"base_s": 240.0, "y": -8.5, "jacket": "#10b981", "id": 81, "name": "Bystander #1"},
            {"base_s": 740.0, "y": 8.5, "jacket": "#8b5cf6", "id": 82, "name": "Bystander #2"},
        ]

        self.pedestrian_groups = {}
        self._init_pedestrians()
        self._spawn_traffic()

    def _init_pedestrians(self):
        """Initialize persistent pedestrians and sidewalk bystanders."""
        self.pedestrians = []
        self.pedestrian_groups = {}

        # 1. Crossing pedestrian groups at zebra crosswalks
        for cross in self.CROSSING_SCHEDULE:
            s = cross["base_s"]
            base_id = cross["id"]
            peds = [
                {
                    "id": base_id + 1, "s": s - 1.1, "y": -8.8, "dir": 1.0, "speed": 1.4,
                    "target_y": 8.8, "jacket": "#ef4444", "class_name": "pedestrian",
                },
                {
                    "id": base_id + 2, "s": s + 0.7, "y": -9.6, "dir": 1.0, "speed": 1.25,
                    "target_y": 8.8, "jacket": "#0284c7", "class_name": "pedestrian",
                },
                {
                    "id": base_id + 3, "s": s + 1.4, "y": 8.8, "dir": -1.0, "speed": 1.5,
                    "target_y": -8.8, "jacket": "#f59e0b", "class_name": "pedestrian",
                },
                {
                    "id": base_id + 4, "s": s - 0.5, "y": 9.6, "dir": -1.0, "speed": 1.3,
                    "target_y": -8.8, "jacket": "#10b981", "class_name": "pedestrian",
                },
            ]
            self.pedestrian_groups[s] = peds

            for p in peds:
                obj = DetectedObject(
                    id=p["id"],
                    bbox_3d=BoundingBox3D(
                        x=p["s"], y=p["y"], z=0.0,
                        length=0.8, width=0.8, height=1.8,
                        yaw=0.0 if p["dir"] > 0 else float(np.pi),
                        confidence=0.98, class_id=5, class_name="pedestrian",
                        velocity=(0.0, float(p["dir"] * p["speed"]), 0.0)
                    ),
                    track_id=p["id"]
                )
                obj.bbox_3d.jacketColor = p["jacket"]
                obj.bbox_3d.isCrossing = abs(p["y"]) < 7.5
                self.pedestrians.append(obj)

        # 2. Bystanders standing safely on sidewalk
        for b in self.BYSTANDER_SCHEDULE:
            b_obj = DetectedObject(
                id=b["id"],
                bbox_3d=BoundingBox3D(
                    x=b["base_s"], y=b["y"], z=0.0,
                    length=0.8, width=0.8, height=1.8,
                    yaw=float(-np.pi / 2 if b["y"] > 0 else np.pi / 2),
                    confidence=0.95, class_id=5, class_name="pedestrian",
                    velocity=(0.0, 0.0, 0.0)
                ),
                track_id=b["id"]
            )
            b_obj.bbox_3d.jacketColor = b["jacket"]
            b_obj.bbox_3d.isCrossing = False
            self.pedestrians.append(b_obj)

    def _spawn_traffic(self):
        """Spawn realistic traffic with clear passing lanes for smooth overtaking."""
        self.vehicles = []

        # Structured traffic setup:
        # Cruising lane is y = 1.75. Passing lane is y = -1.75.
        # Initial lead vehicle is ahead in cruising lane, passing lane is clear!
        traffic_configs = [
            {"id": 1, "s": 95.0,  "y":  1.75, "speed": 6.5,  "class": "truck", "length": 6.5, "width": 2.2, "height": 2.6}, # Slow lead truck to overtake after crosswalk
            {"id": 2, "s": 150.0, "y":  5.25, "speed": 16.0, "class": "car",   "length": 4.5, "width": 2.0, "height": 1.5}, # Right outer lane
            {"id": 3, "s": 220.0, "y": -1.75, "speed": 17.5, "class": "car",   "length": 4.5, "width": 2.0, "height": 1.5}, # Left lane, far ahead
            {"id": 4, "s": 310.0, "y":  1.75, "speed": 14.0, "class": "car",   "length": 4.5, "width": 2.0, "height": 1.5}, # Cruising lane, far ahead
            {"id": 5, "s": 420.0, "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.5, "width": 2.0, "height": 1.5}, # Far-left lane
            {"id": 6, "s": 530.0, "y":  1.75, "speed": 15.0, "class": "car",   "length": 4.5, "width": 2.0, "height": 1.5},
        ]

        for cfg in traffic_configs:
            obj = DetectedObject(
                id=cfg["id"],
                bbox_3d=BoundingBox3D(
                    x=cfg["s"], y=cfg["y"], z=0.0,
                    length=cfg["length"], width=cfg["width"], height=cfg["height"],
                    yaw=0.0, confidence=0.96, class_id=0, class_name=cfg["class"],
                    velocity=(cfg["speed"], 0.0, 0.0)
                ),
                track_id=cfg["id"]
            )
            self.vehicles.append(obj)

    def step(self, ego_state: VehicleState):
        """Step world simulation forward in time."""
        self.time += self.dt
        lane_centers = [-5.25, -1.75, 1.75, 5.25]

        # 1. Step vehicle positions along highway with collision-free spacing
        for obj in self.vehicles:
            if obj.bbox_3d and obj.bbox_3d.velocity:
                vx, vy, vz = obj.bbox_3d.velocity

                # Check if lead vehicle is ahead in the same lane
                lead_veh = None
                min_gap = float('inf')
                for other in self.vehicles:
                    if other.id != obj.id and other.bbox_3d:
                        if abs(other.bbox_3d.y - obj.bbox_3d.y) < 1.4 and other.bbox_3d.x > obj.bbox_3d.x:
                            gap = other.bbox_3d.x - obj.bbox_3d.x
                            if gap < min_gap:
                                min_gap = gap
                                lead_veh = other

                # Check if ego car is ahead in same lane
                if abs(ego_state.y - obj.bbox_3d.y) < 1.4 and ego_state.x > obj.bbox_3d.x:
                    ego_gap = ego_state.x - obj.bbox_3d.x
                    if ego_gap < min_gap:
                        min_gap = ego_gap

                curr_vx = vx
                if min_gap < 14.0:
                    curr_vx = min(vx, max(0.0, min_gap * 0.45))

                obj.bbox_3d.x += curr_vx * self.dt
                obj.bbox_3d.y += vy * self.dt

                # Stable recycling: ONLY recycle when vehicle falls far behind the ego vehicle (>75m behind)
                if obj.bbox_3d.x < ego_state.x - 75.0:
                    obj.bbox_3d.x = ego_state.x + float(np.random.uniform(280.0, 350.0))
                    obj.bbox_3d.y = float(np.random.choice(lane_centers))
                    new_speed = float(np.random.uniform(12.0, 17.0))
                    obj.bbox_3d.velocity = (new_speed, 0.0, 0.0)

        # 2. Determine active crossing station & manage pedestrian crossing
        min_ahead_dist = 999999.0
        active_station_s = 55.0

        for cross in self.CROSSING_SCHEDULE:
            dist_to_cross = cross["base_s"] - ego_state.x
            if -25.0 < dist_to_cross < min_ahead_dist:
                min_ahead_dist = dist_to_cross
                active_station_s = cross["base_s"]

        self.active_signal_station = active_station_s
        rel_dist = active_station_s - ego_state.x

        # Step pedestrians
        for ped_obj in self.pedestrians:
            if not ped_obj.bbox_3d:
                continue
            ped_s = ped_obj.bbox_3d.x
            ped_id = ped_obj.id

            # Sidewalk bystanders remain standing safely on sidewalk
            if ped_id in [81, 82]:
                ped_obj.bbox_3d.isCrossing = False
                continue

            # Active crosswalk pedestrian animation
            if abs(ped_s - active_station_s) < 5.0:
                # Signal phase logic:
                # Approach (> 38m): Green, waiting on sidewalk
                # Warning (28m to 38m): Yellow
                # Stop / Crossing (< 28m): Red, walk across road
                if rel_dist > 38.0:
                    self.traffic_signal = "green"
                    ped_obj.bbox_3d.isCrossing = False
                elif 28.0 < rel_dist <= 38.0:
                    self.traffic_signal = "yellow"
                    ped_obj.bbox_3d.isCrossing = False
                elif -15.0 < rel_dist <= 28.0:
                    # Pedestrians walk across
                    if ped_obj.bbox_3d.velocity:
                        vy = ped_obj.bbox_3d.velocity[1]
                        ped_obj.bbox_3d.y += vy * self.dt
                        # Rebound at sidewalk boundaries so they stay in scene
                        if ped_obj.bbox_3d.y > 8.8 and vy > 0:
                            ped_obj.bbox_3d.velocity = (0.0, -abs(vy), 0.0)
                        elif ped_obj.bbox_3d.y < -8.8 and vy < 0:
                            ped_obj.bbox_3d.velocity = (0.0, abs(vy), 0.0)

                    in_road = abs(ped_obj.bbox_3d.y) < 7.5
                    ped_obj.bbox_3d.isCrossing = in_road
                    if in_road:
                        self.traffic_signal = "red"
                    else:
                        self.traffic_signal = "green"
                else:
                    self.traffic_signal = "green"
                    ped_obj.bbox_3d.isCrossing = False

    def get_all_objects(self) -> List[DetectedObject]:
        """Get all objects in world (vehicles, crossing pedestrians, bystanders)."""
        return self.vehicles + self.pedestrians + self.static_objects

    def get_traffic_signal(self) -> Tuple[str, float]:
        """Get current traffic light status and active station s-coordinate."""
        return self.traffic_signal, self.active_signal_station

    def get_ego_vehicle_state(self) -> VehicleState:
        """Get initial ego vehicle state centered in cruising lane."""
        state = VehicleState()
        state.x = 0.0
        state.y = 1.75
        state.yaw = 0.0
        state.speed = 15.0
        state.timestamp = self.time
        return state