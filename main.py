import os
import time
import sys
import threading
import asyncio
from typing import Optional

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.types import VehicleState, PerceptionResult, Trajectory, BehaviorDecision, ControlCommand, SensorData
from src.simulation.world import WorldManager
from src.simulation.vehicle import VehicleManager
from src.simulation.scenario import ScenarioManager
from src.simulation.websocket_server import SimulationWebSocketServer
from src.perception import PerceptionModule
from src.planning import PlanningModule
from src.control import ControlModule
from src.visualization import Visualizer
from src.utils.config import config


class Simulation:
    """Main simulation orchestrator with WebSocket broadcasting."""

    def __init__(self, scenario_name: str = "lane_change", enable_websocket: bool = True, headless: bool = False):
        self.scenario_name = scenario_name
        self.scenario_manager = ScenarioManager()
        self.world = WorldManager()
        self.vehicle = VehicleManager()
        self.headless = headless

        self.perception = PerceptionModule(self.world.get_all_objects())
        self.planning = PlanningModule()
        self.control = ControlModule()
        self.visualizer = Visualizer() if not self.headless else None

        self.vehicle_state = self.scenario_manager.apply_scenario(scenario_name, self.world)
        self.planning.set_goal(*self.scenario_manager.get_scenario(scenario_name)["goal"].values())

        self.dt = config.get('simulation.dt', 0.033)
        self.max_steps = int(config.get('simulation.duration', 60) / self.dt)
        self.step_count = 0
        self.running = True

        self.perception_time = 0.0
        self.planning_time = 0.0
        self.control_time = 0.0

        # WebSocket server
        self.enable_websocket = enable_websocket
        self.ws_server = None
        self.ws_thread = None
        self.ws_loop = None

        if enable_websocket:
            self._start_websocket_server()

    def _start_websocket_server(self):
        """Start WebSocket server in background thread."""
        def run_ws():
            self.ws_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.ws_loop)
            self.ws_server = SimulationWebSocketServer()
            self.ws_loop.run_until_complete(self.ws_server.start())

        self.ws_thread = threading.Thread(target=run_ws, daemon=True)
        self.ws_thread.start()
        time.sleep(0.5)  # Give server time to start
        print(f"WebSocket server started on ws://localhost:8765")

    def step(self) -> bool:
        """Run one simulation step."""
        if not self.running:
            return False

        if self.step_count >= self.max_steps or self.vehicle_state.x >= 1200.0:
            self.step_count = 0
            self.vehicle_state = self.scenario_manager.apply_scenario(self.scenario_name, self.world)
            self.planning.set_goal(*self.scenario_manager.get_scenario(self.scenario_name)["goal"].values())

        if not self.headless:
            if not self.visualizer.handle_events():
                return False

        self.world.step(self.vehicle_state)

        self.perception.update_world_objects(self.world.get_all_objects())

        t0 = time.perf_counter()
        perception_result = self.perception.process(self.vehicle_state, self.dt)
        self.perception_time = time.perf_counter() - t0

        traffic_sig, active_sig = self.world.get_traffic_signal() if hasattr(self.world, 'get_traffic_signal') else ('green', 55.0)
        perception_result.sensor_data['traffic_signal'] = traffic_sig
        perception_result.sensor_data['active_signal_station'] = active_sig

        t0 = time.perf_counter()
        trajectory, behavior = self.planning.plan(self.vehicle_state, perception_result)
        self.planning_time = time.perf_counter() - t0

        trajectory.planning_time = self.planning_time

        t0 = time.perf_counter()
        control_cmd = self.control.compute(self.vehicle_state, trajectory, behavior, self.dt)
        self.control_time = time.perf_counter() - t0

        sensor_data = SensorData(
            camera_front=perception_result.sensor_data.get('camera_front'),
            camera_rear=perception_result.sensor_data.get('camera_rear'),
            lidar=perception_result.sensor_data.get('lidar'),
            radar=perception_result.sensor_data.get('radar'),
            timestamp=self.vehicle_state.timestamp
        )

        self.vehicle_state = self.vehicle.step(self.vehicle_state, control_cmd, self.dt)

        # Broadcast to WebSocket clients
        if self.enable_websocket and self.ws_server:
            traffic_sig, active_sig = self.world.get_traffic_signal() if hasattr(self.world, 'get_traffic_signal') else ('green', 55.0)
            self.ws_server.update_data(
                self.vehicle_state, perception_result, trajectory, behavior, control_cmd, sensor_data,
                traffic_sig, active_sig, world_objects=self.world.get_all_objects()
            )

        if not self.headless:
            self.visualizer.render(
                self.vehicle_state, perception_result, trajectory, behavior, control_cmd, sensor_data
            )

        self.step_count += 1

        if self.step_count % 60 == 0:
            self._print_stats(behavior)

        return True

    def _print_stats(self, behavior: BehaviorDecision):
        """Print performance stats."""
        ws_status = f"WS:{len(self.ws_server.clients) if self.ws_server else 0}" if self.enable_websocket else ""
        print(f"Step {self.step_count}/{self.max_steps} | "
              f"Pos: ({self.vehicle_state.x:.1f}, {self.vehicle_state.y:.1f}) | "
              f"Speed: {self.vehicle_state.speed*3.6:.1f} km/h | "
              f"Behavior: {behavior.state.value} | "
              f"Perception: {self.perception_time*1000:.1f}ms | "
              f"Planning: {self.planning_time*1000:.1f}ms | "
              f"Control: {self.control_time*1000:.1f}ms | "
              f"FPS: {self.visualizer.fps if self.visualizer else int(1/self.dt)} {ws_status}")

    def run(self):
        """Run simulation loop."""
        print(f"Starting simulation: {self.scenario_manager.get_scenario('highway')['name']}")
        print(f"Duration: {config.get('simulation.duration', 60)}s @ {1/self.dt:.0f}Hz")
        if self.enable_websocket:
            print(f"Web UI available at: http://localhost:3000")

        try:
            while self.running:
                step_start = time.perf_counter()
                if not self.step():
                    break
                if self.headless:
                    elapsed = time.perf_counter() - step_start
                    sleep_time = max(0.001, self.dt - elapsed)
                    time.sleep(sleep_time)
        except KeyboardInterrupt:
            print("\nSimulation interrupted")
        finally:
            if not self.headless:
                self.visualizer.close()
            print("Simulation ended")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('scenario', nargs='?', default='lane_change', help='Scenario name')
    parser.add_argument('--no-ws', action='store_true', help='Disable WebSocket server')
    parser.add_argument('--headless', action='store_true', help='Run without pygame visualization')
    args = parser.parse_args()

    sim = Simulation(args.scenario, enable_websocket=not args.no_ws, headless=args.headless)
    sim.run()


if __name__ == "__main__":
    main()