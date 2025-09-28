import * as Slider from '@radix-ui/react-slider';
import { useContext, useEffect, useMemo, useState } from 'react';
import { ControlContext } from '@/context/ControlContext';
import clsx from 'clsx';

const PAN_RANGE = [-90, 90];
const TILT_RANGE = [-45, 45];

export function PanTiltControl() {
  const { sendPanTiltCommand, sendPreset, video, startVideoStream, stopVideoStream } =
    useContext(ControlContext);
  const [pan, setPan] = useState(0);
  const [tilt, setTilt] = useState(0);
  const [pendingPreset, setPendingPreset] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      sendPanTiltCommand({ panDeg: pan, tiltDeg: tilt });
    }, 120);
    return () => window.clearTimeout(timer);
  }, [pan, tilt, sendPanTiltCommand]);

  useEffect(() => {
    if (video.status === 'idle') {
      startVideoStream();
    }
  }, [video.status, startVideoStream]);

  useEffect(() => () => stopVideoStream(), [stopVideoStream]);

  const angleBadge = useMemo(
    () => (
      <div className="mt-4 flex gap-4 text-sm text-slate-500 dark:text-slate-300">
        <span aria-live="polite">Pan {pan.toFixed(0)}°</span>
        <span aria-live="polite">Tilt {tilt.toFixed(0)}°</span>
      </div>
    ),
    [pan, tilt],
  );

  const streamStatusLabel = useMemo(() => {
    switch (video.status) {
      case 'live':
        return 'Live stream';
      case 'starting':
        return 'Connecting…';
      case 'fallback':
        return 'Fallback still';
      case 'error':
        return 'Stream error';
      default:
        return 'Stream idle';
    }
  }, [video.status]);

  const isLive = video.status === 'live';
  const isStarting = video.status === 'starting';
  const streamButtonLabel = isLive ? 'Stop Stream' : isStarting ? 'Starting…' : 'Start Stream';

  const handlePreset = (preset: 'center' | 'sweep' | 'inspect') => {
    setPendingPreset(preset);
    if (preset === 'center') {
      setPan(0);
      setTilt(0);
    } else if (preset === 'sweep') {
      setPan(60);
      setTilt(0);
    } else {
      setPan(0);
      setTilt(-30);
    }
    sendPreset(preset);
    window.setTimeout(() => setPendingPreset(null), 600);
  };

  return (
    <section className="card" aria-labelledby="pantilt-title">
      <header>
        <h2 id="pantilt-title" className="text-lg font-semibold">
          PanTilt Servos
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Fine-grained orientation control with presets.
        </p>
      </header>

      <div className="mt-4 space-y-6">
        <div>
          <div
            className="relative aspect-video overflow-hidden rounded-lg bg-slate-900"
            data-testid="pantilt-stream"
            data-stream-status={video.status}
          >
            {video.src ? (
              <img
                src={video.src}
                alt={video.status === 'live' ? 'PanTilt live stream' : 'PanTilt fallback still'}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-sm text-slate-500">
                Stream unavailable
              </div>
            )}
            <span className="absolute bottom-2 left-2 rounded-md bg-slate-900/80 px-2 py-1 text-xs font-medium text-slate-100">
              {streamStatusLabel}
            </span>
            {video.lastError && (
              <span className="absolute bottom-2 right-2 rounded-md bg-amber-500/80 px-2 py-1 text-xs font-semibold text-slate-900">
                {video.lastError}
              </span>
            )}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              className="btn border border-brand-400/40 bg-brand-500/90 text-white hover:bg-brand-400 focus-visible:ring-brand-300 disabled:cursor-not-allowed disabled:bg-slate-700"
              onClick={isLive ? stopVideoStream : startVideoStream}
              disabled={isStarting}
            >
              {streamButtonLabel}
            </button>
            {video.fallbackSrc && video.status === 'fallback' && (
              <span className="text-xs text-slate-400">Displaying cached still image.</span>
            )}
          </div>
        </div>

        <div>
          <label htmlFor="pan-slider" className="block text-sm font-medium text-slate-200">
            Pan Angle
          </label>
          <Slider.Root
            id="pan-slider"
            className="relative mt-2 flex h-6 w-full touch-none select-none items-center"
            min={PAN_RANGE[0]}
            max={PAN_RANGE[1]}
            step={1}
            value={[pan]}
            onValueChange={([value]) => setPan(value)}
            aria-label="Pan angle"
          >
            <Slider.Track className="relative h-2 w-full grow rounded-full bg-slate-700">
              <Slider.Range className="absolute h-full rounded-full bg-brand-400" />
            </Slider.Track>
          <Slider.Thumb
            className="block h-5 w-5 rounded-full border border-slate-200 bg-white shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
            aria-valuemin={PAN_RANGE[0]}
            aria-valuemax={PAN_RANGE[1]}
            aria-label="Pan angle"
          />
          </Slider.Root>
        </div>

        <div>
          <label htmlFor="tilt-slider" className="block text-sm font-medium text-slate-200">
            Tilt Angle
          </label>
          <Slider.Root
            id="tilt-slider"
            className="relative mt-2 flex h-6 w-full touch-none select-none items-center"
            min={TILT_RANGE[0]}
            max={TILT_RANGE[1]}
            step={1}
            value={[tilt]}
            onValueChange={([value]) => setTilt(value)}
            aria-label="Tilt angle"
          >
            <Slider.Track className="relative h-2 w-full grow rounded-full bg-slate-700">
              <Slider.Range className="absolute h-full rounded-full bg-brand-400" />
            </Slider.Track>
          <Slider.Thumb
            className="block h-5 w-5 rounded-full border border-slate-200 bg-white shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
            aria-valuemin={TILT_RANGE[0]}
            aria-valuemax={TILT_RANGE[1]}
            aria-label="Tilt angle"
          />
          </Slider.Root>
        </div>

        {angleBadge}

        <div className="flex flex-wrap gap-2">
          {(
            [
              { id: 'center', label: 'Center' },
              { id: 'sweep', label: 'Sweep' },
              { id: 'inspect', label: 'Inspect Down' },
            ] as const
          ).map((preset) => (
            <button
              key={preset.id}
              type="button"
              className={clsx(
                'btn border border-brand-400/40 bg-brand-500/90 text-white hover:bg-brand-400 focus-visible:ring-brand-300',
                pendingPreset === preset.id ? 'animate-pulse' : '',
              )}
              onClick={() => handlePreset(preset.id)}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
