"""Bird's eye view visualization."""
import pygame
import numpy as np
from typing import List
from ..types import VehicleState, PerceptionResult, Trajectory, BehaviorDecision, DetectedObject, LaneMarking
from ..utils.config import config


class BirdEyeView:
    """Bird's eye view renderer."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.range = config.get('visualization.bird_eye_range', 80.0)
        self.scale = min(width, height) / (2 * self.range)
        self.center_x = width // 2
        self.center_y = height // 2

        self.colors = config.get('visualization.colors', {
            'vehicle': [0, 100, 255],
            'trajectory': [0, 255, 0],
            'objects': [255, 0, 0],
            'lanes': [255, 255, 0],
            'lidar': [255, 255, 255]
        })

        self.surface = pygame.Surface((width, height))

    def render(self, vehicle_state: VehicleState,
               perception: PerceptionResult,
               trajectory: Trajectory,
               behavior: BehaviorDecision) -> pygame.Surface:
        """Render bird's eye view."""
        # Surrounding landscape / grass terrain (deep natural green)
        self.surface.fill((21, 54, 34))

        self._draw_road_surface(vehicle_state)
        self._draw_grid()
        self._draw_lanes(perception.lanes, vehicle_state)
        self._draw_objects(perception.objects, vehicle_state)
        self._draw_trajectory(trajectory, vehicle_state)
        self._draw_vehicle(vehicle_state)
        self._draw_fov(vehicle_state)
        self._draw_info(vehicle_state, behavior)

        return self.surface

    def _draw_road_surface(self, vehicle_state: VehicleState):
        """Draw realistic asphalt road corridor, sidewalks, and curbs."""
        road_half_width = 8.0  # 16m total roadway
        curb_width = 0.8
        sidewalk_width = 2.5

        ds_range = np.linspace(-self.range * 1.2, self.range * 1.2, 40)

        left_sidewalk_pts = []
        right_sidewalk_pts = []
        left_curb_pts = []
        right_curb_pts = []
        left_road_pts = []
        right_road_pts = []

        for ds in ds_range:
            wx = vehicle_state.x + ds
            wy = 0.0

            l_sw = self._world_to_screen(wx, wy - (road_half_width + curb_width + sidewalk_width), vehicle_state)
            r_sw = self._world_to_screen(wx, wy + (road_half_width + curb_width + sidewalk_width), vehicle_state)
            l_cb = self._world_to_screen(wx, wy - (road_half_width + curb_width), vehicle_state)
            r_cb = self._world_to_screen(wx, wy + (road_half_width + curb_width), vehicle_state)
            l_rd = self._world_to_screen(wx, wy - road_half_width, vehicle_state)
            r_rd = self._world_to_screen(wx, wy + road_half_width, vehicle_state)

            left_sidewalk_pts.append(l_sw)
            right_sidewalk_pts.append(r_sw)
            left_curb_pts.append(l_cb)
            right_curb_pts.append(r_cb)
            left_road_pts.append(l_rd)
            right_road_pts.append(r_rd)

        # 1. Paved concrete sidewalks
        if len(left_sidewalk_pts) >= 2 and len(right_sidewalk_pts) >= 2:
            sw_poly = left_sidewalk_pts + right_sidewalk_pts[::-1]
            pygame.draw.polygon(self.surface, (63, 69, 83), sw_poly)

        # 2. Asphalt roadway (rich dark-slate tarmac)
        if len(left_road_pts) >= 2 and len(right_road_pts) >= 2:
            road_poly = left_road_pts + right_road_pts[::-1]
            pygame.draw.polygon(self.surface, (34, 38, 51), road_poly)

        # 3. Raised concrete curb lines
        if len(left_curb_pts) >= 2:
            pygame.draw.lines(self.surface, (100, 116, 139), False, left_curb_pts, 3)
            pygame.draw.lines(self.surface, (100, 116, 139), False, right_curb_pts, 3)

    def _draw_grid(self):
        """Draw coordinate grid."""
        grid_size = 10.0
        num_lines = int(self.range / grid_size)

        for i in range(-num_lines, num_lines + 1):
            x = self.center_x + i * grid_size * self.scale
            y = self.center_y + i * grid_size * self.scale

            color = (60, 60, 80) if i != 0 else (100, 100, 120)
            pygame.draw.line(self.surface, color, (x, 0), (x, self.height), 1)
            pygame.draw.line(self.surface, color, (0, y), (self.width, y), 1)

    def _world_to_screen(self, x: float, y: float,
                         vehicle_state: VehicleState) -> tuple:
        """Convert world coordinates to screen coordinates."""
        rel_x = x - vehicle_state.x
        rel_y = y - vehicle_state.y

        cos_yaw = np.cos(-vehicle_state.yaw)
        sin_yaw = np.sin(-vehicle_state.yaw)

        local_x = cos_yaw * rel_x - sin_yaw * rel_y
        local_y = sin_yaw * rel_x + cos_yaw * rel_y

        screen_x = int(self.center_x + local_y * self.scale)
        screen_y = int(self.center_y - local_x * self.scale)

        return screen_x, screen_y

    def _draw_lanes(self, lanes: List[LaneMarking], vehicle_state: VehicleState):
        """Draw lane markings."""
        for lane in lanes:
            if len(lane.points) < 2:
                continue

            points = []
            for pt in lane.points:
                sx, sy = self._world_to_screen(pt[0], pt[1], vehicle_state)
                if 0 <= sx < self.width and 0 <= sy < self.height:
                    points.append((sx, sy))

            if len(points) >= 2:
                color = (255, 255, 255) if lane.color == 'white' else (255, 255, 0)
                if lane.type == 'dashed':
                    for i in range(0, len(points) - 1, 2):
                        pygame.draw.line(self.surface, color, points[i], points[i+1], 2)
                else:
                    pygame.draw.lines(self.surface, color, False, points, 2)

    def _draw_objects(self, objects: List[DetectedObject], vehicle_state: VehicleState):
        """Draw detected objects."""
        for obj in objects:
            if not obj.bbox_3d:
                continue

            bbox = obj.bbox_3d
            corners = self._get_bbox_corners(bbox)
            screen_corners = [self._world_to_screen(c[0], c[1], vehicle_state) for c in corners]

            cls_name = obj.bbox_3d.class_name if obj.bbox_3d else "unknown"
            color = self.colors['objects']
            if cls_name == "person":
                color = (255, 0, 255)
            elif cls_name in ["bicycle", "motorcycle"]:
                color = (255, 165, 0)

            if len(screen_corners) == 4:
                pygame.draw.polygon(self.surface, color, screen_corners, 2)

            cx, cy = self._world_to_screen(bbox.x, bbox.y, vehicle_state)
            if 0 <= cx < self.width and 0 <= cy < self.height:
                font = pygame.font.Font(None, 16)
                conf = obj.bbox_3d.confidence if obj.bbox_3d else 0.0
                text = font.render(f"{cls_name} {conf:.2f}", True, (255, 255, 255))
                self.surface.blit(text, (cx + 10, cy - 10))

                if obj.track_id is not None:
                    id_text = font.render(f"ID:{obj.track_id}", True, (200, 200, 200))
                    self.surface.blit(id_text, (cx + 10, cy + 5))

    def _get_bbox_corners(self, bbox) -> List[tuple]:
        """Get 4 corners of 3D bounding box in bird's eye view."""
        cos_yaw = np.cos(bbox.yaw)
        sin_yaw = np.sin(bbox.yaw)

        half_l = bbox.length / 2
        half_w = bbox.width / 2

        corners = [
            (bbox.x + cos_yaw * half_l - sin_yaw * half_w,
             bbox.y + sin_yaw * half_l + cos_yaw * half_w),
            (bbox.x + cos_yaw * half_l + sin_yaw * half_w,
             bbox.y + sin_yaw * half_l - cos_yaw * half_w),
            (bbox.x - cos_yaw * half_l + sin_yaw * half_w,
             bbox.y - sin_yaw * half_l - cos_yaw * half_w),
            (bbox.x - cos_yaw * half_l - sin_yaw * half_w,
             bbox.y - sin_yaw * half_l + cos_yaw * half_w),
        ]
        return corners

    def _draw_trajectory(self, trajectory: Trajectory, vehicle_state: VehicleState):
        """Draw planned trajectory."""
        if not trajectory.valid or len(trajectory.waypoints) < 2:
            return

        points = []
        for wp in trajectory.waypoints:
            sx, sy = self._world_to_screen(wp.x, wp.y, vehicle_state)
            if 0 <= sx < self.width and 0 <= sy < self.height:
                points.append((sx, sy))

        if len(points) >= 2:
            color = self.colors['trajectory']
            pygame.draw.lines(self.surface, color, False, points, 3)

            for i in range(0, len(points), 5):
                pygame.draw.circle(self.surface, color, points[i], 3)

    def _draw_vehicle(self, vehicle_state: VehicleState):
        """Draw ego vehicle."""
        length = 4.5
        width = 2.0

        cos_yaw = np.cos(vehicle_state.yaw)
        sin_yaw = np.sin(vehicle_state.yaw)

        corners = [
            (cos_yaw * length/2 - sin_yaw * width/2,
             sin_yaw * length/2 + cos_yaw * width/2),
            (cos_yaw * length/2 + sin_yaw * width/2,
             sin_yaw * length/2 - cos_yaw * width/2),
            (-cos_yaw * length/2 + sin_yaw * width/2,
             -sin_yaw * length/2 - cos_yaw * width/2),
            (-cos_yaw * length/2 - sin_yaw * width/2,
             -sin_yaw * length/2 + cos_yaw * width/2),
        ]

        screen_corners = [(int(self.center_x + c[1] * self.scale),
                          int(self.center_y - c[0] * self.scale)) for c in corners]

        color = self.colors['vehicle']
        pygame.draw.polygon(self.surface, color, screen_corners)
        pygame.draw.polygon(self.surface, (255, 255, 255), screen_corners, 2)

        front_center = (int(self.center_x + sin_yaw * length/2 * self.scale),
                       int(self.center_y - cos_yaw * length/2 * self.scale))
        rear_center = (int(self.center_x - sin_yaw * length/2 * self.scale),
                      int(self.center_y + cos_yaw * length/2 * self.scale))
        pygame.draw.line(self.surface, (255, 255, 255), rear_center, front_center, 2)

    def _draw_fov(self, vehicle_state: VehicleState):
        """Draw sensor FOV indicators."""
        fov_angle = np.deg2rad(90)
        range_dist = min(50, self.range)

        left_angle = vehicle_state.yaw + fov_angle/2
        right_angle = vehicle_state.yaw - fov_angle/2

        left_end = (int(self.center_x + range_dist * np.sin(left_angle) * self.scale),
                   int(self.center_y - range_dist * np.cos(left_angle) * self.scale))
        right_end = (int(self.center_x + range_dist * np.sin(right_angle) * self.scale),
                    int(self.center_y - range_dist * np.cos(right_angle) * self.scale))

        pygame.draw.line(self.surface, (100, 100, 150), (self.center_x, self.center_y), left_end, 1)
        pygame.draw.line(self.surface, (100, 100, 150), (self.center_x, self.center_y), right_end, 1)

    def _draw_info(self, vehicle_state: VehicleState, behavior: BehaviorDecision):
        """Draw info text."""
        font = pygame.font.Font(None, 20)
        info = [
            f"Speed: {vehicle_state.speed*3.6:.1f} km/h",
            f"Steer: {np.degrees(vehicle_state.steer_angle):.1f} deg",
            f"Behavior: {behavior.state.value}",
            f"Target Speed: {behavior.target_speed*3.6:.1f} km/h",
        ]

        for i, line in enumerate(info):
            text = font.render(line, True, (255, 255, 255))
            self.surface.blit(text, (10, 10 + i * 22))