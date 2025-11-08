from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # user_id -> WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        # call_id -> {caller_id, receiver_id}
        self.active_calls: Dict[str, dict] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        """Foydalanuvchini ulash"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections)}")

        # Barcha onlayn foydalanuvchilarga status_update yuborish
        await self.broadcast_status_update(user_id, "online")

    def disconnect(self, user_id: str):
        """Foydalanuvchini uzish"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast_status_update(self, user_id: str, status: str):
        """Barcha foydalanuvchilarga status yangilanishini yuborish"""
        message = {
            "type": "status_update",
            "user_id": user_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }

        # O'zidan boshqa barchaga yuborish
        for uid, connection in list(self.active_connections.items()):
            if uid != user_id:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {uid}: {e}")

    async def send_to_user(self, user_id: str, message: dict):
        """Ma'lum foydalanuvchiga xabar yuborish"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
                return True
            except Exception as e:
                logger.error(f"Error sending to {user_id}: {e}")
                return False
        return False

    async def handle_signaling(self, user_id: str, data: dict):
        """WebRTC signaling xabarlarini qayta ishlash"""
        signal_type = data.get("type")

        if signal_type == "offer":
            # Offer ni receiver ga yuborish
            receiver_id = data.get("receiver_id")
            await self.send_to_user(receiver_id, {
                "type": "offer",
                "caller_id": user_id,
                "call_id": data.get("call_id"),
                "sdp": data.get("sdp"),
                "timestamp": datetime.utcnow().isoformat()
            })

        elif signal_type == "answer":
            # Answer ni caller ga yuborish
            caller_id = data.get("caller_id")
            await self.send_to_user(caller_id, {
                "type": "answer",
                "receiver_id": user_id,
                "call_id": data.get("call_id"),
                "sdp": data.get("sdp"),
                "timestamp": datetime.utcnow().isoformat()
            })

        elif signal_type == "ice":
            # ICE candidate ni ikkinchi tomonga yuborish
            target_id = data.get("target_id")
            await self.send_to_user(target_id, {
                "type": "ice",
                "from": user_id,
                "call_id": data.get("call_id"),
                "candidate": data.get("candidate"),
                "timestamp": datetime.utcnow().isoformat()
            })

    async def start_call(self, caller_id: str, receiver_id: str, call_id: str):
        """Qo'ng'iroqni boshlash - receiver ga signal yuborish"""
        success = await self.send_to_user(receiver_id, {
            "type": "incoming_call",
            "call_id": call_id,
            "caller_id": caller_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        if success:
            self.active_calls[call_id] = {
                "caller_id": caller_id,
                "receiver_id": receiver_id,
                "started_at": datetime.utcnow().isoformat()
            }

        return success

    async def end_call(self, call_id: str):
        """Qo'ng'iroqni tugatish - har ikkala tomonga signal"""
        if call_id in self.active_calls:
            call_info = self.active_calls[call_id]

            # Har ikkala foydalanuvchiga call_ended yuborish
            await self.send_to_user(call_info["caller_id"], {
                "type": "call_ended",
                "call_id": call_id,
                "timestamp": datetime.utcnow().isoformat()
            })

            await self.send_to_user(call_info["receiver_id"], {
                "type": "call_ended",
                "call_id": call_id,
                "timestamp": datetime.utcnow().isoformat()
            })

            del self.active_calls[call_id]

    def is_user_online(self, user_id: str) -> bool:
        """Foydalanuvchi onlayn ekanligini tekshirish"""
        return user_id in self.active_connections

    def get_online_users(self) -> List[str]:
        """Barcha onlayn foydalanuvchilar ro'yxati"""
        return list(self.active_connections.keys())


# Global instance
manager = ConnectionManager()