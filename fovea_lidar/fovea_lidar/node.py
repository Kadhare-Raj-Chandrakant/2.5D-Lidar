import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import PointCloud2
from visualization_msgs.msg import MarkerArray
from std_msgs.msg import Bool
import numpy as np
import yaml
import os
import time
import threading

from preprocess import pointcloud2_to_array, preprocess_points
from grid_map import GridMap2D, GridMapConfig
from risk import compute_risk
from uncertainty import compute_uncertainty
from foveation import compute_foveation_pipeline, ROI
from hysteresis import HysteresisManager
from fallback import FallbackController, FallbackMapPublisher
from viz import Visualizer
from benchmark import benchmark_timer


class FoveaLidarNode(Node):
    def __init__(self):
        super().__init__('fovea_lidar_node')
        
        self.declare_parameters(
            namespace='',
            parameters=[
                ('config_file', ''),
                ('input_topic', '/lidar_points'),
                ('output_topic_elevation', '/fovea/elevation_map'),
                ('output_topic_occupancy', '/fovea/occupancy_map'),
                ('output_topic_risk', '/fovea/risk_map'),
                ('output_topic_roi', '/fovea/foveation_rois'),
                ('output_topic_fallback', '/fovea/fallback_map'),
                ('viz_rate_hz', 10.0),
            ]
        )

        config_file = self.get_parameter('config_file').get_parameter_value().string_value
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            pkg_share = os.path.join(os.path.dirname(__file__), '..', 'config', 'params.yaml')
            if os.path.exists(pkg_share):
                with open(pkg_share, 'r') as f:
                    self.config = yaml.safe_load(f)
            else:
                self.config = self._default_config()

        self._init_components()
        self._init_publishers()
        self._init_subscribers()
        self._init_timers()

        self.frame_id = 0
        self.latest_points = None
        self.points_lock = threading.Lock()
        self.running = True

        self.get_logger().info('Fovea LiDAR Node initialized')

    def _default_config(self):
        return {
            'max_range': 50.0,
            'min_range': 0.5,
            'voxel_size': 0.1,
            'grid_resolution': 0.2,
            'grid_size_x': 200,
            'grid_size_y': 200,
            'grid_origin_x': -20.0,
            'grid_origin_y': -20.0,
            'occupancy_threshold': 1,
            'risk_weight_occupancy': 1.0,
            'risk_weight_elevation_var': 0.5,
            'risk_weight_proximity': 0.3,
            'risk_weight_roughness': 0.2,
            'proximity_falloff': 10.0,
            'uncertainty_base': 1.0,
            'uncertainty_decay': 0.1,
            'foveation_alpha': 0.7,
            'foveation_beta': 0.3,
            'foveation_top_k': 10,
            'roi_min_size': 3,
            'roi_max_size': 15,
            'roi_expansion': 1,
            'hysteresis_frames': 5,
            'hysteresis_threshold': 0.3,
            'fallback_latency_ms': 100,
            'fallback_coarse_resolution': 1.0,
            'target_frame_time_ms': 100,
            'max_points_per_frame': 50000,
            'viz_elevation_min': -2.0,
            'viz_elevation_max': 3.0,
        }

    def _init_components(self):
        grid_config = GridMapConfig(
            resolution=self.config['grid_resolution'],
            size_x=self.config['grid_size_x'],
            size_y=self.config['grid_size_y'],
            origin_x=self.config['grid_origin_x'],
            origin_y=self.config['grid_origin_y'],
            occupancy_threshold=self.config['occupancy_threshold'],
            coarse_resolution=self.config['fallback_coarse_resolution'],
        )
        self.grid_map = GridMap2D(grid_config)

        self.hysteresis = HysteresisManager(
            hysteresis_frames=self.config['hysteresis_frames']
        )

        self.fallback_controller = FallbackController(
            max_latency_ms=self.config['fallback_latency_ms'],
            coarse_map=self.grid_map.coarse_map,
            on_fallback=self._on_fallback,
            on_recover=self._on_recover,
        )

        self.fallback_publisher = FallbackMapPublisher(self.grid_map.coarse_map)

        self.visualizer = Visualizer(
            frame_id="map",
            elevation_min=self.config['viz_elevation_min'],
            elevation_max=self.config['viz_elevation_max'],
        )

        self.prev_rois: list[ROI] = []
        self.in_fallback_mode = False

    def _init_publishers(self):
        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
        )

        self.pub_elevation = self.create_publisher(
            MarkerArray, self.get_parameter('output_topic_elevation').value, qos)
        self.pub_occupancy = self.create_publisher(
            MarkerArray, self.get_parameter('output_topic_occupancy').value, qos)
        self.pub_risk = self.create_publisher(
            MarkerArray, self.get_parameter('output_topic_risk').value, qos)
        self.pub_roi = self.create_publisher(
            MarkerArray, self.get_parameter('output_topic_roi').value, qos)
        self.pub_fallback = self.create_publisher(
            MarkerArray, self.get_parameter('output_topic_fallback').value, qos)

        self.pub_fallback_status = self.create_publisher(Bool, '/fovea/fallback_active', 10)

    def _init_subscribers(self):
        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=5,
        )
        self.sub_lidar = self.create_subscription(
            PointCloud2,
            self.get_parameter('input_topic').value,
            self.lidar_callback,
            qos,
        )

    def _init_timers(self):
        viz_rate = self.get_parameter('viz_rate_hz').value
        self.timer = self.create_timer(1.0 / viz_rate, self.process_and_publish)

    def lidar_callback(self, msg: PointCloud2):
        try:
            points = pointcloud2_to_array(msg, remove_nan=True)
            with self.points_lock:
                self.latest_points = points
        except Exception as e:
            self.get_logger().error(f'Error processing point cloud: {e}')

    def _on_fallback(self):
        self.get_logger().warn('FALLBACK ACTIVATED - Switching to coarse map')
        self.in_fallback_mode = True
        self.pub_fallback_status.publish(Bool(data=True))

    def _on_recover(self):
        self.get_logger().info('FALLBACK RECOVERED - Resuming foveated processing')
        self.in_fallback_mode = False
        self.pub_fallback_status.publish(Bool(data=False))

    def process_and_publish(self):
        self.fallback_controller.record_frame_start()
        benchmark_timer.next_frame()

        points = None
        with self.points_lock:
            if self.latest_points is not None:
                points = self.latest_points.copy()
                self.latest_points = None

        success = True
        try:
            if points is not None and len(points) > 0:
                with benchmark_timer.time("preprocess"):
                    points = preprocess_points(
                        points,
                        min_range=self.config['min_range'],
                        max_range=self.config['max_range'],
                        voxel_size=self.config['voxel_size'],
                        remove_nan=True,
                    )

                if len(points) > self.config['max_points_per_frame']:
                    idx = np.random.choice(len(points), self.config['max_points_per_frame'], replace=False)
                    points = points[idx]

                self.grid_map.update(points)

            risk = compute_risk(
                self.grid_map,
                weight_occupancy=self.config['risk_weight_occupancy'],
                weight_elevation_var=self.config['risk_weight_elevation_var'],
                weight_proximity=self.config['risk_weight_proximity'],
                weight_roughness=self.config['risk_weight_roughness'],
                proximity_falloff=self.config['proximity_falloff'],
            )

            uncertainty = compute_uncertainty(
                self.grid_map,
                base_uncertainty=self.config['uncertainty_base'],
                decay_rate=self.config['uncertainty_decay'],
            )

            self.prev_rois = compute_foveation_pipeline(
                self.grid_map,
                risk,
                uncertainty,
                self.prev_rois,
                self.frame_id,
                alpha=self.config['foveation_alpha'],
                beta=self.config['foveation_beta'],
                top_k=self.config['foveation_top_k'],
                threshold=self.config['hysteresis_threshold'],
                roi_min_size=self.config['roi_min_size'],
                roi_max_size=self.config['roi_max_size'],
                roi_expansion=self.config['roi_expansion'],
                hysteresis_frames=self.config['hysteresis_frames'],
            )

        except Exception as e:
            self.get_logger().error(f'Processing error: {e}')
            success = False

        self.fallback_controller.record_frame_end(success)
        self.frame_id += 1

        self.publish_visualization()

        if self.frame_id % 100 == 0:
            benchmark_timer.print_summary()

    def publish_visualization(self):
        self.visualizer.reset_counter()

        if self.in_fallback_mode:
            fallback_markers = self.visualizer.create_fallback_markers(self.grid_map.coarse_map)
            self.pub_fallback.publish(fallback_markers)
        else:
            elevation_markers = self.visualizer.create_elevation_markers(self.grid_map)
            self.pub_elevation.publish(elevation_markers)

            occupancy_markers = self.visualizer.create_occupancy_markers(self.grid_map)
            self.pub_occupancy.publish(occupancy_markers)

            risk = compute_risk(
                self.grid_map,
                weight_occupancy=self.config['risk_weight_occupancy'],
                weight_elevation_var=self.config['risk_weight_elevation_var'],
                weight_proximity=self.config['risk_weight_proximity'],
                weight_roughness=self.config['risk_weight_roughness'],
                proximity_falloff=self.config['proximity_falloff'],
            )
            risk_markers = self.visualizer.create_risk_markers(self.grid_map, risk)
            self.pub_risk.publish(risk_markers)

            roi_markers = self.visualizer.create_roi_markers(self.prev_rois)
            self.pub_roi.publish(roi_markers)

    def destroy_node(self):
        self.running = False
        benchmark_timer.print_summary()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = FoveaLidarNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()