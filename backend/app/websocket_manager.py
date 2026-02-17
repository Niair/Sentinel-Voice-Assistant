"""
WebSocket Manager for Real-Time Alert Broadcasting
Handles WebSocket connections and broadcasts alerts to all connected clients
"""

from typing import List
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class AlertWebSocketManager:
    """
    Manages WebSocket connections for real-time alert broadcasting.

    Features:
    - Multiple client connections
    - Automatic reconnection handling
    - Connection status tracking
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_count = 0

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_count += 1
        logger.info(
            f"🟢 WebSocket client connected. Total: {len(self.active_connections)}"
        )

        # Send welcome message
        await websocket.send_json(
            {
                "type": "connection",
                "status": "connected",
                "message": "Alert stream connected. Waiting for events...",
            }
        )

    async def disconnect(self, websocket: WebSocket):
        """Remove disconnected client"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                f"🔴 WebSocket client disconnected. Total: {len(self.active_connections)}"
            )

    async def broadcast_alert(self, alert: dict):
        """
        Broadcast alert to all connected clients

        Args:
            alert: Alert dictionary with event details
        """
        if not self.active_connections:
            return  # No clients connected

        # Add metadata
        alert["type"] = "alert"
        alert["broadcast_time"] = __import__("datetime").datetime.utcnow().isoformat()

        # Send to all connections
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(alert)
            except Exception as e:
                logger.error(f"Failed to send to WebSocket client: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            await self.disconnect(conn)

        logger.info(f"📢 Alert broadcast to {len(self.active_connections)} clients")

    async def broadcast_status(self, status: dict):
        """Broadcast system status update"""
        if not self.active_connections:
            return

        status["type"] = "status"
        status["broadcast_time"] = __import__("datetime").datetime.utcnow().isoformat()

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(status)
            except Exception as e:
                disconnected.append(connection)

        for conn in disconnected:
            await self.disconnect(conn)

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)


# Singleton instance
alert_ws_manager = AlertWebSocketManager()
