from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class Session:
    """WebRTC Session"""

    def __init__(self, session_id: str, user1_id: str, user2_id: str):
        self.session_id = session_id
        self.user1_id = user1_id
        self.user2_id = user2_id
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.status = "active"

        # Store signaling messages for reconnect
        self.pending_messages = {
            user1_id: [],
            user2_id: []
        }

        # Connection state
        self.connections = {
            user1_id: True,
            user2_id: True
        }

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()

    def is_expired(self, timeout_minutes: int = 5) -> bool:
        """Check if session expired"""
        return datetime.utcnow() - self.last_activity > timedelta(minutes=timeout_minutes)

    def mark_disconnected(self, user_id: str):
        """Mark user as disconnected"""
        if user_id in self.connections:
            self.connections[user_id] = False

    def mark_connected(self, user_id: str):
        """Mark user as reconnected"""
        if user_id in self.connections:
            self.connections[user_id] = True
            self.update_activity()

    def both_disconnected(self) -> bool:
        """Check if both users disconnected"""
        return not any(self.connections.values())

    def add_pending_message(self, user_id: str, message: dict):
        """Add message for delivery on reconnect"""
        if user_id in self.pending_messages:
            self.pending_messages[user_id].append({
                **message,
                "queued_at": datetime.utcnow().isoformat()
            })

    def get_pending_messages(self, user_id: str) -> list:
        """Get and clear pending messages"""
        if user_id in self.pending_messages:
            messages = self.pending_messages[user_id]
            self.pending_messages[user_id] = []
            return messages
        return []


class SessionManager:
    """Manage WebRTC sessions"""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}  # session_id -> Session
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id

    def create_session(self, session_id: str, user1_id: str, user2_id: str) -> Session:
        """Create new session"""
        session = Session(session_id, user1_id, user2_id)
        self.sessions[session_id] = session
        self.user_sessions[user1_id] = session_id
        self.user_sessions[user2_id] = session_id

        logger.info(f"✅ Session created: {session_id} ({user1_id} <-> {user2_id})")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self.sessions.get(session_id)

    def get_user_session(self, user_id: str) -> Optional[Session]:
        """Get user's active session"""
        session_id = self.user_sessions.get(user_id)
        if session_id:
            return self.sessions.get(session_id)
        return None

    def end_session(self, session_id: str):
        """End session"""
        session = self.sessions.get(session_id)
        if session:
            session.status = "ended"

            # Remove from user mappings
            self.user_sessions.pop(session.user1_id, None)
            self.user_sessions.pop(session.user2_id, None)

            # Remove session after some time (for history)
            # For now, just mark as ended
            logger.info(f"✅ Session ended: {session_id}")

    def handle_disconnect(self, user_id: str) -> Optional[Session]:
        """Handle user disconnect"""
        session = self.get_user_session(user_id)
        if session:
            session.mark_disconnected(user_id)
            logger.info(f"⚠️ User {user_id} disconnected from session {session.session_id}")

            # If both disconnected, end session
            if session.both_disconnected():
                self.end_session(session.session_id)
                logger.info(f"❌ Session {session.session_id} ended (both disconnected)")

            return session
        return None

    def handle_reconnect(self, user_id: str) -> Optional[Session]:
        """Handle user reconnect"""
        session = self.get_user_session(user_id)
        if session and session.status == "active":
            session.mark_connected(user_id)
            logger.info(f"✅ User {user_id} reconnected to session {session.session_id}")
            return session
        return None

    def add_pending_message(self, session_id: str, target_user_id: str, message: dict):
        """Queue message for offline user"""
        session = self.get_session(session_id)
        if session:
            session.add_pending_message(target_user_id, message)

    def get_pending_messages(self, user_id: str) -> list:
        """Get pending messages for reconnected user"""
        session = self.get_user_session(user_id)
        if session:
            return session.get_pending_messages(user_id)
        return []

    def cleanup_expired_sessions(self, timeout_minutes: int = 5):
        """Remove expired sessions"""
        expired = [
            sid for sid, session in self.sessions.items()
            if session.is_expired(timeout_minutes)
        ]

        for session_id in expired:
            self.end_session(session_id)
            del self.sessions[session_id]
            logger.info(f"🧹 Cleaned up expired session: {session_id}")

    def get_session_info(self, session_id: str) -> dict:
        """Get session information"""
        session = self.get_session(session_id)
        if session:
            return {
                "session_id": session.session_id,
                "user1_id": session.user1_id,
                "user2_id": session.user2_id,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "connections": session.connections,
                "pending_messages_count": {
                    user_id: len(msgs)
                    for user_id, msgs in session.pending_messages.items()
                }
            }
        return None


# Global instance
session_manager = SessionManager()