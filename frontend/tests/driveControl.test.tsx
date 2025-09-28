import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DriveControl } from '../src/components/DriveControl';
import { ControlContext, ControlContextValue } from '../src/context/ControlContext';
import { ReactNode } from 'react';

const defaultDiagnostics = {
  motors: { status: 'unknown', lastEventAt: null, lastCommand: null, history: [] },
  ultrasonic: {},
  line_sensors: {},
  pan_tilt: { status: 'unknown', pan_deg: 0, tilt_deg: 0, preset: null, updatedAt: null, stale: true },
  video_stream: { status: 'idle', detail: null, src: null, stale: true, lastEventAt: null },
  events: [],
};

const baseContext: ControlContextValue = {
  connection: { status: 'connected', latencyMs: 32, lastCommandAt: null, retries: 0 },
  telemetry: {
    ultrasonic: { front: 120, rear: 115, left: 90, right: 92 },
    lineFollow: { left: false, center: true, right: false },
    heartbeat: { lastSeen: new Date(), stale: false },
  },
  diagnostics: defaultDiagnostics,
  sendDriveCommand: vi.fn(),
  sendPanTiltCommand: vi.fn(),
  sendPreset: vi.fn(),
  queueSize: 0,
  video: { status: 'live', src: 'http://stream', fallbackSrc: null, lastError: null },
  startVideoStream: vi.fn(),
  stopVideoStream: vi.fn(),
};

function renderWithContext(node: ReactNode, overrides: Partial<ControlContextValue> = {}) {
  const value: ControlContextValue = { ...baseContext, ...overrides };
  return render(<ControlContext.Provider value={value}>{node}</ControlContext.Provider>);
}

describe('DriveControl', () => {
  it('sends drive command when keyboard input is pressed', async () => {
    const sendDriveCommand = vi.fn();
    const user = userEvent.setup();
    renderWithContext(<DriveControl />, { sendDriveCommand });

    const drivePad = screen.getByLabelText(/drive surface/i);
    drivePad.focus();
    await user.keyboard('w');

    expect(sendDriveCommand).toHaveBeenLastCalledWith({ vx: 1, vy: 0, omega: 0 });
    expect(screen.getByText(/connected/i)).toBeInTheDocument();
    expect(screen.getByText(/last command/i)).toBeInTheDocument();
  });

  it('queues command feedback when disconnected', async () => {
    const sendDriveCommand = vi.fn();
    const user = userEvent.setup();
    renderWithContext(<DriveControl />, {
      sendDriveCommand,
      connection: { status: 'reconnecting', latencyMs: null, lastCommandAt: null, retries: 2 },
      queueSize: 3,
    });

    const drivePad = screen.getByLabelText(/drive surface/i);
    drivePad.focus();
    await user.keyboard('w');

    expect(sendDriveCommand).toHaveBeenCalled();
    expect(screen.getByText(/queued 3 commands/i)).toBeInTheDocument();
    expect(screen.getByText(/reconnecting/i)).toBeInTheDocument();
  });
});
