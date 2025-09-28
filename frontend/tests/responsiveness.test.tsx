import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { App } from '../src/App';
import { ControlContext, ControlContextValue } from '../src/context/ControlContext';

const contextValue: ControlContextValue = {
  connection: { status: 'connected', latencyMs: 18, lastCommandAt: null, retries: 0 },
  telemetry: {
    ultrasonic: { front: 100, rear: 100, left: 100, right: 100 },
    lineFollow: { left: false, center: false, right: false },
    heartbeat: { lastSeen: new Date(), stale: false },
  },
  sendDriveCommand: vi.fn(),
  sendPanTiltCommand: vi.fn(),
  sendPreset: vi.fn(),
  queueSize: 0,
};

describe('App responsiveness', () => {
  it('updates layout data attribute based on breakpoint', () => {
    const matchMediaMock = vi.spyOn(window, 'matchMedia');
    matchMediaMock.mockImplementation((query: string) => ({
      matches: query.includes('min-width: 1024px'),
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    } as MediaQueryList));

    render(
      <ControlContext.Provider value={contextValue}>
        <App />
      </ControlContext.Provider>
    );

    expect(screen.getByTestId('layout-root')).toHaveAttribute('data-layout', 'desktop');

    matchMediaMock.mockImplementation((query: string) => ({
      matches: query.includes('min-width: 768px') && !query.includes('min-width: 1024px'),
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    } as MediaQueryList));

    render(
      <ControlContext.Provider value={contextValue}>
        <App />
      </ControlContext.Provider>
    );

    expect(screen.getAllByTestId('layout-root')[1]).toHaveAttribute('data-layout', 'tablet');
  });
});
