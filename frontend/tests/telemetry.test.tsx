import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { TelemetryPanel } from '../src/components/TelemetryPanel';
import { ControlContext, ControlContextValue } from '../src/context/ControlContext';
import { ReactNode } from 'react';

vi.useFakeTimers();

let contextValue: ControlContextValue;

function renderTelemetry(node: ReactNode) {
  return render(<ControlContext.Provider value={contextValue}>{node}</ControlContext.Provider>);
}

beforeEach(() => {
  contextValue = {
    connection: { status: 'connected', latencyMs: 20, lastCommandAt: null, retries: 0 },
    telemetry: {
      ultrasonic: { front: 55, rear: 10, left: 80, right: 35 },
      lineFollow: { left: false, center: true, right: true },
      heartbeat: { lastSeen: new Date(), stale: false },
    },
    sendDriveCommand: vi.fn(),
    sendPanTiltCommand: vi.fn(),
    sendPreset: vi.fn(),
    queueSize: 0,
    video: { status: 'live', src: 'http://stream', fallbackSrc: null, lastError: null },
    startVideoStream: vi.fn(),
    stopVideoStream: vi.fn(),
  };
});

describe('TelemetryPanel', () => {
  it('renders ultrasonic thresholds with appropriate classes', () => {
    renderTelemetry(<TelemetryPanel />);
    expect(screen.getByText(/front/).closest('div')).toHaveAttribute('data-level', 'safe');
    expect(screen.getByText(/rear/).closest('div')).toHaveAttribute('data-level', 'danger');
    expect(screen.getByText(/right/).closest('div')).toHaveAttribute('data-level', 'caution');
  });

  it('marks telemetry stale when no updates arrive within 2 seconds', () => {
    const { rerender } = renderTelemetry(<TelemetryPanel />);

    act(() => {
      vi.advanceTimersByTime(2100);
    });

    contextValue = {
      ...contextValue,
      telemetry: {
        ...contextValue.telemetry,
        heartbeat: { ...contextValue.telemetry.heartbeat, stale: true },
      },
    };

    rerender(
      <ControlContext.Provider value={contextValue}>
        <TelemetryPanel />
      </ControlContext.Provider>
    );

    expect(screen.getByText(/telemetry stale/i)).toBeInTheDocument();
  });
});
