import { createContext } from 'react';

export type ConnectionStatus = 'connected' | 'connecting' | 'reconnecting' | 'disconnected';

export interface ConnectionState {
  status: ConnectionStatus;
  latencyMs: number | null;
  lastCommandAt: Date | null;
  retries: number;
}

export interface UltrasonicTelemetry {
  front: number;
  rear: number;
  left: number;
  right: number;
}

export interface LineFollowTelemetry {
  left: boolean;
  center: boolean;
  right: boolean;
}

export interface HeartbeatTelemetry {
  lastSeen: Date | null;
  stale: boolean;
}

export interface ControlTelemetry {
  ultrasonic: UltrasonicTelemetry;
  lineFollow: LineFollowTelemetry;
  heartbeat: HeartbeatTelemetry;
}

export type HealthStatus = 'ok' | 'stale' | 'unknown';

export interface DiagnosticsEvent {
  timestamp: Date;
  component: string;
  event: string;
  data: Record<string, unknown>;
}

export interface MotorCommandSample {
  left_speed: number;
  right_speed: number;
  duration_s: number | null;
  queue_depth: number | null;
  source: string;
}

export interface DiagnosticsState {
  motors: {
    status: HealthStatus;
    lastEventAt: Date | null;
    lastCommand: MotorCommandSample | null;
    history: MotorCommandSample[];
  };
  ultrasonic: Record<string, Array<{ distance_cm: number; valid: boolean }>>;
  line_sensors: Record<string, Array<{ active: boolean }>>;
  pan_tilt: {
    status: HealthStatus;
    pan_deg: number;
    tilt_deg: number;
    preset: string | null;
    updatedAt: Date | null;
    stale: boolean;
  };
  video_stream: {
    status: string;
    detail: string | null;
    src: string | null;
    stale: boolean;
    lastEventAt: Date | null;
  };
  events: DiagnosticsEvent[];
}

export interface DriveCommandPayload {
  vx: number;
  vy: number;
  omega: number;
}

export interface PanTiltCommandPayload {
  panDeg: number;
  tiltDeg: number;
}

export type VideoStreamStatus = 'idle' | 'starting' | 'live' | 'fallback' | 'error';

export interface VideoStreamState {
  status: VideoStreamStatus;
  src: string | null;
  fallbackSrc: string | null;
  lastError: string | null;
}

export interface ControlContextValue {
  connection: ConnectionState;
  telemetry: ControlTelemetry;
  diagnostics: DiagnosticsState;
  queueSize: number;
  sendDriveCommand: (payload: DriveCommandPayload) => void;
  sendPanTiltCommand: (payload: PanTiltCommandPayload) => void;
  sendPreset: (preset: 'center' | 'sweep' | 'inspect') => void;
  video: VideoStreamState;
  startVideoStream: () => void;
  stopVideoStream: () => void;
}

export const ControlContext = createContext<ControlContextValue>({
  connection: { status: 'disconnected', latencyMs: null, lastCommandAt: null, retries: 0 },
  telemetry: {
    ultrasonic: { front: 0, rear: 0, left: 0, right: 0 },
    lineFollow: { left: false, center: false, right: false },
    heartbeat: { lastSeen: null, stale: true },
  },
  diagnostics: {
    motors: { status: 'unknown', lastEventAt: null, lastCommand: null, history: [] },
    ultrasonic: {},
    line_sensors: {},
    pan_tilt: {
      status: 'unknown',
      pan_deg: 0,
      tilt_deg: 0,
      preset: null,
      updatedAt: null,
      stale: true,
    },
    video_stream: { status: 'idle', detail: null, src: null, stale: true, lastEventAt: null },
    events: [],
  },
  queueSize: 0,
  sendDriveCommand: () => undefined,
  sendPanTiltCommand: () => undefined,
  sendPreset: () => undefined,
  video: { status: 'idle', src: null, fallbackSrc: null, lastError: null },
  startVideoStream: () => undefined,
  stopVideoStream: () => undefined,
});
