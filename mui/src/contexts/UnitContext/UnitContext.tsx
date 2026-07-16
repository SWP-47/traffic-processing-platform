import { createContext } from 'react';

export type TrafficUnit = 'packets' | 'bytes';

export interface UnitContextValue {
  unit: TrafficUnit;
  setUnit: (unit: TrafficUnit) => void;
  toggleUnit: () => void;
}

export const UnitContext = createContext<UnitContextValue | null>(null);