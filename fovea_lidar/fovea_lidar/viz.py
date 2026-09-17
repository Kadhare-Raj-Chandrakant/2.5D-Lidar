import numpy as np
from typing import List, Optional
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point
from std_msgs.msg import ColorRGBA
from builtin_interfaces.msg import Duration
from grid_map import GridMap2D
from foveation import ROI
from benchmark import benchmark_timer


class Visualizer:
    def __init__(
        self,
        frame_id: str = "map",
        elevation_min: float = -2.0,
        elevation_max: float = 3.0,
    ):
        self.frame_id = frame_id
        self.elevation_min = elevation_min
        self.elevation_max = elevation_max
        self.marker_id_counter = 0

    def _next_id(self) -> int:
        self.marker_id_counter += 1
        return self.marker_id_counter

    def _elevation_to_color(self, z: float) -> ColorRGBA:
        z_clipped = np.clip(z, self.elevation_min, self.elevation_max)
        t = (z_clipped - self.elevation_min) / (self.elevation_max - self.elevation_min)
        r = int(255 * t)
        g = int(255 * (1 - t))
        b = 0
        return ColorRGBA(r=r/255.0, g=g/255.0, b=b/255.0, a=0.7)

    def _risk_to_color(self, risk: float, max_risk: float = 10.0) -> ColorRGBA:
        t = np.clip(risk / max_risk, 0.0, 1.0)
        r = int(255 * t)
        g = int(255 * (1 - t))
        b = 0
        return ColorRGBA(r=r/255.0, g=g/255.0, b=b/255.0, a=0.8)

    def create_elevation_markers(self, grid_map: GridMap2D, namespace: str = "elevation") -> MarkerArray:
        with benchmark_timer.time("viz_elevation"):
            markers = MarkerArray()
            elevation = grid_map.get_elevation()
            occupancy = grid_map.get_occupancy()
            size_y, size_x = elevation.shape
            res = grid_map.resolution
            ox, oy = grid_map.origin_x, grid_map.origin_y

            marker = Marker()
            marker.header.frame_id = self.frame_id
            marker.ns = namespace
            marker.id = self._next_id()
            marker.type = Marker.CUBE_LIST
            marker.action = Marker.ADD
            marker.pose.orientation.w = 1.0
            marker.scale.x = res * 0.95
            marker.scale.y = res * 0.95
            marker.scale.z = 0.05
            marker.lifetime = Duration(sec=1)

            points = []
            colors = []

            for y in range(size_y):
                for x in range(size_x):
                    if occupancy[y, x] > 0 and np.isfinite(elevation[y, x]):
                        wx = ox + (x + 0.5) * res
                        wy = oy + (y + 0.5) * res
                        wz = elevation[y, x]
                        points.append(Point(x=wx, y=wy, z=wz))
                        colors.append(self._elevation_to_color(wz))

            marker.points = points
            marker.colors = colors
            markers.markers.append(marker)
            return markers

    def create_occupancy_markers(self, grid_map: GridMap2D, namespace: str = "occupancy") -> MarkerArray:
        with benchmark_timer.time("viz_occupancy"):
            markers = MarkerArray()
            occupancy = grid_map.get_occupancy()
            size_y, size_x = occupancy.shape
            res = grid_map.resolution
            ox, oy = grid_map.origin_x, grid_map.origin_y

            marker = Marker()
            marker.header.frame_id = self.frame_id
            marker.ns = namespace
            marker.id = self._next_id()
            marker.type = Marker.CUBE_LIST
            marker.action = Marker.ADD
            marker.pose.orientation.w = 1.0
            marker.scale.x = res * 0.9
            marker.scale.y = res * 0.9
            marker.scale.z = 0.1
            marker.lifetime = Duration(sec=1)

            points = []
            colors = []

            for y in range(size_y):
                for x in range(size_x):
                    if occupancy[y, x] > 0:
                        wx = ox + (x + 0.5) * res
                        wy = oy + (y + 0.5) * res
                        points.append(Point(x=wx, y=wy, z=0.05))
                        colors.append(ColorRGBA(r=1.0, g=0.0, b=0.0, a=0.5))

            marker.points = points
            marker.colors = colors
            markers.markers.append(marker)
            return markers

    def create_risk_markers(self, grid_map: GridMap2D, risk: np.ndarray, namespace: str = "risk") -> MarkerArray:
        with benchmark_timer.time("viz_risk"):
            markers = MarkerArray()
            occupancy = grid_map.get_occupancy()
            size_y, size_x = risk.shape
            res = grid_map.resolution
            ox, oy = grid_map.origin_x, grid_map.origin_y

            marker = Marker()
            marker.header.frame_id = self.frame_id
            marker.ns = namespace
            marker.id = self._next_id()
            marker.type = Marker.CUBE_LIST
            marker.action = Marker.ADD
            marker.pose.orientation.w = 1.0
            marker.scale.x = res * 0.8
            marker.scale.y = res * 0.8
            marker.scale.z = 0.2
            marker.lifetime = Duration(sec=1)

            points = []
            colors = []

            max_risk = risk.max() if risk.max() > 0 else 1.0

            for y in range(size_y):
                for x in range(size_x):
                    if occupancy[y, x] > 0 and risk[y, x] > 0.1:
                        wx = ox + (x + 0.5) * res
                        wy = oy + (y + 0.5) * res
                        points.append(Point(x=wx, y=wy, z=0.15))
                        colors.append(self._risk_to_color(risk[y, x], max_risk))

            marker.points = points
            marker.colors = colors
            markers.markers.append(marker)
            return markers

    def create_roi_markers(self, rois: List[ROI], namespace: str = "foveation_roi") -> MarkerArray:
        with benchmark_timer.time("viz_roi"):
            markers = MarkerArray()
            
            for i, roi in enumerate(rois):
                marker = Marker()
                marker.header.frame_id = self.frame_id
                marker.ns = namespace
                marker.id = self._next_id()
                marker.type = Marker.CUBE
                marker.action = Marker.ADD
                marker.pose.position.x = roi.center_x
                marker.pose.position.y = roi.center_y
                marker.pose.position.z = 1.0
                marker.pose.orientation.w = 1.0
                marker.scale.x = roi.size_x * 0.2 * 0.95
                marker.scale.y = roi.size_y * 0.2 * 0.95
                marker.scale.z = 2.0
                marker.color = ColorRGBA(r=0.0, g=1.0, b=1.0, a=0.5)
                marker.lifetime = Duration(sec=1)
                markers.markers.append(marker)

                wire = Marker()
                wire.header.frame_id = self.frame_id
                wire.ns = namespace + "_wire"
                wire.id = self._next_id()
                wire.type = Marker.LINE_STRIP
                wire.action = Marker.ADD
                wire.pose.orientation.w = 1.0
                wire.scale.x = 0.05
                wire.color = ColorRGBA(r=0.0, g=1.0, b=1.0, a=1.0)
                wire.lifetime = Duration(sec=1)
                
                half_x = roi.size_x * 0.2 / 2
                half_y = roi.size_y * 0.2 / 2
                corners = [
                    Point(x=roi.center_x - half_x, y=roi.center_y - half_y, z=0.0),
                    Point(x=roi.center_x + half_x, y=roi.center_y - half_y, z=0.0),
                    Point(x=roi.center_x + half_x, y=roi.center_y + half_y, z=0.0),
                    Point(x=roi.center_x - half_x, y=roi.center_y + half_y, z=0.0),
                    Point(x=roi.center_x - half_x, y=roi.center_y - half_y, z=0.0),
                ]
                wire.points = corners
                markers.markers.append(wire)

                text = Marker()
                text.header.frame_id = self.frame_id
                text.ns = namespace + "_text"
                text.id = self._next_id()
                text.type = Marker.TEXT_VIEW_FACING
                text.action = Marker.ADD
                text.pose.position.x = roi.center_x
                text.pose.position.y = roi.center_y
                text.pose.position.z = 2.5
                text.pose.orientation.w = 1.0
                text.scale.z = 0.5
                text.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
                text.text = f"ROI:{roi.score:.2f}"
                text.lifetime = Duration(sec=1)
                markers.markers.append(text)

            return markers

    def create_fallback_markers(self, coarse_map, namespace: str = "fallback") -> MarkerArray:
        with benchmark_timer.time("viz_fallback"):
            markers = MarkerArray()
            elevation = coarse_map.get_elevation_grid()
            occupancy = coarse_map.get_occupancy_grid()
            size_y, size_x = elevation.shape
            res = coarse_map.resolution
            ox, oy = coarse_map.origin_x, coarse_map.origin_y

            marker = Marker()
            marker.header.frame_id = self.frame_id
            marker.ns = namespace
            marker.id = self._next_id()
            marker.type = Marker.CUBE_LIST
            marker.action = Marker.ADD
            marker.pose.orientation.w = 1.0
            marker.scale.x = res * 0.9
            marker.scale.y = res * 0.9
            marker.scale.z = 0.1
            marker.lifetime = Duration(sec=1)

            points = []
            colors = []

            for y in range(size_y):
                for x in range(size_x):
                    if occupancy[y, x] > 0 and np.isfinite(elevation[y, x]):
                        wx = ox + (x + 0.5) * res
                        wy = oy + (y + 0.5) * res
                        wz = elevation[y, x]
                        points.append(Point(x=wx, y=wy, z=wz))
                        colors.append(ColorRGBA(r=0.5, g=0.5, b=1.0, a=0.6))

            marker.points = points
            marker.colors = colors
            markers.markers.append(marker)
            return markers

    def reset_counter(self):
        self.marker_id_counter = 0