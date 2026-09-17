"""Lane detection from camera/ground plane."""
import numpy as np
from typing import List, Optional
from ..types import LaneMarking, SensorData
from ..utils.config import config


class LaneDetector:
    """Detects lane markings from sensor data."""

    def __init__(self):
        self.method = config.get('perception.lane_detection.method', 'polynomial')
        self.degree = config.get('perception.lane_detection.degree', 3)
        self.window_size = config.get('perception.lane_detection.window_size', 20)

    def detect(self, sensor_data: SensorData, vehicle_state) -> List[LaneMarking]:
        """Detect lanes from camera image (simplified)."""
        lanes = []

        if sensor_data.camera_front is not None:
            lanes.extend(self._detect_from_camera(sensor_data.camera_front))

        lanes.extend(self._generate_synthetic_lanes(vehicle_state))

        return lanes

    def _detect_from_camera(self, image: np.ndarray) -> List[LaneMarking]:
        """Detect lanes from camera (placeholder for real lane detection)."""
        lanes = []
        h, w = image.shape[:2]

        for offset in [-1, 1]:
            points = []
            for i in range(self.window_size):
                y = h - i * (h // self.window_size)
                x = w // 2 + offset * (w // 4) + np.random.randint(-10, 10)
                points.append([x, y])

            lanes.append(LaneMarking(
                points=np.array(points),
                color='white',
                type='solid' if offset == -1 else 'dashed',
                confidence=0.8
            ))

        return lanes

    def _generate_synthetic_lanes(self, vehicle_state) -> List[LaneMarking]:
        """Generate synthetic lane markings based on vehicle position."""
        lanes = []
        markings_y = [-7.0, -3.5, 0.0, 3.5, 7.0]

        for line_y in markings_y:
            points = []
            for s in np.linspace(vehicle_state.x - 40, vehicle_state.x + 100, 25):
                points.append([s, line_y])

            is_edge = abs(line_y) >= 6.9
            lane_type = 'solid' if is_edge else 'dashed'
            color = 'yellow' if is_edge else 'white'

            lanes.append(LaneMarking(
                points=np.array(points),
                color=color,
                type=lane_type,
                confidence=0.95
            ))

        return lanes

    def fit_polynomial(self, points: np.ndarray, degree: int = None) -> np.ndarray:
        """Fit polynomial to lane points."""
        if degree is None:
            degree = self.degree

        if len(points) < degree + 1:
            return np.zeros(degree + 1)

        x = points[:, 0]
        y = points[:, 1]

        try:
            coeffs = np.polyfit(y, x, degree)
            return coeffs
        except:
            return np.zeros(degree + 1)

    def evaluate_polynomial(self, coeffs: np.ndarray, y_vals: np.ndarray) -> np.ndarray:
        """Evaluate polynomial at given y values."""
        return np.polyval(coeffs, y_vals)