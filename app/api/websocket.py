from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..services.websocket_manager import ws_manager
from ..services.session_manager import session_manager
from ..services.call_service import CallService
from ..services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)


async def websocket_endpoint(
        websocket: WebSocket,
        user_id: str,
        reconnect: bool = False,
        db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time communication
    URL: ws://localhost:8000/ws/{user_id}?reconnect=true

    Features:
    - WebRTC signaling (offer/answer/ice)
    - Session management
    - Reconnect support
    - Message queuing
    """
    try:
        # Verify user exists
        user = AuthService.get_user_by_id(db, user_id)
        if not user:
            await websocket.close(code=4004, reason="User not found")
            return

        # Check if reconnecting
        is_reconnect = reconnect or ws_manager.get_reconnect_attempts(user_id) > 0

        # Connect user
        await ws_manager.connect(user_id, websocket, is_reconnect=is_reconnect)

        # Handle reconnection
        if is_reconnect:
            await handle_reconnect(user_id, websocket, db)

        logger.info(f"✅ User {user_id} connected (reconnect={is_reconnect})")

        try:
            while True:
                # Receive message
                data = await websocket.receive_json()
                msg_type = data.get("type")

                logger.info(f"📨 Received from {user_id}: {msg_type}")

                # Handle messages
                if msg_type == "start_call":
                    await handle_start_call(user_id, data, db, websocket)

                elif msg_type == "end_call":
                    await handle_end_call(user_id, data, db, websocket)

                elif msg_type == "offer":
                    await handle_offer(user_id, data, websocket)

                elif msg_type == "answer":
                    await handle_answer(user_id, data, websocket)

                elif msg_type == "ice":
                    await handle_ice(user_id, data, websocket)

                elif msg_type == "ping":
                    # Heartbeat
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "get_session_info":
                    # Get current session info
                    session = session_manager.get_user_session(user_id)
                    if session:
                        info = session_manager.get_session_info(session.session_id)
                        await websocket.send_json({
                            "type": "session_info",
                            "data": info
                        })
                    else:
                        await websocket.send_json({
                            "type": "session_info",
                            "data": None
                        })

                else:
                    await websocket.send_json({
                        "success": False,
                        "error": f"Unknown message type: {msg_type}"
                    })

        except WebSocketDisconnect:
            logger.info(f"❌ User {user_id} disconnected")

    except Exception as e:
        logger.error(f"WebSocket error for {user_id}: {e}")

    finally:
        # Handle disconnect
        ws_manager.disconnect(user_id)
        session_manager.handle_disconnect(user_id)
        await ws_manager.broadcast_status(user_id, "offline")


async def handle_reconnect(user_id: str, websocket: WebSocket, db: Session):
    """Handle user reconnection"""
    # Restore session
    session = session_manager.handle_reconnect(user_id)

    if session:
        # Send session info
        await websocket.send_json({
            "type": "reconnected",
            "session": session_manager.get_session_info(session.session_id)
        })

        # Send pending messages
        pending = session_manager.get_pending_messages(user_id)
        if pending:
            await websocket.send_json({
                "type": "pending_messages",
                "messages": pending
            })
            logger.info(f"📬 Sent {len(pending)} pending messages to {user_id}")

        # Notify other user about reconnection
        other_user = session.user2_id if session.user1_id == user_id else session.user1_id
        await ws_manager.send_to_user(other_user, {
            "type": "peer_reconnected",
            "user_id": user_id,
            "session_id": session.session_id
        })


async def handle_start_call(user_id: str, data: dict, db: Session, websocket: WebSocket):
    """Handle start_call RPC - Creates WebRTC session"""
    try:
        receiver_id = data.get("receiver_id")

        if not receiver_id:
            await websocket.send_json({"success": False, "error": "receiver_id required"})
            return

        # Check if receiver exists
        receiver = AuthService.get_user_by_id(db, receiver_id)

        # Check if receiver is online
        if not ws_manager.is_online(receiver_id):
            await websocket.send_json({"success": False, "error": "Receiver is offline"})
            return

        # Create call in database
        call = CallService.create_call(db, user_id, receiver_id)

        # Create WebRTC session
        session = session_manager.create_session(call.id, user_id, receiver_id)

        # Send incoming_call to receiver
        await ws_manager.send_to_user(receiver_id, {
            "type": "incoming_call",
            "session_id": call.id,
            "caller_id": user_id,
            "timestamp": call.started_at.isoformat()
        })

        # Send response to caller
        await websocket.send_json({
            "success": True,
            "data": {
                "session_id": call.id,
                "call_id": call.id,
                "status": "ongoing",
                "started_at": call.started_at.isoformat()
            }
        })

        logger.info(f"✅ Session created: {call.id} ({user_id} -> {receiver_id})")

    except Exception as e:
        logger.error(f"Error in start_call: {e}")
        await websocket.send_json({"success": False, "error": str(e)})


async def handle_end_call(user_id: str, data: dict, db: Session, websocket: WebSocket):
    """Handle end_call RPC - Ends WebRTC session"""
    try:
        call_id = data.get("call_id")
        session_id = data.get("session_id") or call_id

        if not session_id:
            await websocket.send_json({"success": False, "error": "session_id required"})
            return

        # Get call
        call = CallService.get_call(db, session_id)
        if not call:
            await websocket.send_json({"success": False, "error": "Call not found"})
            return

        # Check if user is part of call
        if user_id not in [call.caller_id, call.receiver_id]:
            await websocket.send_json({"success": False, "error": "Not part of this call"})
            return

        # End call in database
        call = CallService.end_call(db, session_id)

        # End session
        session_manager.end_session(session_id)

        # Notify both users
        other_user = call.receiver_id if call.caller_id == user_id else call.caller_id
        await ws_manager.send_to_user(other_user, {
            "type": "call_ended",
            "session_id": session_id
        })

        # Send response
        await websocket.send_json({
            "success": True,
            "data": {
                "session_id": session_id,
                "status": "ended"
            }
        })

        logger.info(f"✅ Session ended: {session_id}")

    except Exception as e:
        logger.error(f"Error in end_call: {e}")
        await websocket.send_json({"success": False, "error": str(e)})


async def handle_offer(user_id: str, data: dict, websocket: WebSocket):
    """Handle WebRTC offer"""
    receiver_id = data.get("receiver_id")
    session_id = data.get("session_id") or data.get("call_id")
    sdp = data.get("sdp")

    if not all([receiver_id, session_id, sdp]):
        await websocket.send_json({
            "success": False,
            "error": "receiver_id, session_id and sdp required"
        })
        return

    # Get session
    session = session_manager.get_session(session_id)
    if not session:
        await websocket.send_json({"success": False, "error": "Session not found"})
        return

    session.update_activity()

    # Forward offer to receiver
    message = {
        "type": "offer",
        "caller_id": user_id,
        "session_id": session_id,
        "sdp": sdp
    }

    if ws_manager.is_online(receiver_id):
        await ws_manager.send_to_user(receiver_id, message)
        await websocket.send_json({"success": True})
    else:
        # Queue message for when user reconnects
        session_manager.add_pending_message(session_id, receiver_id, message)
        await websocket.send_json({"success": True, "queued": True})

    logger.info(f"📤 Offer: {user_id} -> {receiver_id} (session: {session_id})")


async def handle_answer(user_id: str, data: dict, websocket: WebSocket):
    """Handle WebRTC answer"""
    caller_id = data.get("caller_id")
    session_id = data.get("session_id") or data.get("call_id")
    sdp = data.get("sdp")

    if not all([caller_id, session_id, sdp]):
        await websocket.send_json({
            "success": False,
            "error": "caller_id, session_id and sdp required"
        })
        return

    # Get session
    session = session_manager.get_session(session_id)
    if not session:
        await websocket.send_json({"success": False, "error": "Session not found"})
        return

    session.update_activity()

    # Forward answer to caller
    message = {
        "type": "answer",
        "receiver_id": user_id,
        "session_id": session_id,
        "sdp": sdp
    }

    if ws_manager.is_online(caller_id):
        await ws_manager.send_to_user(caller_id, message)
        await websocket.send_json({"success": True})
    else:
        # Queue message
        session_manager.add_pending_message(session_id, caller_id, message)
        await websocket.send_json({"success": True, "queued": True})

    logger.info(f"📤 Answer: {user_id} -> {caller_id} (session: {session_id})")


async def handle_ice(user_id: str, data: dict, websocket: WebSocket):
    """Handle ICE candidate"""
    target_id = data.get("target_id")
    session_id = data.get("session_id") or data.get("call_id")
    candidate = data.get("candidate")

    if not all([target_id, session_id, candidate]):
        await websocket.send_json({
            "success": False,
            "error": "target_id, session_id and candidate required"
        })
        return

    # Get session
    session = session_manager.get_session(session_id)
    if session:
        session.update_activity()

    # Forward ICE candidate
    message = {
        "type": "ice",
        "from": user_id,
        "session_id": session_id,
        "candidate": candidate
    }

    if ws_manager.is_online(target_id):
        await ws_manager.send_to_user(target_id, message)
        await websocket.send_json({"success": True})
    else:
        # Queue message
        if session:
            session_manager.add_pending_message(session_id, target_id, message)
        await websocket.send_json({"success": True, "queued": True})

    logger.info(f"🧊 ICE: {user_id} -> {target_id} (session: {session_id})")