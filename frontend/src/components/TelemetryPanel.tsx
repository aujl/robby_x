import { useContext, useEffect, useMemo, useState } from 'react';
import { ControlContext, DiagnosticsEvent } from '@/context/ControlContext';
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

function formatEventDetail(event: DiagnosticsEvent) {
  const entries = Object.entries(event.data)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => `${key.replace(/_/g, ' ')}: ${value}`);
  return entries.length ? entries.join(' · ') : 'No additional data';
}

export function TelemetryPanel() {
  const { telemetry, connection, diagnostics } = useContext(ControlContext);
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

  const timeline = useMemo(() => {
    return diagnostics.events.slice(-6).map((event) => ({
      key: `${event.component}-${event.event}-${event.timestamp.getTime()}`,
      component: event.component,
      event: event.event,
      detail: formatEventDetail(event),
    }));
  }, [diagnostics.events]);

  const cameraStatus = diagnostics.video_stream;
  const panTilt = diagnostics.pan_tilt;

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

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-slate-700/40 bg-slate-900/60 p-3">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">CamJam Timeline</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {timeline.length === 0 && <li className="text-slate-500">No diagnostics events recorded yet.</li>}
            {timeline.map((item) => (
              <li key={item.key} className="rounded-md border border-slate-800/40 bg-slate-900/80 p-2">
                <div className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
                  <span>{item.component}</span>
                  <span>{item.event}</span>
                </div>
                <p className="mt-1 text-slate-200">{item.detail}</p>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-lg border border-slate-700/40 bg-slate-900/60 p-3">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Camera Status</h3>
          <dl className="mt-2 space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <dt className="text-slate-400">Stream</dt>
              <dd
                className={clsx(
                  'rounded-full px-2 py-0.5 text-xs font-medium',
                  cameraStatus.status === 'live'
                    ? 'bg-emerald-500/10 text-emerald-300'
                    : cameraStatus.stale
                      ? 'bg-amber-500/10 text-amber-300'
                      : 'bg-slate-700/60 text-slate-300'
                )}
              >
                {cameraStatus.status}
              </dd>
            </div>
            {cameraStatus.detail && (
              <div className="flex items-start justify-between gap-4">
                <dt className="text-slate-400">Detail</dt>
                <dd className="text-right text-slate-200">{cameraStatus.detail}</dd>
              </div>
            )}
            <div className="flex items-center justify-between">
              <dt className="text-slate-400">Pan / Tilt</dt>
              <dd className="text-slate-200">
                {panTilt.pan_deg.toFixed(0)}° / {panTilt.tilt_deg.toFixed(0)}°
              </dd>
            </div>
            {panTilt.preset && (
              <div className="flex items-center justify-between">
                <dt className="text-slate-400">Preset</dt>
                <dd className="text-slate-200 capitalize">{panTilt.preset}</dd>
              </div>
            )}
            <div className="flex items-center justify-between">
              <dt className="text-slate-400">Health</dt>
              <dd className={panTilt.stale ? 'text-amber-300' : 'text-emerald-300'}>
                {panTilt.stale ? 'Stale' : 'Responsive'}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </section>
  );
}
