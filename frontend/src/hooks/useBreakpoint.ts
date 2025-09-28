import { useEffect, useState } from 'react';

export type LayoutMode = 'desktop' | 'tablet' | 'phone';

const QUERIES: Record<LayoutMode, string> = {
  desktop: '(min-width: 1024px)',
  tablet: '(min-width: 768px)',
  phone: '(max-width: 767px)',
};

export function useBreakpoint(): LayoutMode {
  const [mode, setMode] = useState<LayoutMode>('phone');

  useEffect(() => {
    const desktop = window.matchMedia(QUERIES.desktop);
    const tablet = window.matchMedia(QUERIES.tablet);

    const update = () => {
      if (desktop.matches) {
        setMode('desktop');
      } else if (tablet.matches) {
        setMode('tablet');
      } else {
        setMode('phone');
      }
    };

    update();

    desktop.addEventListener('change', update);
    tablet.addEventListener('change', update);

    return () => {
      desktop.removeEventListener('change', update);
      tablet.removeEventListener('change', update);
    };
  }, []);

  return mode;
}
