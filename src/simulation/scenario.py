"""Scenario management."""
import json
from pathlib import Path
from typing import Dict, Any, List
from ..types import VehicleState
from ..utils.config import config


class ScenarioManager:
    """Manages simulation scenarios."""

    def __init__(self):
        self.scenarios: Dict[str, Dict[str, Any]] = {}
        self.current_scenario = None
        self._load_scenarios()

    def _load_scenarios(self):
        """Load scenario definitions."""
        self.scenarios = {
            "highway": {
                "name": "Highway Driving",
                "description": "Straight highway with traffic",
                "ego_start": {"x": 0, "y": 1.75, "yaw": 0, "speed": 20},
                "goal": {"x": 1500, "y": 1.75},
                "traffic_density": 20,
                "duration": 180,
            },
            "urban": {
                "name": "Urban Driving",
                "description": "City streets with intersections",
                "ego_start": {"x": 0, "y": 1.75, "yaw": 0, "speed": 10},
                "goal": {"x": 1000, "y": 1.75},
                "traffic_density": 25,
                "duration": 180,
            },
            "lane_change": {
                "name": "Lane Change Test",
                "description": "Test lane change behavior with slower vehicle ahead",
                "ego_start": {"x": 0, "y": 1.75, "yaw": 0, "speed": 18.0},
                "goal": {"x": 1500, "y": 1.75},
                "traffic_density": 6,
                "duration": 180,
                "special_objects": [
                    {"x": 65.0, "y": 1.75, "speed": 6.5, "class": "truck"}
                ]
            },
            "emergency_brake": {
                "name": "Emergency Brake Test",
                "description": "Test emergency braking with stationary obstacle",
                "ego_start": {"x": 0, "y": 1.75, "yaw": 0, "speed": 20.0},
                "goal": {"x": 1500, "y": 1.75},
                "traffic_density": 0,
                "duration": 180,
                "special_objects": [
                    {"x": 55.0, "y": 1.75, "speed": 0.0, "class": "car"}
                ]
            },
        }

    def get_scenario(self, name: str) -> Dict[str, Any]:
        """Get scenario by name."""
        return self.scenarios.get(name, self.scenarios["lane_change"])

    def list_scenarios(self) -> List[str]:
        """List available scenarios."""
        return list(self.scenarios.keys())

    def apply_scenario(self, name: str, world_manager) -> VehicleState:
        """Apply scenario to world."""
        scenario = self.get_scenario(name)
        self.current_scenario = scenario

        if world_manager:
            world_manager._spawn_traffic()
            world_manager._init_pedestrians()
            if "special_objects" in scenario:
                from ..types import DetectedObject, BoundingBox3D
                for i, spec in enumerate(scenario["special_objects"]):
                    is_truck = spec.get("class") == "truck"
                    spec_obj = DetectedObject(
                        id=1000 + i,
                        bbox_3d=BoundingBox3D(
                            x=float(spec["x"]), y=float(spec["y"]), z=0.0,
                            length=6.5 if is_truck else 4.5,
                            width=2.2 if is_truck else 2.0,
                            height=2.6 if is_truck else 1.5,
                            yaw=0.0, confidence=1.0, class_id=0,
                            class_name=spec.get("class", "truck" if is_truck else "car"),
                            velocity=(float(spec.get("speed", 6.5)), 0.0, 0.0)
                        ),
                        track_id=1000 + i
                    )
                    # Avoid vehicle collision with special obstacle at initial spawn
                    world_manager.vehicles = [spec_obj] + [
                        v for v in world_manager.vehicles
                        if abs(v.bbox_3d.x - spec_obj.bbox_3d.x) > 20.0 or abs(v.bbox_3d.y - spec_obj.bbox_3d.y) > 2.0
                    ]

        ego_start = scenario["ego_start"]
        state = VehicleState()
        state.x = float(ego_start["x"])
        state.y = float(ego_start["y"])
        state.yaw = float(ego_start["yaw"])
        state.speed = float(ego_start["speed"])
        state.timestamp = 0.0

        return state