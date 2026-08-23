/**
 * Reusable WebSocket client with connection status tracking, auto-reconnect,
 * and graceful fallback to Demo Mode.
 */

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8021/ws/telemetry';

export class VitalWebSocketClient {
  constructor(onMessageCallback, onStatusChangeCallback) {
    this.url = WS_URL;
    this.onMessage = onMessageCallback;
    this.onStatusChange = onStatusChangeCallback;
    this.ws = null;
    this.status = 'DISCONNECTED';
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 3;
    this.reconnectTimer = null;
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.setStatus('CONNECTING');

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.setStatus('CONNECTED');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (this.onMessage) this.onMessage(data);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      this.ws.onerror = () => {
        this.setStatus('ERROR');
      };

      this.ws.onclose = () => {
        this.ws = null;
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          this.setStatus('RECONNECTING');
          this.reconnectTimer = setTimeout(() => this.connect(), 2000 * this.reconnectAttempts);
        } else {
          this.setStatus('DISCONNECTED');
        }
      };
    } catch (err) {
      this.setStatus('ERROR');
    }
  }

  disconnect(silent = false) {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.close();
      this.ws = null;
    }
    if (!silent) {
      this.setStatus('DISCONNECTED');
    }
  }

  setStatus(newStatus) {
    this.status = newStatus;
    if (this.onStatusChange) {
      this.onStatusChange(newStatus);
    }
  }
}
