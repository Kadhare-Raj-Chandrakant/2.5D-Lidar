import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from builtin_interfaces.msg import Time
import numpy as np
import math
import time


class SyntheticPublisher(Node):
    def __init__(self):
        super().__init__('synthetic_publisher')
        
        self.declare_parameter('topic', '/lidar_points')
        self.declare_parameter('rate', 10.0)
        self.declare_parameter('num_points', 5000)
        self.declare_parameter('max_range', 50.0)
        self.declare_parameter('add_moving_object', True)
        self.declare_parameter('object_speed', 2.0)

        topic = self.get_parameter('topic').get_parameter_value().string_value
        rate = self.get_parameter('rate').get_parameter_value().double_value
        self.num_points = self.get_parameter('num_points').get_parameter_value().integer_value
        self.max_range = self.get_parameter('max_range').get_parameter_value().double_value
        self.add_moving_object = self.get_parameter('add_moving_object').get_parameter_value().bool_value
        self.object_speed = self.get_parameter('object_speed').get_parameter_value().double_value

        self.publisher = self.create_publisher(PointCloud2, topic, 10)
        self.timer = self.create_timer(1.0 / rate, self.publish_cloud)
        
        self.start_time = time.time()
        self.object_x = 10.0
        self.object_y = 0.0

        self.get_logger().info(f'Synthetic publisher started on {topic} at {rate} Hz')

    def generate_ground_plane(self, num_points: int, max_range: float) -> np.ndarray:
        points = []
        for _ in range(num_points):
            r = np.random.uniform(0.5, max_range)
            theta = np.random.uniform(0, 2 * math.pi)
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            z = np.random.normal(0.0, 0.02)
            points.append([x, y, z])
        return np.array(points, dtype=np.float32)

    def generate_moving_object(self, num_points: int, center_x: float, center_y: float, size: float = 1.5) -> np.ndarray:
        points = []
        for _ in range(num_points):
            x = center_x + np.random.uniform(-size/2, size/2)
            y = center_y + np.random.uniform(-size/2, size/2)
            z = np.random.uniform(0.0, 2.0)
            points.append([x, y, z])
        return np.array(points, dtype=np.float32)

    def generate_noise(self, num_points: int, max_range: float) -> np.ndarray:
        points = []
        for _ in range(num_points):
            r = np.random.uniform(0.5, max_range)
            theta = np.random.uniform(0, 2 * math.pi)
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            z = np.random.uniform(-1.0, 3.0)
            points.append([x, y, z])
        return np.array(points, dtype=np.float32)

    def array_to_pointcloud2(self, points: np.ndarray) -> PointCloud2:
        msg = PointCloud2()
        msg.header.frame_id = "map"
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.height = 1
        msg.width = points.shape[0]
        msg.fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        msg.is_bigendian = False
        msg.point_step = 12
        msg.row_step = msg.point_step * msg.width
        msg.is_dense = True
        msg.data = points.astype(np.float32).tobytes()
        return msg

    def publish_cloud(self):
        elapsed = time.time() - self.start_time

        ground_points = self.generate_ground_plane(self.num_points, self.max_range)

        if self.add_moving_object:
            self.object_x += self.object_speed * (1.0 / 10.0)
            if self.object_x > self.max_range - 5:
                self.object_x = -self.max_range + 5
            obj_points = self.generate_moving_object(500, self.object_x, self.object_y)
            all_points = np.vstack([ground_points, obj_points])
        else:
            all_points = ground_points

        noise_points = self.generate_noise(200, self.max_range)
        all_points = np.vstack([all_points, noise_points])

        msg = self.array_to_pointcloud2(all_points)
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SyntheticPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()