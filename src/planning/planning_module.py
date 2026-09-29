"""Main planning module integrating global, local, and behavior planners."""
from typing import Tuple
from ..types import VehicleState, PerceptionResult, Trajectory, BehaviorDecision
from .global_planner import GlobalPlanner
from .local_planner import LocalPlanner
from .behavior_planner import BehaviorPlanner


class PlanningModule:
    """Main planning pipeline."""

    def __init__(self):
        self.global_planner = GlobalPlanner()
        self.local_planner = LocalPlanner()
        self.behavior_planner = BehaviorPlanner()
        self.goal = (1500.0, 1.75)  # Default highway goal

    def set_goal(self, x: float, y: float):
        """Set navigation goal."""
        self.goal = (x, y)

    def plan(self, vehicle_state: VehicleState,
             perception: PerceptionResult) -> Tuple[Trajectory, BehaviorDecision]:
        """Run full planning pipeline."""
        global_traj = self.global_planner.plan(vehicle_state, self.goal)

        behavior = self.behavior_planner.plan(vehicle_state, perception, global_traj)

        local_traj = self.local_planner.plan(
            vehicle_state,
            global_traj.waypoints,
            perception,
            behavior
        )

        return local_traj, behavior