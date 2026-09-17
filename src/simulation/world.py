"""World management for pygame simulation."""
import numpy as np
from typing import List, Optional
from ..types import VehicleState, DetectedObject, BoundingBox3D
from ..utils.config import config


class WorldManager:
    """Manages the simulation world (pygame mode)."""

    def __init__(self):
        self.vehicles: List[DetectedObject] = []
        self.static_objects: List[DetectedObject] = []
        self.dt = config.get('simulation.dt', 0.033)
        self.time = 0.0

        self._spawn_traffic()

    def _spawn_traffic(self):
        """Spawn traffic vehicles in lane centers."""
        np.random.seed(config.get('simulation.seed', 42))
        lane_centers = [-5.25, -1.75, 1.75, 5.25]

        for i in range(config.get('world.traffic_density', 30)):
            lane_y = float(np.random.choice(lane_centers))
            s = np.random.uniform(25, 250)
            speed = np.random.uniform(6, 14)

            obj = DetectedObject(
                id=i,
                bbox_3d=BoundingBox3D(
                    x=s, y=lane_y, z=0,
                    length=4.5, width=2.0, height=1.5,
                    yaw=0.0, confidence=1.0, class_id=0, class_name="car",
                    velocity=(speed, 0, 0)
                ),
                track_id=i
            )
            self.vehicles.append(obj)

    def step(self, ego_state: VehicleState):
        """Step world simulation."""
        self.time += self.dt
        lane_centers = [-5.25, -1.75, 1.75, 5.25]

        for obj in self.vehicles:
            if obj.bbox_3d and obj.bbox_3d.velocity:
                vx, vy, vz = obj.bbox_3d.velocity
                obj.bbox_3d.x += vx * self.dt
                obj.bbox_3d.y += vy * self.dt

                # Recycle vehicles relative to ego position so road never becomes empty
                if obj.bbox_3d.x < ego_state.x - 60:
                    obj.bbox_3d.x = ego_state.x + 120 + float(np.random.uniform(10, 80))
                    obj.bbox_3d.y = float(np.random.choice(lane_centers))
                elif obj.bbox_3d.x > ego_state.x + 300:
                    obj.bbox_3d.x = ego_state.x + 50 + float(np.random.uniform(10, 60))
                    obj.bbox_3d.y = float(np.random.choice(lane_centers))

    def get_all_objects(self) -> List[DetectedObject]:
        """Get all objects in world."""
        return self.vehicles + self.static_objects

    def get_ego_vehicle_state(self) -> VehicleState:
        """Get initial ego vehicle state centered in cruising lane."""
        state = VehicleState()
        state.x = 0.0
        state.y = 1.75
        state.yaw = 0.0
        state.speed = 0.0
        state.timestamp = self.time
        return state