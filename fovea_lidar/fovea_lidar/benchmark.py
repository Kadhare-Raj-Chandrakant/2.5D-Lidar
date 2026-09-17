import time
import threading
from collections import defaultdict
from contextlib import contextmanager
from typing import Dict, List, Optional, Any

try:
    import rclpy
    from rclpy.node import Node
    ROS2_AVAILABLE = True
except ImportError:
    rclpy = None
    Node = None
    ROS2_AVAILABLE = False


class BenchmarkTimer:
    def __init__(self, node: Optional[Node] = None, enabled: bool = True):
        self.node = node
        self.enabled = enabled
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self.active_timers: Dict[str, float] = {}
        self.lock = threading.Lock()
        self.frame_count = 0

    @contextmanager
    def time(self, name: str):
        if not self.enabled:
            yield
            return
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - start) * 1000  # ms
            with self.lock:
                self.timings[name].append(elapsed)

    def start(self, name: str):
        if not self.enabled:
            return
        with self.lock:
            self.active_timers[name] = time.perf_counter()

    def stop(self, name: str):
        if not self.enabled or name not in self.active_timers:
            return
        elapsed = (time.perf_counter() - self.active_timers.pop(name)) * 1000
        with self.lock:
            self.timings[name].append(elapsed)

    def next_frame(self):
        self.frame_count += 1

    def get_stats(self) -> Dict[str, Dict[str, float]]:
        with self.lock:
            stats = {}
            for name, values in self.timings.items():
                if values:
                    sorted_vals = sorted(values)
                    stats[name] = {
                        'count': len(values),
                        'mean_ms': sum(values) / len(values),
                        'min_ms': min(values),
                        'max_ms': max(values),
                        'p50_ms': sorted_vals[len(sorted_vals) // 2],
                        'p95_ms': sorted_vals[int(len(sorted_vals) * 0.95)],
                        'p99_ms': sorted_vals[int(len(sorted_vals) * 0.99)] if len(sorted_vals) > 100 else max(values),
                    }
            return stats

    def print_summary(self):
        stats = self.get_stats()
        if not stats:
            return
        print("\n" + "=" * 60)
        print(f"BENCHMARK SUMMARY (frames: {self.frame_count})")
        print("=" * 60)
        print(f"{'Stage':<25} {'Count':>6} {'Mean(ms)':>10} {'P50':>8} {'P95':>8} {'Max':>8}")
        print("-" * 60)
        total_mean = 0
        for name, s in sorted(stats.items(), key=lambda x: x[1]['mean_ms'], reverse=True):
            print(f"{name:<25} {s['count']:>6} {s['mean_ms']:>10.2f} {s['p50_ms']:>8.2f} {s['p95_ms']:>8.2f} {s['max_ms']:>8.2f}")
            total_mean += s['mean_ms']
        print("-" * 60)
        print(f"{'TOTAL':<25} {'':>6} {total_mean:>10.2f}")
        print("=" * 60)

        if self.node:
            self.node.get_logger().info(f"Avg frame time: {total_mean:.2f} ms")


benchmark_timer = BenchmarkTimer()