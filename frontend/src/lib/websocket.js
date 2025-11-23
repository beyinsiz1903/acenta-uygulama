/**
 * WebSocket Client for Real-time Updates
 */
import { io } from 'socket.io-client';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const WEBSOCKET_URL = BACKEND_URL.replace('/api', '/ws');

class WebSocketManager {
  constructor() {
    this.socket = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    if (this.socket?.connected) {
      console.log('WebSocket already connected');
      return this.socket;
    }

    console.log('🔌 Connecting to WebSocket:', WEBSOCKET_URL);

    this.socket = io(WEBSOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: this.maxReconnectAttempts,
    });

    this.setupEventHandlers();
    return this.socket;
  }

  setupEventHandlers() {
    this.socket.on('connect', () => {
      console.log('✅ WebSocket connected');
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', (reason) => {
      console.log('❌ WebSocket disconnected:', reason);
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;

      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('Max reconnection attempts reached');
      }
    });

    this.socket.on('connection_established', (data) => {
      console.log('Connection established:', data);
    });

    // Dashboard updates
    this.socket.on('dashboard_update', (data) => {
      this.emit('dashboard_update', data);
    });

    // Booking updates
    this.socket.on('booking_update', (data) => {
      this.emit('booking_update', data);
    });

    // Room status updates
    this.socket.on('room_status_update', (data) => {
      this.emit('room_status_update', data);
    });

    // Notifications
    this.socket.on('notification', (data) => {
      this.emit('notification', data);
    });

    // Pong response
    this.socket.on('pong', (data) => {
      console.log('Pong received:', data);
    });
  }

  joinRoom(room) {
    if (!this.socket?.connected) {
      console.warn('Cannot join room: not connected');
      return;
    }

    console.log(`📍 Joining room: ${room}`);
    this.socket.emit('join_room', { room });
  }

  leaveRoom(room) {
    if (!this.socket?.connected) return;

    console.log(`📍 Leaving room: ${room}`);
    this.socket.emit('leave_room', { room });
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.listeners.get(event);
      if (callbacks) {
        const index = callbacks.indexOf(callback);
        if (index > -1) {
          callbacks.splice(index, 1);
        }
      }
    };
  }

  emit(event, data) {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach(callback => callback(data));
    }
  }

  ping() {
    if (this.socket?.connected) {
      this.socket.emit('ping');
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.listeners.clear();
      console.log('WebSocket disconnected manually');
    }
  }

  isConnected() {
    return this.socket?.connected || false;
  }
}

// Export singleton instance
export const websocket = new WebSocketManager();

// React hook for WebSocket
export function useWebSocket(room = null) {
  const [isConnected, setIsConnected] = React.useState(false);

  React.useEffect(() => {
    const socket = websocket.connect();
    
    const checkConnection = () => {
      setIsConnected(websocket.isConnected());
    };

    socket.on('connect', checkConnection);
    socket.on('disconnect', checkConnection);

    checkConnection();

    if (room) {
      websocket.joinRoom(room);
    }

    return () => {
      if (room) {
        websocket.leaveRoom(room);
      }
      socket.off('connect', checkConnection);
      socket.off('disconnect', checkConnection);
    };
  }, [room]);

  return {
    isConnected,
    socket: websocket,
    joinRoom: websocket.joinRoom.bind(websocket),
    leaveRoom: websocket.leaveRoom.bind(websocket),
    on: websocket.on.bind(websocket),
    emit: websocket.emit.bind(websocket),
  };
}

export default websocket;
