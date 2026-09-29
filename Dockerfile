# Headless telemetry backend for the simulation stack.
# Serves the WebSocket feed on :8765; Caddy terminates TLS in front of it.
FROM python:3.11-slim

# libsdl2  -> pygame (imported at module scope by src/visualization/visualizer.py,
#            even in headless mode, because main.py imports Visualizer unconditionally)
# libgl1 / libglib2.0-0 -> OpenCV shared library dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsdl2-2.0-0 \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV WS_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

EXPOSE 8765

CMD ["python", "main.py", "--headless"]
