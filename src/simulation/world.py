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
        self.signal_cleared_timer = 0.0

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
        # Start safely on sidewalk (y = +/-8.5m) and cross completely across roadway to opposite sidewalk
        for cross in self.CROSSING_SCHEDULE:
            s = cross["base_s"]
            base_id = cross["id"]
            peds = [
                {
                    "id": base_id + 1, "s": s - 1.0, "init_y": -8.4, "target_y": 8.4, "dir": 1.0, "speed": 1.45,
                    "jacket": "#ef4444", "class_name": "pedestrian"
                },
                {
                    "id": base_id + 2, "s": s + 0.8, "init_y": -9.0, "target_y": 8.4, "dir": 1.0, "speed": 1.30,
                    "jacket": "#0284c7", "class_name": "pedestrian"
                },
                {
                    "id": base_id + 3, "s": s + 1.2, "init_y": 8.4, "target_y": -8.4, "dir": -1.0, "speed": 1.50,
                    "jacket": "#f59e0b", "class_name": "pedestrian"
                },
                {
                    "id": base_id + 4, "s": s - 0.4, "init_y": 9.0, "target_y": -8.4, "dir": -1.0, "speed": 1.35,
                    "jacket": "#10b981", "class_name": "pedestrian"
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
                obj.init_y = p["init_y"]
                obj.target_y = p["target_y"]
                obj.walk_dir = p["dir"]
                obj.walk_speed = p["speed"]
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
        # Lane -2: Far-left express passing (y = -5.25, speed ~18 m/s = 65 km/h)
        # Lane -1: Left passing lane (y = -1.75, speed ~16 m/s = 58 km/h)
        # Lane  0: Cruising lane (y = 1.75, speed ~13.5 m/s = 49 km/h)
        # Lane  1: Right outer lane (y = 5.25, speed ~11 m/s = 40 km/h)
        traffic_configs = [
            # Lane 0 (Cruising lane, y = 1.75): Slow lead truck at 70m for overtaking, followed by steady traffic
            {"id": 1,  "s": 70.0,   "y":  1.75, "speed": 6.5,  "class": "truck", "length": 6.5, "width": 2.2, "height": 2.6},
            {"id": 2,  "s": 150.0,  "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 3,  "s": 235.0,  "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 4,  "s": 325.0,  "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.6, "width": 2.0, "height": 1.6},
            {"id": 5,  "s": 420.0,  "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 6,  "s": 520.0,  "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 7,  "s": 625.0,  "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 8,  "s": 735.0,  "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.6, "width": 2.0, "height": 1.6},
            {"id": 9,  "s": 850.0,  "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 10, "s": 970.0,  "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 11, "s": 1090.0, "y":  1.75, "speed": 13.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},

            # Lane -1 (Left passing lane, y = -1.75): Clear between 0m-100m for ego overtaking corridor
            {"id": 12, "s": 120.0,  "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 13, "s": 200.0,  "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 14, "s": 285.0,  "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.7, "width": 2.0, "height": 1.5},
            {"id": 15, "s": 375.0,  "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 16, "s": 470.0,  "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 17, "s": 570.0,  "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 18, "s": 675.0,  "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.7, "width": 2.0, "height": 1.5},
            {"id": 19, "s": 785.0,  "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 20, "s": 900.0,  "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 21, "s": 1020.0, "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 22, "s": 1140.0, "y": -1.75, "speed": 16.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},

            # Lane -2 (Far-left express lane, y = -5.25): High speed flow
            {"id": 23, "s": 25.0,   "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.6, "width": 2.0, "height": 1.5},
            {"id": 24, "s": 95.0,   "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 25, "s": 175.0,  "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 26, "s": 260.0,  "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.6, "width": 2.0, "height": 1.5},
            {"id": 27, "s": 350.0,  "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 28, "s": 445.0,  "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 29, "s": 545.0,  "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.6, "width": 2.0, "height": 1.5},
            {"id": 30, "s": 650.0,  "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 31, "s": 760.0,  "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 32, "s": 875.0,  "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.6, "width": 2.0, "height": 1.5},
            {"id": 33, "s": 995.0,  "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 34, "s": 1120.0, "y": -5.25, "speed": 18.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},

            # Lane 1 (Outer right lane, y = 5.25): Trucks & slower traffic
            {"id": 35, "s": 20.0,   "y":  5.25, "speed": 11.0, "class": "truck", "length": 6.8, "width": 2.2, "height": 2.7},
            {"id": 36, "s": 90.0,   "y":  5.25, "speed": 11.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 37, "s": 165.0,  "y":  5.25, "speed": 11.0, "class": "truck", "length": 6.5, "width": 2.2, "height": 2.6},
            {"id": 38, "s": 245.0,  "y":  5.25, "speed": 11.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 39, "s": 330.0,  "y":  5.25, "speed": 11.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 40, "s": 420.0,  "y":  5.25, "speed": 11.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 41, "s": 515.0,  "y":  5.25, "speed": 11.0, "class": "truck", "length": 6.8, "width": 2.2, "height": 2.7},
            {"id": 42, "s": 615.0,  "y":  5.25, "speed": 11.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 43, "s": 720.0,  "y":  5.25, "speed": 11.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 44, "s": 830.0,  "y":  5.25, "speed": 11.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 45, "s": 945.0,  "y":  5.25, "speed": 11.0, "class": "truck", "length": 6.5, "width": 2.2, "height": 2.6},
            {"id": 46, "s": 1065.0, "y":  5.25, "speed": 11.5, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
            {"id": 47, "s": 1180.0, "y":  5.25, "speed": 11.0, "class": "car",   "length": 4.5, "width": 1.9, "height": 1.5},
        ]

        palette = ["#ef4444", "#06b6d4", "#facc15", "#cbd5e1", "#3b82f6", "#8b5cf6", "#f97316"]
        models = ["Sedan", "SUV", "Hatchback", "Coupe"]

        for cfg in traffic_configs:
            is_truck = cfg["class"] == "truck"
            v_color = cfg.get("color", "#f97316" if is_truck else palette[cfg["id"] % len(palette)])
            v_model = cfg.get("model_name", "Truck" if is_truck else models[cfg["id"] % len(models)])
            obj = DetectedObject(
                id=cfg["id"],
                bbox_3d=BoundingBox3D(
                    x=cfg["s"], y=cfg["y"], z=0.0,
                    length=cfg["length"], width=cfg["width"], height=cfg["height"],
                    yaw=0.0, confidence=0.96, class_id=0 if not is_truck else 1,
                    class_name=cfg["class"],
                    velocity=(cfg["speed"], 0.0, 0.0)
                ),
                track_id=cfg["id"]
            )
            obj.color = v_color
            obj.model_name = v_model
            obj.bbox_3d.color = v_color
            obj.bbox_3d.model_name = v_model
            obj.bbox_3d.track_id = cfg["id"]
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

        if rel_dist > 55.0:
            # Distant approach: Green light, pedestrians waiting safely on sidewalk
            self.traffic_signal = "green"
            self.signal_cleared_timer = 0.0
            for ped_obj in station_peds:
                init_y = getattr(ped_obj, 'init_y', -8.4)
                ped_obj.bbox_3d.y = init_y
                ped_obj.bbox_3d.isCrossing = False
                walk_dir = getattr(ped_obj, 'walk_dir', 1.0)
                walk_speed = getattr(ped_obj, 'walk_speed', 1.4)
                if ped_obj.bbox_3d.velocity:
                    ped_obj.bbox_3d.velocity = (0.0, float(walk_dir * walk_speed), 0.0)
        elif 38.0 < rel_dist <= 55.0:
            # Approaching warning: Yellow light, ego slows down smoothly, pedestrians prepare on sidewalk
            self.traffic_signal = "yellow"
            self.signal_cleared_timer = 0.0
            for ped_obj in station_peds:
                ped_obj.bbox_3d.isCrossing = False
        elif -8.0 <= rel_dist <= 38.0:
            # Active crossing phase: pedestrians walk across zebra crossing step-by-step
            all_cleared = True
            for ped_obj in station_peds:
                target_y = getattr(ped_obj, 'target_y', 8.4)
                walk_dir = getattr(ped_obj, 'walk_dir', 1.0)
                walk_speed = getattr(ped_obj, 'walk_speed', 1.4)

                # Has this pedestrian reached the opposite sidewalk?
                reached = (ped_obj.bbox_3d.y >= target_y) if walk_dir > 0 else (ped_obj.bbox_3d.y <= target_y)

                if not reached:
                    all_cleared = False
                    # Continuous step-by-step natural walking physics without ANY teleporting
                    ped_obj.bbox_3d.y += walk_dir * walk_speed * self.dt
                    ped_obj.bbox_3d.isCrossing = abs(ped_obj.bbox_3d.y) < 7.6
                    ped_obj.bbox_3d.velocity = (0.0, float(walk_dir * walk_speed), 0.0)
                else:
                    # Safely on the destination sidewalk: stop walking and stand safely
                    ped_obj.bbox_3d.y = target_y
                    ped_obj.bbox_3d.isCrossing = False
                    ped_obj.bbox_3d.velocity = (0.0, 0.0, 0.0)

            if not all_cleared:
                self.traffic_signal = "red"
                self.signal_cleared_timer = 0.0
            else:
                # All pedestrians have crossed completely to the other side!
                # Keep RED for 1.4s safety buffer after road is clear, then turn GREEN
                self.signal_cleared_timer += self.dt
                if self.signal_cleared_timer < 1.4:
                    self.traffic_signal = "red"
                else:
                    self.traffic_signal = "green"
        else:
            self.traffic_signal = "green"
            self.signal_cleared_timer = 0.0
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
            if self.traffic_signal in ['red', 'yellow'] and -2.0 < dist_to_signal < 45.0:
                # Stop line is at active_station_s - 7.0m; stop 2.2m safely before the line
                stop_line_gap = max(0.0, dist_to_signal - 9.2)
                if stop_line_gap < min_lead_gap:
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

            if target_v == 0.0 and new_vx < 0.25:
                new_vx = 0.0

            obj.bbox_3d.velocity = (max(0.0, new_vx), 0.0, 0.0)
            obj.bbox_3d.x += new_vx * self.dt

            # Continuous, collision-free rolling-horizon recycling:
            # ONLY recycle when vehicle falls far behind ego (> 75m behind ego, completely past rear camera view)
            # OR if vehicle is far beyond the track end (> 1250m) and ego is not near the end.
            # NEVER recycle vehicles that are actively driving ahead of ego!
            needs_recycle = (obj.bbox_3d.x < ego_state.x - 75.0) or (obj.bbox_3d.x > 1250.0 and ego_state.x < 1000.0)
            if needs_recycle:
                placed = False
                for _ in range(12):
                    cand_lane = float(np.random.choice(lane_centers))
                    # Respawn far ahead on the horizon (150m to 195m ahead, deep in horizon fog)
                    cand_x = ego_state.x + float(np.random.uniform(150.0, 195.0))

                    # Avoid placing directly on an active red-light crosswalk zone
                    if self.traffic_signal in ['red', 'yellow'] and abs(cand_x - active_station_s) < 20.0:
                        continue

                    # Ensure clearance from all vehicles in candidate lane (minimum 35m safe headway)
                    clear = all(
                        abs(other.bbox_3d.x - cand_x) > 35.0
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