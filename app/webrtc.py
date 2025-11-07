import uuid
from typing import Dict

class WebRTCManager:
    def __init__(self):
        self.active_channels: Dict[str, Dict] = {}

    def create_channel(self, caller_id: str, receiver_id: str) -> str:
        channel_id = f"channel_{uuid.uuid4().hex[:8]}"
        self.active_channels[channel_id] = {
            "caller_id": caller_id,
            "receiver_id": receiver_id,
            "created_at": uuid.uuid4().int
        }
        return channel_id

    def close_channel(self, channel_id: str):
        if channel_id in self.active_channels:
            del self.active_channels[channel_id]

    def get_channel_info(self, channel_id: str) -> Dict:
        return self.active_channels.get(channel_id)

webrtc_manager = WebRTCManager()