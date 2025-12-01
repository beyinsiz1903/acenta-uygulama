"""
WebSocket Server for Real-time Updates
Provides live dashboard metrics, booking updates, and notifications
"""
import socketio
import logging
from datetime import datetime
from typing import Dict, Any, Set

logger = logging.getLogger(__name__)

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# Track connected clients by room
connected_clients: Dict[str, Set[str]] = {
    'dashboard': set(),
    'pms': set(),
    'notifications': set(),
    'kitchen': set()
}

@sio.event
async def connect(sid, environ, auth):
    """Handle client connection"""
    logger.info(f"Client connected: {sid}")
    await sio.emit('connection_established', {
        'sid': sid,
        'timestamp': datetime.utcnow().isoformat()
    }, to=sid)

@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {sid}")
    # Remove from all rooms
    for room, clients in connected_clients.items():
        if sid in clients:
            clients.remove(sid)
            logger.info(f"Removed {sid} from room: {room}")

@sio.event
async def join_room(sid, data):
    """Join a specific room for targeted updates"""
    room = data.get('room', 'general')
    await sio.enter_room(sid, room)
    
    if room in connected_clients:
        connected_clients[room].add(sid)
    
    logger.info(f"Client {sid} joined room: {room}")
    await sio.emit('room_joined', {
        'room': room,
        'message': f'Successfully joined {room}'
    }, to=sid)

@sio.event
async def leave_room(sid, data):
    """Leave a specific room"""
    room = data.get('room', 'general')
    await sio.leave_room(sid, room)
    
    if room in connected_clients and sid in connected_clients[room]:
        connected_clients[room].remove(sid)
    
    logger.info(f"Client {sid} left room: {room}")

# Broadcast functions
async def broadcast_dashboard_update(metrics: Dict[str, Any]):
    """Broadcast dashboard metrics update to all dashboard subscribers"""
    try:
        await sio.emit('dashboard_update', {
            'metrics': metrics,
            'timestamp': datetime.utcnow().isoformat()
        }, room='dashboard')
        logger.debug("Dashboard update broadcasted")
    except Exception as e:
        logger.error(f"Failed to broadcast dashboard update: {e}")

async def broadcast_booking_update(booking_data: Dict[str, Any], event_type: str = 'update'):
    """
    Broadcast booking update
    
    Args:
        booking_data: Booking information
        event_type: 'create', 'update', 'checkin', 'checkout', 'cancel'
    """
    try:
        await sio.emit('booking_update', {
            'event_type': event_type,
            'booking': booking_data,
            'timestamp': datetime.utcnow().isoformat()
        }, room='pms')
        logger.debug(f"Booking {event_type} broadcasted")
    except Exception as e:
        logger.error(f"Failed to broadcast booking update: {e}")

async def broadcast_notification(user_id: str, notification: Dict[str, Any]):
    """Send notification to specific user"""
    try:
        # In a production setup, you'd maintain a mapping of user_id to sid
        await sio.emit('notification', {
            'notification': notification,
            'timestamp': datetime.utcnow().isoformat()
        }, room='notifications')
        logger.debug(f"Notification sent to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

async def broadcast_room_status_update(room_id: str, status: str):
    """Broadcast room status change"""
    try:
        await sio.emit('room_status_update', {
            'room_id': room_id,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }, room='pms')
        logger.debug(f"Room status update broadcasted: {room_id} -> {status}")
    except Exception as e:
        logger.error(f"Failed to broadcast room status update: {e}")


async def broadcast_kitchen_orders(tenant_id: str, orders: Any):
    """Broadcast kitchen display orders"""
    try:
        await sio.emit('kitchen_orders', {
            'tenant_id': tenant_id,
            'orders': orders,
            'timestamp': datetime.utcnow().isoformat()
        }, room='kitchen')
        logger.debug("Kitchen orders broadcasted")
    except Exception as e:
        logger.error(f"Failed to broadcast kitchen orders: {e}")

async def get_connected_clients_count() -> Dict[str, int]:
    """Get count of connected clients per room"""
    return {
        room: len(clients)
        for room, clients in connected_clients.items()
    }

# Health check
@sio.event
async def ping(sid):
    """Ping/pong for connection health check"""
    await sio.emit('pong', {
        'timestamp': datetime.utcnow().isoformat()
    }, to=sid)

# Create ASGI app
socket_app = socketio.ASGIApp(
    sio,
    socketio_path='socket.io'
)
