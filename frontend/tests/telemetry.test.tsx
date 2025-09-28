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
    diagnostics: {
      motors: {
        status: 'ok',
        lastEventAt: new Date('2024-01-01T00:00:01Z'),
        lastCommand: {
          left_speed: 0.55,
          right_speed: 0.52,
          duration_s: 1,
          queue_depth: 2,
          source: 'test-suite',
        },
        history: [
          {
            left_speed: 0.55,
            right_speed: 0.52,
            duration_s: 1,
            queue_depth: 2,
            source: 'test-suite',
          },
          {
            left_speed: 0.3,
            right_speed: 0.28,
            duration_s: null,
            queue_depth: 1,
            source: 'operator',
          },
        ],
      },
      ultrasonic: {
        front: [
          { distance_cm: 48, valid: true },
          { distance_cm: 52, valid: false },
        ],
      },
      line_sensors: {
        left: [{ active: false }, { active: true }],
      },
      pan_tilt: {
        status: 'ok',
        pan_deg: 12,
        tilt_deg: -4,
        preset: 'scan',
        updatedAt: new Date('2024-01-01T00:00:02Z'),
        stale: false,
      },
      video_stream: {
        status: 'live',
        detail: 'Nominal bitrate',
        src: 'rtsp://stream',
        stale: false,
        lastEventAt: new Date('2024-01-01T00:00:02Z'),
      },
      events: [
        {
          timestamp: new Date('2024-01-01T00:00:00Z'),
          component: 'motors',
          event: 'drive_command',
          data: { left_speed: 0.55, right_speed: 0.52 },
        },
        {
          timestamp: new Date('2024-01-01T00:00:01Z'),
          component: 'pan_tilt',
          event: 'position_update',
          data: { pan_deg: 10, tilt_deg: -2 },
        },
        {
          timestamp: new Date('2024-01-01T00:00:02Z'),
          component: 'video_stream',
          event: 'status',
          data: { status: 'live', detail: 'Nominal bitrate' },
        },
      ],
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
    expect(screen.getByRole('group', { name: /front distance 55 centimeters/i })).toHaveAttribute(
      'data-level',
      'safe',
    );
    expect(screen.getByRole('group', { name: /rear distance 10 centimeters/i })).toHaveAttribute(
      'data-level',
      'danger',
    );
    expect(screen.getByRole('group', { name: /right distance 35 centimeters/i })).toHaveAttribute(
      'data-level',
      'caution',
    );
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
      </ControlContext.Provider>,
    );

    expect(screen.getByText(/telemetry stale/i)).toBeInTheDocument();
  });

  it('shows diagnostics timeline and camera status details', () => {
    renderTelemetry(<TelemetryPanel />);

    expect(screen.getByText(/camjam timeline/i)).toBeInTheDocument();
    expect(screen.getByText(/left speed: 0.55/i)).toBeInTheDocument();
    expect(screen.getByText(/camera status/i)).toBeInTheDocument();
    expect(screen.getByText(/status: live · detail: Nominal bitrate/i)).toBeInTheDocument();
    expect(screen.getByText(/^Nominal bitrate$/i)).toBeInTheDocument();
    expect(screen.getByText(/Pan \/ Tilt/i)).toBeInTheDocument();
    expect(screen.getByText(/Responsive/i)).toBeInTheDocument();
  });
});
