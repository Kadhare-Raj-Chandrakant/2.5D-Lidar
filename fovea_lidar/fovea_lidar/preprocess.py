import numpy as np
from typing import Tuple, Optional
import struct

try:
    from sensor_msgs.msg import PointCloud2, PointField
    from builtin_interfaces.msg import Time
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False
    PointCloud2 = None
    PointField = None
    Time = None


def pointcloud2_to_array(msg: PointCloud2, remove_nan: bool = True) -> np.ndarray:
    """Convert PointCloud2 to Nx3 numpy array (x, y, z)."""
    dtype_list = []
    for field in msg.fields:
        if field.datatype == PointField.FLOAT32:
            dtype_list.append((field.name, np.float32))
        elif field.datatype == PointField.FLOAT64:
            dtype_list.append((field.name, np.float64))
        elif field.datatype == PointField.INT32:
            dtype_list.append((field.name, np.int32))
        elif field.datatype == PointField.UINT32:
            dtype_list.append((field.name, np.uint32))
        elif field.datatype == PointField.INT16:
            dtype_list.append((field.name, np.int16))
        elif field.datatype == PointField.UINT16:
            dtype_list.append((field.name, np.uint16))
        elif field.datatype == PointField.INT8:
            dtype_list.append((field.name, np.int8))
        elif field.datatype == PointField.UINT8:
            dtype_list.append((field.name, np.uint8))

    if not dtype_list:
        return np.empty((0, 3), dtype=np.float32)

    dtype = np.dtype(dtype_list)
    data = np.frombuffer(msg.data, dtype=dtype)

    if data.size == 0:
        return np.empty((0, 3), dtype=np.float32)

    x = data['x'].astype(np.float32)
    y = data['y'].astype(np.float32)
    z = data['z'].astype(np.float32)

    points = np.column_stack((x, y, z))

    if remove_nan:
        mask = np.isfinite(points).all(axis=1)
        points = points[mask]

    return points


def array_to_pointcloud2(points: np.ndarray, frame_id: str = "map", stamp: Optional[Time] = None) -> PointCloud2:
    """Convert Nx3 numpy array to PointCloud2."""
    msg = PointCloud2()
    msg.header.frame_id = frame_id
    if stamp:
        msg.header.stamp = stamp

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


def remove_nan_inf(points: np.ndarray) -> np.ndarray:
    """Remove points with NaN or Inf values."""
    if points.size == 0:
        return points
    mask = np.isfinite(points).all(axis=1)
    return points[mask]


def range_filter(points: np.ndarray, min_range: float, max_range: float) -> np.ndarray:
    """Filter points by distance from origin."""
    if points.size == 0:
        return points
    dist_sq = np.sum(points[:, :2] ** 2, axis=1)
    mask = (dist_sq >= min_range ** 2) & (dist_sq <= max_range ** 2)
    return points[mask]


def voxel_downsample(points: np.ndarray, voxel_size: float) -> np.ndarray:
    """Voxel grid downsampling using numpy (no Open3D dependency)."""
    if points.size == 0:
        return points

    voxel_indices = np.floor(points / voxel_size).astype(np.int32)

    _, unique_indices = np.unique(voxel_indices, axis=0, return_index=True)
    return points[unique_indices]


def preprocess_points(
    points: np.ndarray,
    min_range: float = 0.5,
    max_range: float = 50.0,
    voxel_size: float = 0.1,
    remove_nan: bool = True,
) -> np.ndarray:
    """Full preprocessing pipeline."""
    if points.size == 0:
        return points

    if remove_nan:
        points = remove_nan_inf(points)

    points = range_filter(points, min_range, max_range)

    if voxel_size > 0:
        points = voxel_downsample(points, voxel_size)

    return points


def estimate_normals(points: np.ndarray, k: int = 10) -> np.ndarray:
    """Estimate surface normals using PCA on k-nearest neighbors (simplified)."""
    if points.shape[0] < 3:
        return np.zeros((points.shape[0], 3), dtype=np.float32)

    normals = np.zeros((points.shape[0], 3), dtype=np.float32)
    for i in range(points.shape[0]):
        diffs = points - points[i]
        dists = np.sum(diffs ** 2, axis=1)
        nn_idx = np.argpartition(dists, min(k, len(dists) - 1))[:k]
        nn_points = points[nn_idx]
        cov = np.cov(nn_points.T)
        eigvals, eigvecs = np.linalg.eigh(cov)
        normals[i] = eigvecs[:, 0]
    return normals