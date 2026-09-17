"""FastDEM bridge: C++ backend when available, Python grid_map fallback otherwise."""
import numpy as np

try:
    import fastdem_pybind as _fb
    HAVE_FASTDEM = all(hasattr(_fb, n) for n in ("ElevationMap", "FastDEM"))
    if not HAVE_FASTDEM:
        _fb = None
except ImportError:
    _fb = None
    HAVE_FASTDEM = False

from grid_map import GridMap2D, GridMapConfig


class FastDEMBridge:
    def __init__(self, width=40.0, height=40.0, resolution=0.2,
                 origin_x=-20.0, origin_y=-20.0, use_cpp=True):
        self.use_cpp = use_cpp and HAVE_FASTDEM
        if self.use_cpp:
            self._map = _fb.ElevationMap()
            self._map.setGeometry(width, height, resolution)
            self._mapper = _fb.FastDEM(self._map)
        else:
            nx, ny = int(width / resolution), int(height / resolution)
            self._grid = GridMap2D(GridMapConfig(
                resolution=resolution, size_x=nx, size_y=ny,
                origin_x=origin_x, origin_y=origin_y))

    @property
    def backend(self):
        return "fastdem_cpp" if self.use_cpp else "python_gridmap"

    def integrate(self, points: np.ndarray):
        if self.use_cpp:
            self._mapper.integrate(points.astype(np.float32))
        else:
            self._grid.update(points)

    def get_elevation(self) -> np.ndarray:
        if self.use_cpp:
            return np.asarray(self._map.getHeight())
        return self._grid.get_elevation()

    def get_uncertainty(self) -> np.ndarray:
        if self.use_cpp:
            return np.asarray(self._map.getUncertainty())
        return self._grid.get_uncertainty()
