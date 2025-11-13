"""
Socket.IO Server for Real-Time Audio Call Signaling
Handles WebRTC signaling between peers
"""
import socketio
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)

# Create Socket.IO server with async mode
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# Track active connections and rooms
active_users: Dict[str, str] = {}  # sid -> user_id
call_rooms: Dict[str, Set[str]] = {}  # room_id -> set of sids


@sio.event
async def connect(sid, environ):
    """Handle client connection"""
    logger.info(f"✅ Client connected: {sid}")
    await sio.emit('connected', {'sid': sid}, room=sid)


@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    logger.info(f"❌ Client disconnected: {sid}")

    # Remove from active users
    user_id = active_users.pop(sid, None)

    # Notify other users in the same room
    for room_id, members in list(call_rooms.items()):
        if sid in members:
            members.remove(sid)
            # Notify other member about disconnect
            for member_sid in members:
                await sio.emit('peer_disconnected', {'user_id': user_id}, room=member_sid)
            # Clean up empty rooms
            if len(members) == 0:
                del call_rooms[room_id]


@sio.event
async def join_call(sid, data):
    """User joins a call room"""
    user_id = data.get('user_id')
    room_id = data.get('room_id', 'default-room')

    logger.info(f"👤 User {user_id} ({sid}) joining room {room_id}")

    # Register user
    active_users[sid] = user_id

    # Check room capacity (max 2 users)
    if room_id not in call_rooms:
        call_rooms[room_id] = set()

    if len(call_rooms[room_id]) >= 2:
        await sio.emit('error', {
            'message': 'Call room is full (max 2 users)'
        }, room=sid)
        return

    # Add to room
    call_rooms[room_id].add(sid)
    await sio.enter_room(sid, room_id)

    # Notify user about successful join
    await sio.emit('joined_call', {
        'room_id': room_id,
        'user_id': user_id,
        'members_count': len(call_rooms[room_id])
    }, room=sid)

    # Notify other members
    for member_sid in call_rooms[room_id]:
        if member_sid != sid:
            await sio.emit('peer_joined', {
                'user_id': user_id,
                'sid': sid
            }, room=member_sid)


@sio.event
async def offer(sid, data):
    """Forward WebRTC offer to the target peer"""
    target_sid = data.get('target_sid')
    sdp = data.get('sdp')

    logger.info(f"📤 Offer from {sid} to {target_sid}")

    if target_sid:
        await sio.emit('offer', {
            'sdp': sdp,
            'caller_sid': sid
        }, room=target_sid)
    else:
        logger.error("No target_sid provided for offer")


@sio.event
async def answer(sid, data):
    """Forward WebRTC answer to the caller"""
    caller_sid = data.get('caller_sid')
    sdp = data.get('sdp')

    logger.info(f"📤 Answer from {sid} to {caller_sid}")

    if caller_sid:
        await sio.emit('answer', {
            'sdp': sdp,
            'answerer_sid': sid
        }, room=caller_sid)
    else:
        logger.error("No caller_sid provided for answer")


@sio.event
async def candidate(sid, data):
    """Forward ICE candidate to the target peer"""
    target_sid = data.get('target_sid')
    candidate = data.get('candidate')

    logger.info(f"🧊 ICE candidate from {sid} to {target_sid}")

    if target_sid:
        await sio.emit('candidate', {
            'candidate': candidate,
            'from_sid': sid
        }, room=target_sid)
    else:
        logger.error("No target_sid provided for ICE candidate")


@sio.event
async def leave_call(sid, data):
    """User leaves the call"""
    room_id = data.get('room_id', 'default-room')

    logger.info(f"👋 User {sid} leaving room {room_id}")

    if room_id in call_rooms and sid in call_rooms[room_id]:
        # Notify other members
        for member_sid in call_rooms[room_id]:
            if member_sid != sid:
                await sio.emit('peer_left', {
                    'sid': sid
                }, room=member_sid)

        # Remove from room
        call_rooms[room_id].remove(sid)
        await sio.leave_room(sid, room_id)

        # Clean up empty room
        if len(call_rooms[room_id]) == 0:
            del call_rooms[room_id]


# Create ASGI app
app = socketio.ASGIApp(sio)