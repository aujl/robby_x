import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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

const contextValue: ControlContextValue = {
  connection: { status: 'connected', latencyMs: 15, lastCommandAt: null, retries: 0 },
  telemetry: {
    ultrasonic: { front: 80, rear: 90, left: 85, right: 75 },
    lineFollow: { left: false, center: false, right: false },
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

describe('PanTiltControl accessibility', () => {
  it('provides slider aria labels and keyboard control', async () => {
    const user = userEvent.setup();
    render(
      <ControlContext.Provider value={contextValue}>
        <PanTiltControl />
      </ControlContext.Provider>
    );

    const panSlider = screen.getByRole('slider', { name: /pan angle/i });
    expect(panSlider).toHaveAttribute('aria-valuemin', '-90');

    await user.tab();
    await user.keyboard('{ArrowRight}');

    await waitFor(() => expect(contextValue.sendPanTiltCommand).toHaveBeenLastCalledWith({ panDeg: 1, tiltDeg: 0 }));
  });

  it('surfaces stream state for assistive tech', () => {
    const value: ControlContextValue = {
      ...contextValue,
      video: { status: 'fallback', src: 'http://still', fallbackSrc: 'http://still', lastError: 'Stream unavailable' },
    };

    render(
      <ControlContext.Provider value={value}>
        <PanTiltControl />
      </ControlContext.Provider>
    );

    const stream = screen.getByTestId('pantilt-stream');
    expect(stream).toHaveAttribute('data-stream-status', 'fallback');
    expect(screen.getByText(/stream unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/displaying cached still image/i)).toBeInTheDocument();
  });
});
