import { useContext, useEffect, useMemo, useState } from 'react';
import { ControlContext } from '@/context/ControlContext';
import clsx from 'clsx';

const DISTANCE_LEVELS = {
  danger: { threshold: 20, label: 'Danger' },
  caution: { threshold: 40, label: 'Caution' },
};

type LineHistory = {
  left: boolean[];
  center: boolean[];
  right: boolean[];
};

function classifyDistance(distance: number): 'danger' | 'caution' | 'safe' {
  if (distance < DISTANCE_LEVELS.danger.threshold) {
    return 'danger';
  }
  if (distance < DISTANCE_LEVELS.caution.threshold) {
    return 'caution';
  }
  return 'safe';
}

export function TelemetryPanel() {
  const { telemetry, connection } = useContext(ControlContext);
  const [history, setHistory] = useState<LineHistory>({ left: [], center: [], right: [] });

  useEffect(() => {
    setHistory((prev) => {
      const next: LineHistory = {
        left: [...prev.left, telemetry.lineFollow.left].slice(-10),
        center: [...prev.center, telemetry.lineFollow.center].slice(-10),
        right: [...prev.right, telemetry.lineFollow.right].slice(-10),
      };
      return next;
    });
  }, [telemetry.lineFollow]);

  const ultrasonicEntries = useMemo(
    () =>
      Object.entries(telemetry.ultrasonic).map(([position, distance]) => {
        const level = classifyDistance(distance);
        return { position, distance, level };
      }),
    [telemetry.ultrasonic]
  );

  return (
    <section className="card" aria-labelledby="telemetry-title">
      <header className="flex items-center justify-between">
        <div>
          <h2 id="telemetry-title" className="text-lg font-semibold">
            Telemetry
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">Sensor awareness and health.</p>
        </div>
        <div className="text-right text-xs text-slate-500 dark:text-slate-400">
          <p aria-live="polite">Latency {connection.latencyMs ?? '—'} ms</p>
          <p aria-live="polite">Heartbeat {telemetry.heartbeat.stale ? 'Stale' : 'Live'}</p>
        </div>
      </header>

      {telemetry.heartbeat.stale && (
        <div className="mt-2 rounded-md border border-amber-400 bg-amber-500/10 p-2 text-sm text-amber-400">
          Telemetry stale – awaiting updates
        </div>
      )}

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Ultrasonic</h3>
          <div className="mt-2 grid gap-2">
            {ultrasonicEntries.map(({ position, distance, level }) => (
              <div
                key={position}
                className={clsx(
                  'flex items-center justify-between rounded-lg border p-2 text-sm',
                  level === 'danger' && 'border-red-400/40 bg-red-500/10 text-red-300',
                  level === 'caution' && 'border-amber-400/40 bg-amber-500/10 text-amber-200',
                  level === 'safe' && 'border-emerald-400/40 bg-emerald-500/10 text-emerald-200'
                )}
                data-level={level}
              >
                <span className="capitalize">{position}</span>
                <span>{distance.toFixed(0)} cm</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Line Follow</h3>
          <div className="mt-2 space-y-2">
            {(['left', 'center', 'right'] as const).map((pos) => (
              <div key={pos} className="rounded-lg border border-slate-700/40 bg-slate-900/60 p-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="capitalize text-slate-300">{pos}</span>
                  <span className={telemetry.lineFollow[pos] ? 'text-brand-300' : 'text-slate-500'}>
                    {telemetry.lineFollow[pos] ? 'ON' : 'OFF'}
                  </span>
                </div>
                <div className="mt-2 flex h-6 items-end gap-1" aria-hidden>
                  {history[pos].map((value, index) => (
                    <span
                      key={index}
                      className={clsx(
                        'h-full w-2 rounded-sm transition-all duration-150',
                        value ? 'bg-brand-400' : 'bg-slate-700'
                      )}
                      style={{ height: value ? '100%' : '40%' }}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
