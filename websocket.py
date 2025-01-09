from fastapi import WebSocket
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, patient_id: int):
        await websocket.accept()
        if patient_id not in self.active_connections:
            self.active_connections[patient_id] = []
        self.active_connections[patient_id].append(websocket)

    def disconnect(self, websocket: WebSocket, patient_id: int):
        if patient_id in self.active_connections:
            try:
                self.active_connections[patient_id].remove(websocket)
                if not self.active_connections[patient_id]:
                    del self.active_connections[patient_id]
            except ValueError:
                logger.warning(f"Attempted to remove non-existent WebSocket for patient {patient_id}")
        else:
            logger.warning(f"Attempted to disconnect non-existent patient {patient_id}")

    async def broadcast(self, message: str, patient_id: int):
        if patient_id in self.active_connections:
            to_remove = []
            for connection in self.active_connections[patient_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Failed to send message to WebSocket: {e}")
                    to_remove.append(connection)
            
            # Clean up any closed connections
            for conn in to_remove:
                self.disconnect(conn, patient_id)

manager = ConnectionManager()
