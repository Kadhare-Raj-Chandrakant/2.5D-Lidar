import time
import threading
import numpy as np
from typing import Optional, Callable
from grid_map import GridMap2D, CoarseGridMap
from benchmark import benchmark_timer


class FallbackController:
    def __init__(
        self,
        max_latency_ms: float = 100.0,
        coarse_map: Optional[CoarseGridMap] = None,
        on_fallback: Optional[Callable] = None,
        on_recover: Optional[Callable] = None,
    ):
        self.max_latency_ms = max_latency_ms
        self.coarse_map = coarse_map
        self.on_fallback = on_fallback
        self.on_recover = on_recover
        
        self.in_fallback = False
        self.last_frame_time = time.perf_counter()
        self.frame_times = []
        self.lock = threading.Lock()
        self.failure_count = 0
        self.max_failures_before_fallback = 3

    def record_frame_start(self):
        self.last_frame_time = time.perf_counter()

    def record_frame_end(self, success: bool = True):
        now = time.perf_counter()
        frame_time_ms = (now - self.last_frame_time) * 1000
        
        with self.lock:
            self.frame_times.append(frame_time_ms)
            if len(self.frame_times) > 100:
                self.frame_times.pop(0)

            if not success:
                self.failure_count += 1
            else:
                self.failure_count = 0

            avg_latency = sum(self.frame_times) / len(self.frame_times) if self.frame_times else 0
            
            should_fallback = (
                self.failure_count >= self.max_failures_before_fallback or
                avg_latency > self.max_latency_ms
            )

            if should_fallback and not self.in_fallback:
                self.in_fallback = True
                if self.on_fallback:
                    self.on_fallback()
            elif not should_fallback and self.in_fallback:
                self.in_fallback = False
                if self.on_recover:
                    self.on_recover()

    def is_in_fallback(self) -> bool:
        return self.in_fallback

    def get_stats(self) -> dict:
        with self.lock:
            return {
                'in_fallback': self.in_fallback,
                'avg_latency_ms': sum(self.frame_times) / len(self.frame_times) if self.frame_times else 0,
                'max_latency_ms': max(self.frame_times) if self.frame_times else 0,
                'failure_count': self.failure_count,
            }


class FallbackMapPublisher:
    def __init__(self, coarse_map: CoarseGridMap):
        self.coarse_map = coarse_map

    def get_fallback_elevation(self) -> np.ndarray:
        return self.coarse_map.get_elevation_grid()

    def get_fallback_occupancy(self) -> np.ndarray:
        return self.coarse_map.get_occupancy_grid()