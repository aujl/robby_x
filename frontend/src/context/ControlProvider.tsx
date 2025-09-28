import { PropsWithChildren } from 'react';
import { ControlContext } from './ControlContext';
import { useControlService } from '@/hooks/useControlService';

export function ControlProvider({ children }: PropsWithChildren) {
  const value = useControlService();
  return <ControlContext.Provider value={value}>{children}</ControlContext.Provider>;
}
