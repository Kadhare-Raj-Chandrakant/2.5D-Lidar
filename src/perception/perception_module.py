"""Main perception module integrating all sub-components."""
from typing import List
from ..types import SensorData, PerceptionResult, VehicleState, DetectedObject
from .sensor_simulator import SensorSimulator
from .object_detector import ObjectDetector
from .lane_detector import LaneDetector
from .sensor_fusion import SensorFusion
from .semantic_model import SemanticSegmentationModel
from .foveated_grid import FoveatedGrid25D
from ..utils.config import config


class PerceptionModule:
    """Main perception pipeline with Deep Learning Semantics & Foveated 2.5D Grid."""

    def __init__(self, world_objects: List = None):
        self.sensor_sim = SensorSimulator(world_objects)
        self.obj_detector = ObjectDetector()
        self.lane_detector = LaneDetector()
        self.sensor_fusion = SensorFusion()
        self.semantic_model = SemanticSegmentationModel()
        self.foveated_grid = FoveatedGrid25D()
        self.world_objects = world_objects or []

    def process(self, vehicle_state: VehicleState, dt: float) -> PerceptionResult:
        """Run full perception pipeline with deep learning semantic segmentation and 2.5D mapping."""
        sensor_data = self.sensor_sim.simulate(vehicle_state, dt)

        cam_objs = self.obj_detector.detect_camera(sensor_data.camera_front)
        lidar_objs = self.obj_detector.detect_lidar(sensor_data.lidar)
        radar_objs = self.obj_detector.detect_radar(sensor_data.radar)

        fused_objects = self.sensor_fusion.fuse(cam_objs, lidar_objs, radar_objs)

        lanes = self.lane_detector.detect(sensor_data, vehicle_state)

        # Deep Learning semantic point cloud classification & Foveated 2.5D Grid Engine
        sem_labels, sem_conf, sem_metrics = self.semantic_model.predict(sensor_data.lidar, fused_objects)
        foveated_grid_payload = self.foveated_grid.build_grid(
            sensor_data.lidar,
            sem_labels,
            {"x": vehicle_state.x, "y": vehicle_state.y, "yaw": vehicle_state.yaw}
        )

        result = PerceptionResult(
            objects=fused_objects,
            lanes=lanes,
            timestamp=vehicle_state.timestamp,
            sensor_data={
                'camera_front': sensor_data.camera_front,
                'camera_rear': sensor_data.camera_rear,
                'lidar': sensor_data.lidar,
                'radar': sensor_data.radar,
                'foveated_grid': foveated_grid_payload,
                'semantic_metrics': sem_metrics,
            }
        )

        self.world_objects = fused_objects
        self.sensor_sim.update_world_objects(fused_objects)

        return result

    def update_world_objects(self, objects: List):
        """Update world objects for sensor simulation."""
        self.world_objects = objects
        self.sensor_sim.update_world_objects(objects)