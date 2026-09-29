"""World management with realistic dynamic highway traffic, crossing pedestrians, and responsive traffic signals."""
import numpy as np
from typing import List, Optional, Tuple
from ..types import VehicleState, DetectedObject, BoundingBox3D
from ..utils.config import config


class WorldManager:
    """Manages the simulation world including dynamic traffic, crossing pedestrians, and traffic signals."""

    def __init__(self):
        self.vehicles: List[DetectedObject] = []
        self.pedestrians: List[DetectedObject] = []
        self.static_objects: List[DetectedObject] = []
        self.dt = config.get('simulation.dt', 0.033)
        self.time = 0.0
        self.traffic_signal = "green"
        self.active_signal_station = 55.0
        self.red_light_timer = 0.0

        # Synchronized with 3D WebGL Environment crosswalk and signal stations (BASE_STATIONS = [55, 250, 450, 950])
        self.CROSSING_SCHEDULE = [
            {"base_s": 55.0,   "id": 90,  "name": "Crosswalk #1 (Station 55m)"},
            {"base_s": 250.0,  "id": 120, "name": "Crosswalk #2 (Station 250m)"},
            {"base_s": 450.0,  "id": 150, "name": "Crosswalk #3 (Station 450m)"},
            {"base_s": 950.0,  "id": 180, "name": "Crosswalk #4 (Station 950m)"},
            {"base_s": 1255.0, "id": 210, "name": "Crosswalk #5 (Loop 2 - 1255m)"},
            {"base_s": 1450.0, "id": 240, "name": "Crosswalk #6 (Loop 2 - 1450m)"},
        ]
        self.BYSTANDER_SCHEDULE = [
            {"base_s": 150.0, "y": -8.2, "jacket": "#10b981", "id": 81, "name": "Bystander #1"},
            {"base_s": 350.0, "y":  8.2, "jacket": "#8b5cf6", "id": 82, "name": "Bystander #2"},
            {"base_s": 650.0, "y": -8.2, "jacket": "#06b6d4", "id": 83, "name": "Bystander #3"},
            {"base_s": 850.0, "y":  8.2, "jacket": "#f97316", "id": 84, "name": "Bystander #4"},
        ]

        self.pedestrian_groups = {}
        self._init_pedestrians()
        self._spawn_traffic()

    def _init_pedestrians(self):
        """Initialize active crossing pedestrians at zebra crosswalks and sidewalk bystanders."""
        self.pedestrians = []
        self.pedestrian_groups = {}

        # 1. Crossing pedestrian groups at each scheduled zebra crosswalk
        for cross in self.CROSSING_SCHEDULE:
            s = cross["base_s"]
            base_id = cross["id"]
            peds = [
                {
                    "id": base_id + 1, "s": s - 1.0, "init_y": -7.5, "dir": 1.0, "speed": 1.35,
                    "target_y": 7.5, "jacket": "#ef4444", "class_name": "pedestrian", "has_crossed": False
                },
                {
                    "id": base_id + 2, "s": s + 0.8, "init_y": -8.2, "dir": 1.0, "speed": 1.20,
                    "target_y": 7.5, "jacket": "#0284c7", "class_name": "pedestrian", "has_crossed": False
                },
                {
                    "id": base_id + 3, "s": s + 1.2, "init_y": 7.5, "dir": -1.0, "speed": 1.40,
                    "target_y": -7.5, "jacket": "#f59e0b", "class_name": "pedestrian", "has_crossed": False
                },
                {
                    "id": base_id + 4, "s": s - 0.4, "init_y": 8.2, "dir": -1.0, "speed": 1.25,
                    "target_y": -7.5, "jacket": "#10b981", "class_name": "pedestrian", "has_crossed": False
                },
            ]
            self.pedestrian_groups[s] = peds

            for p in peds:
                obj = DetectedObject(
                    id=p["id"],
                    bbox_3d=BoundingBox3D(
                        x=p["s"], y=p["init_y"], z=0.0,
                        length=0.8, width=0.8, height=1.8,
                        yaw=0.0 if p["dir"] > 0 else float(np.pi),
                        confidence=0.98, class_id=5, class_name="pedestrian",
                        velocity=(0.0, float(p["dir"] * p["speed"]), 0.0)
                    ),
                    track_id=p["id"]
                )
                obj.bbox_3d.jacketColor = p["jacket"]
                obj.bbox_3d.isCrossing = False
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
        """Spawn rich, realistic multi-lane highway traffic across all 4 highway lanes."""
        self.vehicles = []

        # Lanes:
        # Lane -2: Far-left express passing (y = -5.25)
        # Lane -1: Left passing lane (y = -1.75)
        # Lane  0: Cruising lane (y = 1.75)
        # Lane  1: Right outer lane (y = 5.25)
        traffic_configs = [
            # Lane 0 (Cruising lane, y = 1.75): Slow lead truck at 95m for overtaking, rest spaced >150m apart
            {"id": 1,  "s": 95.0,   "y":  1.75, "speed": 6.5,  "class": "truck", "length": 6.5, "width": 2.2, "height": 2.6},
            {"id": 2,  "s": 260.0,  "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 3,  "s": 520.0,  "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 4,  "s": 820.0,  "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.6, "width": 2.0, "height": 1.6},
            {"id": 5,  "s": 1150.0, "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 6,  "s": 1500.0, "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},

            # Lane -1 (Left passing lane, y = -1.75): Clear near ego so overtaking lane is open
            {"id": 7,  "s": 180.0,  "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 8,  "s": 420.0,  "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 9,  "s": 690.0,  "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.7, "width": 2.0, "height": 1.5},
            {"id": 10, "s": 980.0,  "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 11, "s": 1290.0, "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 12, "s": 1620.0, "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},

            # Lane -2 (Far-left express lane, y = -5.25)
            {"id": 13, "s": 130.0,  "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.6, "width": 2.0, "height": 1.5},
            {"id": 14, "s": 360.0,  "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 15, "s": 610.0,  "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 16, "s": 890.0,  "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.6, "width": 2.0, "height": 1.5},
            {"id": 17, "s": 1200.0, "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 18, "s": 1550.0, "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},

            # Lane 1 (Outer right lane, y = 5.25)
            {"id": 19, "s": 140.0,  "y":  5.25, "speed": 11.0, "class": "truck", "length": 6.8, "width": 2.2, "height": 2.7},
            {"id": 20, "s": 330.0,  "y":  5.25, "speed": 11.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 21, "s": 550.0,  "y":  5.25, "speed": 11.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 22, "s": 800.0,  "y":  5.25, "speed": 11.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 23, "s": 1100.0, "y":  5.25, "speed": 11.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 24, "s": 1450.0, "y":  5.25, "speed": 11.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
        ]

        for cfg in traffic_configs:
            obj = DetectedObject(
                id=cfg["id"],
                bbox_3d=BoundingBox3D(
                    x=cfg["s"], y=cfg["y"], z=0.0,
                    length=cfg["length"], width=cfg["width"], height=cfg["height"],
                    yaw=0.0, confidence=0.96, class_id=0 if cfg["class"] != "truck" else 1,
                    class_name=cfg["class"],
                    velocity=(cfg["speed"], 0.0, 0.0)
                ),
                track_id=cfg["id"]
            )
            obj.base_speed = cfg["speed"]
            self.vehicles.append(obj)

    def step(self, ego_state: VehicleState):
        """Step world simulation forward in time with active pedestrian crossing and signal management."""
        self.dt = 0.033
        self.time += self.dt
        lane_centers = [-5.25, -1.75, 1.75, 5.25]

        # 1. Determine active upcoming crossing station
        min_ahead_dist = 999999.0
        active_station_s = 55.0

        for cross in self.CROSSING_SCHEDULE:
            dist_to_cross = cross["base_s"] - ego_state.x
            if -12.0 < dist_to_cross < min_ahead_dist:
                min_ahead_dist = dist_to_cross
                active_station_s = cross["base_s"]

        self.active_signal_station = active_station_s
        rel_dist = active_station_s - ego_state.x

        # 2. Manage signal phase and pedestrian crossing at active station
        # Approach:
        #   rel_dist > 52m: GREEN, pedestrians waiting on sidewalks
        #   36m < rel_dist <= 52m: YELLOW, ego smoothly slows down, pedestrians prepare
        #   -6m <= rel_dist <= 36m: RED (while crossing is active), pedestrians walk across road
        #   after pedestrians clear or ego passes: GREEN
        station_peds = [p for p in self.pedestrians if abs(p.bbox_3d.x - active_station_s) < 4.0 and p.id not in [81, 82, 83, 84]]

        if rel_dist > 52.0:
            self.traffic_signal = "green"
            self.red_light_timer = 0.0
            for ped_obj in station_peds:
                ped_obj.bbox_3d.isCrossing = False
        elif 36.0 < rel_dist <= 52.0:
            self.traffic_signal = "yellow"
            self.red_light_timer = 0.0
            for ped_obj in station_peds:
                ped_obj.bbox_3d.isCrossing = False
        elif -6.0 <= rel_dist <= 36.0:
            self.red_light_timer += self.dt
            # Active crossing phase: pedestrians cross from one sidewalk to the other
            if self.red_light_timer < 6.8:
                self.traffic_signal = "red"
                for ped_obj in station_peds:
                    if ped_obj.bbox_3d and ped_obj.bbox_3d.velocity:
                        vy = ped_obj.bbox_3d.velocity[1]
                        ped_obj.bbox_3d.y += vy * self.dt
                    ped_obj.bbox_3d.isCrossing = abs(ped_obj.bbox_3d.y) < 7.0
            else:
                # Pedestrians have finished crossing to the other side: stand safely on sidewalk, light turns green
                self.traffic_signal = "green"
                for ped_obj in station_peds:
                    ped_obj.bbox_3d.isCrossing = False
                    if ped_obj.bbox_3d and ped_obj.bbox_3d.velocity:
                        if ped_obj.bbox_3d.velocity[1] > 0:
                            ped_obj.bbox_3d.y = 7.8
                        else:
                            ped_obj.bbox_3d.y = -7.8
        else:
            self.traffic_signal = "green"
            self.red_light_timer = 0.0
            for ped_obj in station_peds:
                ped_obj.bbox_3d.isCrossing = False

        # Bystanders stay stationary on sidewalk
        for ped_obj in self.pedestrians:
            if ped_obj.id in [81, 82, 83, 84]:
                ped_obj.bbox_3d.isCrossing = False

        # 3. Step vehicle traffic along highway with collision-free car-following physics
        for obj in self.vehicles:
            if not obj.bbox_3d or not obj.bbox_3d.velocity:
                continue

            base_speed = getattr(obj, 'base_speed', obj.bbox_3d.velocity[0])
            curr_vx = obj.bbox_3d.velocity[0]
            obj_half_l = obj.bbox_3d.length / 2.0

            # Find closest lead vehicle in the exact same lane corridor
            min_lead_gap = float('inf')
            lead_speed = base_speed

            for other in self.vehicles:
                if other.id != obj.id and other.bbox_3d:
                    if abs(other.bbox_3d.y - obj.bbox_3d.y) < 1.4:
                        other_half_l = other.bbox_3d.length / 2.0
                        gap = (other.bbox_3d.x - other_half_l) - (obj.bbox_3d.x + obj_half_l)
                        if 0.0 < gap < min_lead_gap:
                            min_lead_gap = gap
                            if other.bbox_3d.velocity:
                                lead_speed = other.bbox_3d.velocity[0]

            # Check if ego car is ahead in same lane
            if abs(ego_state.y - obj.bbox_3d.y) < 1.4:
                ego_gap = (ego_state.x - 2.4) - (obj.bbox_3d.x + obj_half_l)
                if 0.0 < ego_gap < min_lead_gap:
                    min_lead_gap = ego_gap
                    lead_speed = ego_state.speed

            # Traffic signal obedience for other vehicles at active crosswalk stop line
            dist_to_signal = active_station_s - (obj.bbox_3d.x + obj_half_l)
            if self.traffic_signal in ['red', 'yellow'] and 0.0 < dist_to_signal < 40.0:
                stop_line_gap = dist_to_signal - 7.5
                if 0.0 < stop_line_gap < min_lead_gap:
                    min_lead_gap = stop_line_gap
                    lead_speed = 0.0

            # Safe car-following deceleration profile:
            if min_lead_gap < 7.0:
                target_v = 0.0  # Standstill stop buffer: never drive into vehicle ahead
            elif min_lead_gap < 18.0:
                headway_factor = max(0.0, (min_lead_gap - 7.0) / 11.0)
                target_v = min(lead_speed * headway_factor, base_speed * 0.5)
            elif min_lead_gap < 38.0:
                target_v = min(base_speed, lead_speed + 0.35 * (min_lead_gap - 18.0))
            else:
                target_v = base_speed

            # Smooth acceleration / braking
            if target_v > curr_vx:
                new_vx = min(target_v, curr_vx + 1.8 * self.dt)
            else:
                new_vx = max(target_v, curr_vx - 3.5 * self.dt)

            obj.bbox_3d.velocity = (max(0.0, new_vx), 0.0, 0.0)
            obj.bbox_3d.x += new_vx * self.dt

            # Stable, invisible recycling:
            # ONLY recycle when vehicle falls far behind ego (>120m behind) or reaches the end of track (>2500m)
            # NEVER recycle while ahead of ego!
            if obj.bbox_3d.x < ego_state.x - 120.0 or obj.bbox_3d.x > 2500.0:
                # Place 320m to 460m ahead of ego (far into the horizon fog where user cannot see it)
                placed = False
                for _ in range(8):
                    cand_lane = float(np.random.choice(lane_centers))
                    cand_x = ego_state.x + float(np.random.uniform(320.0, 460.0))
                    # Ensure clearance from all vehicles in candidate lane
                    clear = all(
                        abs(other.bbox_3d.x - cand_x) > 50.0
                        for other in self.vehicles
                        if other.id != obj.id and other.bbox_3d and abs(other.bbox_3d.y - cand_lane) < 1.0
                    )
                    if clear:
                        obj.bbox_3d.x = cand_x
                        obj.bbox_3d.y = cand_lane
                        base_speeds = {-5.25: 18.0, -1.75: 16.0, 1.75: 13.5, 5.25: 11.0}
                        obj.base_speed = base_speeds.get(cand_lane, 14.0)
                        obj.bbox_3d.velocity = (obj.base_speed, 0.0, 0.0)
                        placed = True
                        break
                if not placed:
                    obj.bbox_3d.x = ego_state.x + 380.0
                    obj.bbox_3d.velocity = (base_speed, 0.0, 0.0)

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