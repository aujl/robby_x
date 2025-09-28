import mitt, { Emitter } from 'mitt';
import {
  ControlTelemetry,
  DriveCommandPayload,
  PanTiltCommandPayload,
  ConnectionState,
} from '@/context/ControlContext';

type Events = {
  telemetry: ControlTelemetry;
  connection: ConnectionState;
  queue: number;
};

export type ControlMessage =
  | { type: 'drive/setpoint'; payload: DriveCommandPayload }
  | { type: 'pantilt/command'; payload: PanTiltCommandPayload }
  | { type: 'pantilt/preset'; payload: 'center' | 'sweep' | 'inspect' };

const HEARTBEAT_TIMEOUT = 2000;

export class ControlService {
  private emitter: Emitter<Events>;
  private queue: ControlMessage[] = [];
  private socket: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private retries = 0;
  private lastCommandAt: Date | null = null;

  constructor(private readonly url: string) {
    this.emitter = mitt<Events>();
    this.emitConnection({
      status: 'disconnected',
      latencyMs: null,
      lastCommandAt: null,
      retries: 0,
    });
  }

  on = this.emitter.on;
  off = this.emitter.off;

  connect() {
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    this.emitConnection({
      status: 'connecting',
      latencyMs: null,
      lastCommandAt: this.lastCommandAt,
      retries: this.retries,
    });

    try {
      this.socket = new WebSocket(this.url);
      const socket = this.socket;

      const start = performance.now();
      socket.addEventListener('open', () => {
        this.retries = 0;
        const latency = Math.round(performance.now() - start);
        this.emitConnection({
          status: 'connected',
          latencyMs: latency,
          lastCommandAt: this.lastCommandAt,
          retries: this.retries,
        });
        this.flushQueue();
      });

      socket.addEventListener('message', (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type === 'telemetry/state') {
          const telemetry: ControlTelemetry = {
            ultrasonic: payload.ultrasonic,
            lineFollow: payload.lineFollow,
            heartbeat: {
              lastSeen: new Date(),
              stale: false,
            },
          };
          this.emitter.emit('telemetry', telemetry);
          window.setTimeout(() => {
            this.emitter.emit('telemetry', {
              ...telemetry,
              heartbeat: { lastSeen: telemetry.heartbeat.lastSeen, stale: true },
            });
          }, HEARTBEAT_TIMEOUT);
        } else if (payload.type === 'service/latency') {
          this.emitConnection({
            status: this.socket?.readyState === WebSocket.OPEN ? 'connected' : 'disconnected',
            latencyMs: payload.latencyMs,
            lastCommandAt: this.lastCommandAt,
            retries: this.retries,
          });
        }
      });

      socket.addEventListener('close', () => {
        this.emitConnection({
          status: 'reconnecting',
          latencyMs: null,
          lastCommandAt: this.lastCommandAt,
          retries: this.retries,
        });
        this.scheduleReconnect();
      });

      socket.addEventListener('error', () => {
        socket.close();
      });
    } catch (error) {
      this.scheduleReconnect();
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
    }
    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  send(message: ControlMessage) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
      this.lastCommandAt = new Date();
      this.emitConnection({
        status: 'connected',
        latencyMs: this.socket ? this.socket.bufferedAmount : null,
        lastCommandAt: this.lastCommandAt,
        retries: this.retries,
      });
    } else {
      this.queue.push(message);
      this.emitter.emit('queue', this.queue.length);
      if (!this.socket || this.socket.readyState === WebSocket.CLOSED) {
        this.scheduleReconnect();
      }
    }
  }

  private flushQueue() {
    while (this.queue.length && this.socket?.readyState === WebSocket.OPEN) {
      const message = this.queue.shift();
      if (message) {
        this.socket.send(JSON.stringify(message));
      }
    }
    this.emitter.emit('queue', this.queue.length);
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) {
      return;
    }
    this.retries += 1;
    const delay = Math.min(1000 * 2 ** this.retries, 10000);
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private emitConnection(state: ConnectionState) {
    this.emitter.emit('connection', state);
  }
}
