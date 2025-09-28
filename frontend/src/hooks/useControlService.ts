import { useEffect, useMemo, useState } from 'react';
import { ControlContextValue, ControlTelemetry, ConnectionState } from '@/context/ControlContext';
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

export function useControlService(): ControlContextValue {
  const [telemetry, setTelemetry] = useState<ControlTelemetry>(DEFAULT_TELEMETRY);
  const [connection, setConnection] = useState<ConnectionState>(DEFAULT_CONNECTION);
  const [queueSize, setQueueSize] = useState<number>(0);

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

  return {
    connection,
    telemetry,
    queueSize,
    sendDriveCommand: (payload) => service.send({ type: 'drive/setpoint', payload }),
    sendPanTiltCommand: (payload) => service.send({ type: 'pantilt/command', payload }),
    sendPreset: (preset) => service.send({ type: 'pantilt/preset', payload: preset }),
  };
}
