import { useState, useEffect, type ReactNode } from 'react';
import { UnitContext, type TrafficUnit } from './UnitContext';

const STORAGE_KEY = 'traffic-unit-preference';

export function UnitProvider({ children }: { children: ReactNode }) {
  const [unit, setUnitState] = useState<TrafficUnit>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === 'bytes' ? 'bytes' : 'packets';
  });

  const setUnit = (newUnit: TrafficUnit) => {
    setUnitState(newUnit);
    localStorage.setItem(STORAGE_KEY, newUnit);
  };

  const toggleUnit = () => {
    setUnit(unit === 'packets' ? 'bytes' : 'packets');
  };

  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY && (e.newValue === 'packets' || e.newValue === 'bytes')) {
        setUnitState(e.newValue);
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  return (
    <UnitContext.Provider value={{ unit, setUnit, toggleUnit }}>
      {children}
    </UnitContext.Provider>
  );
}