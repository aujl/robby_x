import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PanTiltControl } from '../src/components/PanTiltControl';
import { ControlContext, ControlContextValue } from '../src/context/ControlContext';

const contextValue: ControlContextValue = {
  connection: { status: 'connected', latencyMs: 15, lastCommandAt: null, retries: 0 },
  telemetry: {
    ultrasonic: { front: 80, rear: 90, left: 85, right: 75 },
    lineFollow: { left: false, center: false, right: false },
    heartbeat: { lastSeen: new Date(), stale: false },
  },
  sendDriveCommand: vi.fn(),
  sendPanTiltCommand: vi.fn(),
  sendPreset: vi.fn(),
  queueSize: 0,
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
});
