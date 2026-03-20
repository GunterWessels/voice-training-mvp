FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# Single worker — WebSocket state is in-process; Railway injects $PORT
# --ws-ping-interval 20: send WS ping every 20s to keep Railway proxy from dropping idle connections
# --ws-ping-timeout 10: close if no pong within 10s (dead connection)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --ws-ping-interval 20 --ws-ping-timeout 10"]
