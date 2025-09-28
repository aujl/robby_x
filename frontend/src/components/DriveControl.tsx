import {
  useContext,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
} from 'react';
import { ControlContext } from '@/context/ControlContext';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';

const KEYBOARD_MAP: Record<string, { vx: number; vy: number; omega: number }> = {
  w: { vx: 1, vy: 0, omega: 0 },
  ArrowUp: { vx: 1, vy: 0, omega: 0 },
  s: { vx: -1, vy: 0, omega: 0 },
  ArrowDown: { vx: -1, vy: 0, omega: 0 },
  a: { vx: 0, vy: -1, omega: 0 },
  ArrowLeft: { vx: 0, vy: -1, omega: 0 },
  d: { vx: 0, vy: 1, omega: 0 },
  ArrowRight: { vx: 0, vy: 1, omega: 0 },
  q: { vx: 0, vy: 0, omega: -1 },
  e: { vx: 0, vy: 0, omega: 1 },
};

export function DriveControl() {
  const { sendDriveCommand, connection, queueSize } = useContext(ControlContext);
  const padRef = useRef<HTMLButtonElement>(null);
  const [vector, setVector] = useState({ vx: 0, vy: 0, omega: 0 });
  const [lastInteraction, setLastInteraction] = useState<Date | null>(null);

  const statusText = useMemo(() => {
    const parts = [connection.status.toUpperCase()];
    if (connection.latencyMs != null) {
      parts.push(`${connection.latencyMs} ms`);
    }
    if (connection.retries > 0) {
      parts.push(`retry ${connection.retries}`);
    }
    return parts.join(' · ');
  }, [connection]);

  const lastCommandText = useMemo(() => {
    const timestamp = connection.lastCommandAt ?? lastInteraction;
    if (!timestamp) {
      return 'Last command: Not yet';
    }
    return `Last command: ${formatDistanceToNow(timestamp, { addSuffix: true })}`;
  }, [connection.lastCommandAt, lastInteraction]);

  const dispatchCommand = (payload: { vx: number; vy: number; omega: number }) => {
    sendDriveCommand(payload);
    setVector(payload);
    setLastInteraction(new Date());
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const mapping = KEYBOARD_MAP[event.key];
    if (!mapping) {
      return;
    }
    event.preventDefault();
    dispatchCommand(mapping);
  };

  const handlePointer = (event: PointerEvent<HTMLButtonElement>) => {
    const rect = padRef.current?.getBoundingClientRect();
    if (!rect) {
      return;
    }
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const normalizedX = (x / rect.width) * 2 - 1;
    const normalizedY = -((y / rect.height) * 2 - 1);
    const payload = {
      vx: Number(normalizedY.toFixed(2)),
      vy: Number(normalizedX.toFixed(2)),
      omega: 0,
    };
    dispatchCommand(payload);
  };

  return (
    <section className="card" aria-labelledby="drive-title">
      <header className="flex items-center justify-between">
        <div>
          <h2 id="drive-title" className="text-lg font-semibold">
            Drive Control
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400" aria-live="polite">
            {statusText}
          </p>
        </div>
        <div className="text-right text-sm text-slate-500 dark:text-slate-400">
          <span>{lastCommandText}</span>
          {queueSize > 0 && <p className="text-amber-500">Queued {queueSize} commands</p>}
        </div>
      </header>

      <button
        ref={padRef}
        type="button"
        aria-label="Drive surface"
        onKeyDown={handleKeyDown}
        onPointerDown={(event) => {
          event.currentTarget.setPointerCapture(event.pointerId);
          handlePointer(event);
        }}
        onPointerMove={(event) => {
          if (event.currentTarget.hasPointerCapture(event.pointerId)) {
            handlePointer(event);
          }
        }}
        onPointerUp={(event) => {
          event.currentTarget.releasePointerCapture(event.pointerId);
          dispatchCommand({ vx: 0, vy: 0, omega: 0 });
        }}
        className={clsx(
          'mt-4 grid h-64 place-items-center rounded-2xl border border-brand-500/40 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-center text-sm text-slate-200 shadow-inner focus:outline-none focus:ring-4 focus:ring-brand-400/50',
          'touch-none',
        )}
      >
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-400">Command Vector</p>
          <p className="font-mono text-lg">
            vx {vector.vx.toFixed(2)} · vy {vector.vy.toFixed(2)} · ω {vector.omega.toFixed(2)}
          </p>
          <p className="mt-2 text-xs text-slate-400">
            Use joystick, keyboard (WASD/Arrows), or touch to drive.
          </p>
        </div>
      </button>
    </section>
  );
}
