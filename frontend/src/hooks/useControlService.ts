import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ControlContextValue,
  ControlTelemetry,
  ConnectionState,
  VideoStreamState,
  DiagnosticsState,
} from '@/context/ControlContext';
import { ControlService } from '@/services/ControlService';

const DEFAULT_TELEMETRY: ControlTelemetry = {
  ultrasonic: { front: 0, rear: 0, left: 0, right: 0 },
  lineFollow: { left: false, center: false, right: false },
  heartbeat: { lastSeen: null, stale: true },
};

const DEFAULT_CONNECTION: ConnectionState = {
  status: 'disconnected',
  latencyMs: null,
  lastCommandAt: null,
  retries: 0,
};

const DEFAULT_DIAGNOSTICS: DiagnosticsState = {
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
};

export function useControlService(): ControlContextValue {
  const [telemetry, setTelemetry] = useState<ControlTelemetry>(DEFAULT_TELEMETRY);
  const [connection, setConnection] = useState<ConnectionState>(DEFAULT_CONNECTION);
  const [queueSize, setQueueSize] = useState<number>(0);
  const [diagnostics] = useState<DiagnosticsState>(DEFAULT_DIAGNOSTICS);
  const streamUrl = useMemo(
    () => import.meta.env.VITE_VIDEO_STREAM_URL ?? 'http://localhost:8081/stream.mjpg',
    [],
  );
  const fallbackUrl = useMemo(() => import.meta.env.VITE_VIDEO_FALLBACK_URL ?? null, []);
  const [video, setVideo] = useState<VideoStreamState>({
    status: 'idle',
    src: null,
    fallbackSrc: fallbackUrl,
    lastError: null,
  });
  const probeRef = useRef<HTMLImageElement | null>(null);

  const service = useMemo(() => {
    const url = import.meta.env.VITE_CONTROL_WS ?? 'ws://localhost:8080/ws';
    return new ControlService(url);
  }, []);

  useEffect(() => {
    service.on('telemetry', setTelemetry);
    service.on('connection', setConnection);
    service.on('queue', setQueueSize);
    service.connect();

    return () => {
      service.off('telemetry', setTelemetry);
      service.off('connection', setConnection);
      service.off('queue', setQueueSize);
      service.disconnect();
    };
  }, [service]);

  const startVideoStream = useCallback(() => {
    setVideo((prev) => ({ ...prev, status: 'starting', lastError: null }));

    const probe = new Image();
    if (probeRef.current) {
      probeRef.current.onload = null;
      probeRef.current.onerror = null;
    }
    probeRef.current = probe;

    const finalize = (
      status: VideoStreamState['status'],
      src: string | null,
      error: string | null,
    ) => {
      if (probeRef.current !== probe) {
        return;
      }
      probe.onload = null;
      probe.onerror = null;
      probeRef.current = null;
      setVideo({ status, src, fallbackSrc: fallbackUrl, lastError: error });
    };

    const cacheBust = `${streamUrl}${streamUrl.includes('?') ? '&' : '?'}cacheBust=${Date.now()}`;
    probe.onload = () => finalize('live', streamUrl, null);
    probe.onerror = () =>
      finalize(fallbackUrl ? 'fallback' : 'error', fallbackUrl, 'Stream unavailable');
    probe.src = cacheBust;
  }, [fallbackUrl, streamUrl]);

  const stopVideoStream = useCallback(() => {
    const probe = probeRef.current;
    if (probe) {
      probe.onload = null;
      probe.onerror = null;
      probeRef.current = null;
    }
    setVideo({ status: 'idle', src: null, fallbackSrc: fallbackUrl, lastError: null });
  }, [fallbackUrl]);

  useEffect(() => () => stopVideoStream(), [stopVideoStream]);

  return {
    connection,
    telemetry,
    diagnostics,
    queueSize,
    sendDriveCommand: (payload) => service.send({ type: 'drive/setpoint', payload }),
    sendPanTiltCommand: (payload) => service.send({ type: 'pantilt/command', payload }),
    sendPreset: (preset) => service.send({ type: 'pantilt/preset', payload: preset }),
    video,
    startVideoStream,
    stopVideoStream,
  };
}
