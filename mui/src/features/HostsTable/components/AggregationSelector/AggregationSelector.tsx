import { useEffect, useRef, useState, type MouseEvent } from 'react';
import styles from './AggregationSelector.module.css';

const SCALES = [
  { value: 300,       label: '5m'  },
  { value: 900,       label: '15m' },
  { value: 3600,      label: '1h'  },
  { value: 86_400,    label: '24h' },
  { value: 604_800,   label: '7d'  },
  { value: 2_592_000, label: '30d' },
];

function AggregationSelector({ defaultValue, onTimeScaleChange }: { onTimeScaleChange: (value: number) => void, defaultValue?: number }) {
  const [timeScale, setTimeScale] = useState<number>(defaultValue ?? SCALES[0]!.value);
  const buttonsContainer = useRef<HTMLDivElement>(null);

  // Configure time scale
  const selectScale = (event: MouseEvent<HTMLButtonElement>) => {
    const newScale = +(event.target as HTMLSpanElement).getAttribute("data-value")!;
    setTimeScale(newScale);
  };

  useEffect(() => {
    if (!buttonsContainer.current) return;

    // Update CSS classes
    buttonsContainer.current.querySelectorAll(`.${styles.selector}`).forEach(e => e.classList.remove(styles.active!));
    buttonsContainer.current.querySelector(`.${styles.selector}[data-value="${timeScale}"]`)?.classList.add(styles.active!);

    onTimeScaleChange(timeScale);
  }, [timeScale, onTimeScaleChange])

  return (
    <div className={styles.selectors} ref={buttonsContainer}>
      {
        SCALES.map((scale, i) => (
          <button key={i} onClick={selectScale} data-value={scale.value} className={styles.selector}>{scale.label}</button>
        ))
      }
    </div>
  );
}

export default AggregationSelector;