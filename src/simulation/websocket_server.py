"""WebSocket server to bridge Python simulation to web UI."""
import asyncio
import json
import time
from typing import Set
import websockets
from websockets.server import WebSocketServerProtocol


class SimulationWebSocketServer:
    """WebSocket server for real-time simulation data streaming."""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.latest_data = None
        self.running = False

    async def register(self, websocket: WebSocketServerProtocol):
        """Register new client."""
        self.clients.add(websocket)
        print(f"Client connected. Total: {len(self.clients)}")

        if self.latest_data:
            await websocket.send(json.dumps(self.latest_data))

    async def unregister(self, websocket: WebSocketServerProtocol):
        """Unregister client."""
        self.clients.discard(websocket)
        print(f"Client disconnected. Total: {len(self.clients)}")

    async def broadcast(self, data: dict):
        """Broadcast data to all connected clients."""
        if not self.clients:
            return

        message = json.dumps(data)
        disconnected = set()

        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                print(f"Error sending to client: {e}")
                disconnected.add(client)

        for client in disconnected:
            self.clients.discard(client)

    async def handler(self, websocket: WebSocketServerProtocol):
        """Handle WebSocket connection."""
        await self.register(websocket)
        try:
            async for message in websocket:
                pass
        finally:
            await self.unregister(websocket)

    def update_data(self, vehicle_state, perception, trajectory, behavior, control, sensor_data):
        """Update latest simulation data for broadcasting."""
        self.latest_data = {
            "type": "simulation_data",
            "timestamp": time.time(),
            "vehicle_state": {
                "x": vehicle_state.x,
                "y": vehicle_state.y,
                "yaw": vehicle_state.yaw,
                "speed": vehicle_state.speed,
                "acceleration": vehicle_state.acceleration,
                "steer_angle": vehicle_state.steer_angle,
            } if vehicle_state else None,
            "perception": {
                "objects": [
                    {
                        "id": obj.id,
                        "track_id": obj.track_id,
                        "class_name": obj.bbox_3d.class_name if obj.bbox_3d else None,
                        "confidence": obj.bbox_3d.confidence if obj.bbox_3d else 0,
                        "bbox_3d": {
                            "x": obj.bbox_3d.x,
                            "y": obj.bbox_3d.y,
                            "z": obj.bbox_3d.z,
                            "length": obj.bbox_3d.length,
                            "width": obj.bbox_3d.width,
                            "height": obj.bbox_3d.height,
                            "yaw": obj.bbox_3d.yaw,
                        } if obj.bbox_3d else None,
                    }
                    for obj in perception.objects
                ],
                "lanes": [
                    {
                        "points": lane.points.tolist() if hasattr(lane.points, 'tolist') else lane.points,
                        "color": lane.color,
                        "type": lane.type,
                    }
                    for lane in perception.lanes
                ],
                "sensor_data": {
                    "lidar": perception.sensor_data.get('lidar').tolist() if perception.sensor_data.get('lidar') is not None else None,
                    "radar": perception.sensor_data.get('radar'),
                    "foveated_grid": perception.sensor_data.get('foveated_grid'),
                    "semantic_metrics": perception.sensor_data.get('semantic_metrics'),
                } if perception.sensor_data else None,
            } if perception else None,
            "trajectory": {
                "waypoints": [
                    {
                        "x": wp.x,
                        "y": wp.y,
                        "yaw": wp.yaw,
                        "speed": wp.speed,
                    }
                    for wp in trajectory.waypoints
                ],
                "valid": trajectory.valid,
                "planning_time": trajectory.planning_time,
            } if trajectory else None,
            "behavior": {
                "state": behavior.state.value if behavior else "unknown",
                "target_speed": behavior.target_speed if behavior else 0,
                "target_lane": behavior.target_lane if behavior else None,
            } if behavior else None,
            "control": {
                "steer": control.steer if control else 0,
                "throttle": control.throttle if control else 0,
                "brake": control.brake if control else 0,
            } if control else None,
            "sensor_data": sensor_data,
        }

    async def broadcast_loop(self, interval: float = 0.033):
        """Continuous broadcast loop."""
        while self.running:
            if self.latest_data:
                await self.broadcast(self.latest_data)
            await asyncio.sleep(interval)

    async def start(self):
        """Start the WebSocket server."""
        self.running = True
        print(f"Starting WebSocket server on ws://{self.host}:{self.port}")

        async with websockets.serve(self.handler, self.host, self.port):
            await self.broadcast_loop()

    def stop(self):
        """Stop the server."""
        self.running = False


async def main():
    server = SimulationWebSocketServer()
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())