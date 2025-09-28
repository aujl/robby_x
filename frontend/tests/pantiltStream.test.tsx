import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PanTiltControl } from '../src/components/PanTiltControl';
import { ControlContext, ControlContextValue } from '../src/context/ControlContext';

const defaultDiagnostics = {
  motors: { status: 'unknown', lastEventAt: null, lastCommand: null, history: [] },
  ultrasonic: {},
  line_sensors: {},
  pan_tilt: { status: 'unknown', pan_deg: 0, tilt_deg: 0, preset: null, updatedAt: null, stale: true },
  video_stream: { status: 'idle', detail: null, src: null, stale: true, lastEventAt: null },
  events: [],
};

const baseContext: ControlContextValue = {
  connection: { status: 'connected', latencyMs: 20, lastCommandAt: null, retries: 0 },
  telemetry: {
    ultrasonic: { front: 90, rear: 90, left: 90, right: 90 },
    lineFollow: { left: false, center: true, right: false },
    heartbeat: { lastSeen: new Date(), stale: false },
  },
  diagnostics: defaultDiagnostics,
  queueSize: 0,
  sendDriveCommand: vi.fn(),
  sendPanTiltCommand: vi.fn(),
  sendPreset: vi.fn(),
  video: { status: 'idle', src: null, fallbackSrc: null, lastError: null },
  startVideoStream: vi.fn(),
  stopVideoStream: vi.fn(),
};

function renderWithValue(value: ControlContextValue) {
  return render(
    <ControlContext.Provider value={value}>
      <PanTiltControl />
    </ControlContext.Provider>
  );
}

describe('PanTiltControl stream', () => {
  it('auto-starts the stream when idle', () => {
    const startVideoStream = vi.fn();
    const value: ControlContextValue = { ...baseContext, startVideoStream };
    renderWithValue(value);
    expect(startVideoStream).toHaveBeenCalledTimes(1);
  });

  it('allows stopping the stream when live', async () => {
    const stopVideoStream = vi.fn();
    const user = userEvent.setup();
    const value: ControlContextValue = {
      ...baseContext,
      video: { status: 'live', src: 'http://stream', fallbackSrc: null, lastError: null },
      stopVideoStream,
    };

    renderWithValue(value);

    const toggle = screen.getByRole('button', { name: /stop stream/i });
    await user.click(toggle);

    expect(stopVideoStream).toHaveBeenCalledTimes(1);
  });
});
