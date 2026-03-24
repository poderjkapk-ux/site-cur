# websocket_manager.py

from typing import List, Dict
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Соединения персонала (все сотрудники получают уведомления о заказах)
        self.staff_connections: List[WebSocket] = []
        # Соединения столиков (ключ - table_id)
        self.table_connections: Dict[int, List[WebSocket]] = {}

    async def connect_staff(self, websocket: WebSocket):
        await websocket.accept()
        self.staff_connections.append(websocket)
        # logger.info("Staff WebSocket connected")

    def disconnect_staff(self, websocket: WebSocket):
        if websocket in self.staff_connections:
            self.staff_connections.remove(websocket)

    async def connect_table(self, websocket: WebSocket, table_id: int):
        await websocket.accept()
        if table_id not in self.table_connections:
            self.table_connections[table_id] = []
        self.table_connections[table_id].append(websocket)
        # logger.info(f"Table #{table_id} WebSocket connected")

    def disconnect_table(self, websocket: WebSocket, table_id: int):
        if table_id in self.table_connections:
            if websocket in self.table_connections[table_id]:
                self.table_connections[table_id].remove(websocket)
            if not self.table_connections[table_id]:
                del self.table_connections[table_id]

    async def broadcast_staff(self, message: dict):
        """Отправляет сообщение всему персоналу"""
        to_remove = []
        for connection in self.staff_connections:
            try:
                await connection.send_json(message)
            except Exception:
                to_remove.append(connection)
        
        for dead_conn in to_remove:
            self.disconnect_staff(dead_conn)

    async def broadcast_table(self, table_id: int, message: dict):
        """Отправляет сообщение конкретному столику"""
        if table_id in self.table_connections:
            to_remove = []
            for connection in self.table_connections[table_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    to_remove.append(connection)
            
            for dead_conn in to_remove:
                self.disconnect_table(dead_conn, table_id)

# Глобальный экземпляр
manager = ConnectionManager()