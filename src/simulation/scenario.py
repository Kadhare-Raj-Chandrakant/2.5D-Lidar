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
                "ego_start": {"x": 0, "y": 1.75, "yaw": 0, "speed": 15},
                "goal": {"x": 1500, "y": 1.75},
                "traffic_density": 6,
                "duration": 180,
                "special_objects": [
                    {"x": 45, "y": 1.75, "speed": 4.5, "class": "truck"}
                ]
            },
            "emergency_brake": {
                "name": "Emergency Brake Test",
                "description": "Test emergency braking with stationary obstacle",
                "ego_start": {"x": 0, "y": 1.75, "yaw": 0, "speed": 20},
                "goal": {"x": 1500, "y": 1.75},
                "traffic_density": 0,
                "duration": 180,
                "special_objects": [
                    {"x": 50, "y": 1.75, "speed": 0, "class": "car"}
                ]
            },
        }

    def get_scenario(self, name: str) -> Dict[str, Any]:
        """Get scenario by name."""
        return self.scenarios.get(name, self.scenarios["highway"])

    def list_scenarios(self) -> List[str]:
        """List available scenarios."""
        return list(self.scenarios.keys())

    def apply_scenario(self, name: str, world_manager) -> VehicleState:
        """Apply scenario to world."""
        scenario = self.get_scenario(name)
        self.current_scenario = scenario

        ego_start = scenario["ego_start"]
        state = VehicleState()
        state.x = ego_start["x"]
        state.y = ego_start["y"]
        state.yaw = ego_start["yaw"]
        state.speed = ego_start["speed"]
        state.timestamp = 0.0

        return state