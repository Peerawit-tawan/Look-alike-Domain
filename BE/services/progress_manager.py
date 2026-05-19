import threading
import asyncio
from fastapi import WebSocket, WebSocketDisconnect

class ProgressManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._progress = {
            "percent": 0.0,
            "running": False,
            "status": "Idle",
        }
        self.cancel_flag = False

    def reset(self, status="Starting..."):
        with self._lock:
            self._progress["percent"] = 0.0
            self._progress["running"] = True
            self._progress["status"] = status
        self.cancel_flag = False

    def set_status(self, status: str):
        with self._lock:
            self._progress["status"] = status

    def stop(self):
        with self._lock:
            self._progress["running"] = False

    def update(self, checked: int, total: int):
        with self._lock:
            new_percent = int((checked / total) * 100) if total > 0 else 0
            # ป้องกันเปอร์เซ็นต์ลดลง (Monotonic Progress)
            if new_percent > self._progress["percent"]:
                self._progress["percent"] = new_percent
            elif checked >= total and total > 0:
                self._progress["percent"] = 100.0

    def get_snapshot(self):
        with self._lock:
            return dict(self._progress)

    async def websocket_handler(self, ws: WebSocket):
        await ws.accept()
        try:
            while True:
                snapshot = self.get_snapshot()
                await ws.send_json(snapshot)
                await asyncio.sleep(0.5)
                try:
                    await asyncio.wait_for(ws.receive_text(), timeout=0.01)
                except asyncio.TimeoutError:
                    pass
        except (WebSocketDisconnect, ConnectionResetError):
            pass

progress_manager = ProgressManager()
