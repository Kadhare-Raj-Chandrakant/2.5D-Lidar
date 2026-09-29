"""WebSocket server to bridge Python simulation to web UI."""
import asyncio
import json
import math
import os
import time
from typing import Set
import numpy as np
import websockets
from websockets.server import WebSocketServerProtocol


class SimulationWebSocketServer:
    """WebSocket server for real-time simulation data streaming."""

    def __init__(self, host: str = None, port: int = 8765):
        self.host = host or os.environ.get("WS_HOST", "localhost")
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.latest_data = None
        self.running = False

    def _serialize_json(self, data: dict) -> str:
        """Safely serialize simulation payload to JSON string."""
        def _fallback_serializer(obj):
            if hasattr(obj, 'tolist'):
                return obj.tolist()
            if hasattr(obj, '__dict__'):
                return {k: v for k, v in obj.__dict__.items() if not k.startswith('_') and not callable(v)}
            return str(obj)

        return json.dumps(data, default=_fallback_serializer)

    async def register(self, websocket: WebSocketServerProtocol):
        """Register new client."""
        self.clients.add(websocket)
        print(f"Client connected. Total: {len(self.clients)}")

        if self.latest_data:
            try:
                await websocket.send(self._serialize_json(self.latest_data))
            except Exception as e:
                print(f"Error sending initial state to client: {e}")

    async def unregister(self, websocket: WebSocketServerProtocol):
        """Unregister client."""
        self.clients.discard(websocket)
        print(f"Client disconnected. Total: {len(self.clients)}")

    async def broadcast(self, data: dict):
        """Broadcast data to all connected clients."""
        if not self.clients:
            return

        try:
            message = self._serialize_json(data)
        except Exception as e:
            print(f"[WebSocket] Serialization error: {e}")
            return

        disconnected = set()

        for client in set(self.clients):  # snapshot to avoid RuntimeError if set mutates during iteration
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

    def update_data(self, vehicle_state, perception, trajectory, behavior, control, sensor_data, traffic_signal="green", active_signal_station=55.0, world_objects=None):
        """Update latest simulation data for broadcasting."""
        # Downsample LiDAR point cloud to representative sample for ultra-low latency 60 FPS streaming
        lidar_data = None
        if perception and perception.sensor_data and perception.sensor_data.get('lidar') is not None:
            raw_lidar = perception.sensor_data.get('lidar')
            if hasattr(raw_lidar, '__getitem__'):
                lidar_data = raw_lidar[::4][:600].tolist() if hasattr(raw_lidar, 'tolist') else raw_lidar[:600]

        world_objs_payload = []
        if world_objects and vehicle_state:
            for obj in world_objects:
                if not obj.bbox_3d:
                    continue
                if abs(obj.bbox_3d.x - vehicle_state.x) > 220.0:
                    continue
                vx = obj.bbox_3d.velocity[0] if obj.bbox_3d.velocity else 0.0
                vy = obj.bbox_3d.velocity[1] if obj.bbox_3d.velocity else 0.0
                speed_val = float(np.hypot(vx, vy))
                if speed_val < 0.25:
                    speed_val = 0.0
                cls_name = getattr(obj.bbox_3d, 'class_name', 'car')
                veh_color = getattr(obj, 'color', getattr(obj.bbox_3d, 'color', None))
                veh_model = getattr(obj, 'model_name', getattr(obj.bbox_3d, 'model_name', None))
                track_id_val = getattr(obj, 'track_id', obj.id)
                world_objs_payload.append({
                    "id": obj.id,
                    "track_id": track_id_val,
                    "class_name": cls_name,
                    "confidence": getattr(obj.bbox_3d, 'confidence', 1.0),
                    "currentSpeed": speed_val,
                    "color": veh_color,
                    "model_name": veh_model,
                    "bbox_3d": {
                        "x": float(obj.bbox_3d.x),
                        "y": float(obj.bbox_3d.y),
                        "z": float(obj.bbox_3d.z),
                        "length": float(obj.bbox_3d.length),
                        "width": float(obj.bbox_3d.width),
                        "height": float(obj.bbox_3d.height),
                        "yaw": float(obj.bbox_3d.yaw),
                        "class_name": cls_name,
                        "color": veh_color,
                        "model_name": veh_model,
                        "track_id": track_id_val,
                        "isCrossing": getattr(obj.bbox_3d, 'isCrossing', False),
                        "jacketColor": getattr(obj.bbox_3d, 'jacketColor', None),
                    }
                })

        self.latest_data = {
            "type": "simulation_data",
            "timestamp": time.time(),
            "traffic_signal": traffic_signal,
            "active_signal_station": active_signal_station,
            "world_objects": world_objs_payload,
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
                        "class_name": getattr(obj.bbox_3d, 'class_name', None) if obj.bbox_3d else None,
                        "confidence": getattr(obj.bbox_3d, 'confidence', 0.9) if obj.bbox_3d else 0,
                        "bbox_3d": {
                            "x": obj.bbox_3d.x,
                            "y": obj.bbox_3d.y,
                            "z": obj.bbox_3d.z,
                            "length": obj.bbox_3d.length,
                            "width": obj.bbox_3d.width,
                            "height": obj.bbox_3d.height,
                            "yaw": obj.bbox_3d.yaw,
                            "class_name": getattr(obj.bbox_3d, 'class_name', 'car'),
                            "isCrossing": getattr(obj.bbox_3d, 'isCrossing', False),
                            "jacketColor": getattr(obj.bbox_3d, 'jacketColor', None),
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
                    "lidar": lidar_data,
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
            "sensor_data": {
                "timestamp": getattr(sensor_data, 'timestamp', time.time()),
                "radar": getattr(sensor_data, 'radar', None),
            } if sensor_data else None,
        }

    async def broadcast_loop(self, interval: float = 0.033):
        """Continuous broadcast loop."""
        while self.running:
            if self.latest_data and self.clients:
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