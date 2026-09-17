"""Global path planner using A* on road graph."""
import numpy as np
import heapq
from typing import List, Optional, Tuple, Dict
from ..types import Waypoint, Trajectory, VehicleState
from ..utils.config import config


class GlobalPlanner:
    """Global route planner using A* on waypoint graph."""

    def __init__(self):
        self.resolution = config.get('planning.global.resolution', 2.0)
        self.waypoints: List[Waypoint] = []
        self.graph: Dict[int, List[Tuple[int, float]]] = {}
        self._build_road_graph()

    def _build_road_graph(self):
        """Build synthetic road graph for lane centers."""
        self.waypoints = []
        self.graph = {}
        lane_centers = [-5.25, -1.75, 1.75, 5.25]
        s_steps = np.arange(0, 1500, self.resolution)
        num_s = len(s_steps)

        # Store 2D index to waypoint ID mapping
        grid = {}
        for l_idx, lane_y in enumerate(lane_centers):
            for s_idx, s in enumerate(s_steps):
                idx = len(self.waypoints)
                grid[(l_idx, s_idx)] = idx
                self.waypoints.append(Waypoint(x=float(s), y=float(lane_y), yaw=0.0, speed=15.0, s=float(s)))
                self.graph[idx] = []

        # Connect neighbors directly (same lane forward, and adjacent lane changes)
        for l_idx in range(len(lane_centers)):
            for s_idx in range(num_s - 1):
                cur_idx = grid[(l_idx, s_idx)]
                # Forward in same lane
                next_same = grid[(l_idx, s_idx + 1)]
                self.graph[cur_idx].append((next_same, self.resolution))

                # Diagonal transition to left lane
                if l_idx > 0:
                    left_next = grid[(l_idx - 1, s_idx + 1)]
                    dist = float(np.hypot(self.resolution, 3.5))
                    self.graph[cur_idx].append((left_next, dist))

                # Diagonal transition to right lane
                if l_idx < len(lane_centers) - 1:
                    right_next = grid[(l_idx + 1, s_idx + 1)]
                    dist = float(np.hypot(self.resolution, 3.5))
                    self.graph[cur_idx].append((right_next, dist))

    def plan(self, start: VehicleState, goal: Tuple[float, float]) -> Trajectory:
        """Plan global path from start to goal."""
        start_idx = self._nearest_waypoint(start.x, start.y)
        goal_idx = self._nearest_waypoint(goal[0], goal[1])

        path_indices = self._astar(start_idx, goal_idx)

        trajectory = Trajectory()
        for idx in path_indices:
            wp = self.waypoints[idx]
            trajectory.waypoints.append(Waypoint(
                x=wp.x, y=wp.y, yaw=wp.yaw, speed=wp.speed, s=wp.s
            ))

        trajectory.valid = len(trajectory.waypoints) > 0
        return trajectory

    def _nearest_waypoint(self, x: float, y: float) -> int:
        min_dist = float('inf')
        nearest = 0
        for i, wp in enumerate(self.waypoints):
            dist = (wp.x - x)**2 + (wp.y - y)**2
            if dist < min_dist:
                min_dist = dist
                nearest = i
        return nearest

    def _astar(self, start: int, goal: int) -> List[int]:
        open_set = [(0, start)]
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self._heuristic(start, goal)}

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]

            for neighbor, cost in self.graph.get(current, []):
                tentative_g = g_score[current] + cost
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return [start]

    def _heuristic(self, a: int, b: int) -> float:
        wp_a = self.waypoints[a]
        wp_b = self.waypoints[b]
        return np.hypot(wp_a.x - wp_b.x, wp_a.y - wp_b.y)

    def get_waypoints_ahead(self, vehicle_state: VehicleState, horizon: float) -> List[Waypoint]:
        """Get waypoints ahead of vehicle within horizon."""
        idx = self._nearest_waypoint(vehicle_state.x, vehicle_state.y)
        ahead = []
        for i in range(idx, min(idx + int(horizon / self.resolution) + 10, len(self.waypoints))):
            wp = self.waypoints[i]
            dist = np.hypot(wp.x - vehicle_state.x, wp.y - vehicle_state.y)
            if dist <= horizon:
                ahead.append(wp)
        return ahead