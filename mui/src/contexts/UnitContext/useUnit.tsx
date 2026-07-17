
import { useContext } from 'react';
import { UnitContext, type UnitContextValue } from './UnitContext';

export function useUnit(): UnitContextValue {
  const ctx = useContext(UnitContext);
  if (!ctx) {
    throw new Error('useUnit must be used within <UnitProvider>');
  }
  return ctx;
}