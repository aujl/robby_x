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
  queueSize: 0,
  sendDriveCommand: () => undefined,
  sendPanTiltCommand: () => undefined,
  sendPreset: () => undefined,
  video: { status: 'idle', src: null, fallbackSrc: null, lastError: null },
  startVideoStream: () => undefined,
  stopVideoStream: () => undefined,
});
