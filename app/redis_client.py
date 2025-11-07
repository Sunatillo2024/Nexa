import redis
from typing import Optional
from .config import settings
import json


class RedisClient:
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.connect()

    def connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self.client.ping()
            print("✅ Redis connected successfully")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            self.client = None

    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if self.client is None:
            return False
        try:
            self.client.ping()
            return True
        except:
            return False

    def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Check if rate limit is exceeded"""
        if not self.is_connected():
            return True  # Allow if Redis is down

        try:
            current = self.client.get(key)
            if current is None:
                self.client.setex(key, window, 1)
                return True

            if int(current) >= limit:
                return False

            self.client.incr(key)
            return True
        except Exception as e:
            print(f"Rate limit check error: {e}")
            return True
    def set_user_online(self, user_id: str, socket_id: str = None):
        if not self.is_connected():
            return

        try:
            key = f"presence:{user_id}"
            data = {"status": "online", "socket_id": socket_id}
            self.client.setex(key, 300, json.dumps(data))
        except Exception as e:
            print(f"Set user online error: {e}")

    def set_user_offline(self, user_id: str):
        if not self.is_connected():
            return

        try:
            key = f"presence:{user_id}"
            self.client.delete(key)
        except Exception as e:
            print(f"Set user offline error: {e}")

    def get_user_status(self, user_id: str) -> dict:
        if not self.is_connected():
            return {"status": "offline"}

        try:
            key = f"presence:{user_id}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return {"status": "offline"}
        except Exception as e:
            print(f"Get user status error: {e}")
            return {"status": "offline"}

    # Call signaling
    def store_webrtc_signal(self, call_id: str, signal_data: dict, ttl: int = 60):
        if not self.is_connected():
            return False

        try:
            key = f"webrtc:{call_id}"
            self.client.lpush(key, json.dumps(signal_data))
            self.client.expire(key, ttl)
            return True
        except Exception as e:
            print(f"Store WebRTC signal error: {e}")
            return False

    def get_webrtc_signals(self, call_id: str) -> list:
        if not self.is_connected():
            return []

        try:
            key = f"webrtc:{call_id}"
            signals = self.client.lrange(key, 0, -1)
            return [json.loads(s) for s in signals]
        except Exception as e:
            print(f"Get WebRTC signals error: {e}")
            return []

    def close(self):
        if self.client:
            self.client.close()


# Global Redis client instance
redis_client = RedisClient()