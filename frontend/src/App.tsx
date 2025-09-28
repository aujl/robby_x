import { useContext, useEffect, useState } from 'react';
import { DriveControl } from '@/components/DriveControl';
import { PanTiltControl } from '@/components/PanTiltControl';
import { TelemetryPanel } from '@/components/TelemetryPanel';
import { useBreakpoint } from '@/hooks/useBreakpoint';
import { ControlContext } from '@/context/ControlContext';
import clsx from 'clsx';

export function App() {
  const layout = useBreakpoint();
  const { connection, queueSize } = useContext(ControlContext);
  const [theme, setTheme] = useState<'dark' | 'light'>(() => (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  return (
    <div
      data-testid="layout-root"
      data-layout={layout}
      className={clsx('min-h-screen bg-slate-100 text-slate-900 transition-colors dark:bg-slate-950 dark:text-slate-50')}
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6">
        <header className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-bold">CamJam Control Console</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Operate the rover with confidence across devices.</p>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <button
              type="button"
              className="btn border border-brand-400/40 bg-brand-500/80 text-white hover:bg-brand-400"
              onClick={() => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))}
              aria-pressed={theme === 'dark'}
            >
              {theme === 'dark' ? 'Switch to Light' : 'Switch to Dark'}
            </button>
            <div className="rounded-lg border border-slate-200/20 bg-slate-900/40 px-3 py-2 text-xs uppercase tracking-wider text-slate-300">
              {connection.status} · {connection.latencyMs ?? '—'} ms · queue {queueSize}
            </div>
          </div>
        </header>

        <main className="grid-layout gap-4">
          <DriveControl />
          <PanTiltControl />
          <TelemetryPanel />
        </main>
      </div>
    </div>
  );
}
