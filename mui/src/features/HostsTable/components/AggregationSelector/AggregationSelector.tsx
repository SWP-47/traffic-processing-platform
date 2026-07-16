import { useEffect, useState, type MouseEvent } from 'react';
import styles from './AggregationSelector.module.css';

const SCALES = [
  { value: 300,       label: '5m'  },
  { value: 900,       label: '15m' },
  { value: 3600,      label: '1h'  },
  { value: 86_400,    label: '24h' },
  { value: 604_800,   label: '7d'  },
  { value: 2_592_000, label: '30d' },
];

function AggregationSelector({ onTimeScaleChange }: { onTimeScaleChange: (value: number) => void }) {
  const [timeScale, setTimeScale] = useState<number>(SCALES[0]!.value);

  // Configure time scale
  const selectScale = (event: MouseEvent<HTMLButtonElement>) => {
    const newScale = +(event.target as HTMLSpanElement).getAttribute("data-value")!;
    setTimeScale(newScale);
  };

  useEffect(() => {
    // Update CSS classes
    document.querySelectorAll(`.${styles.selector}`).forEach(e => e.classList.remove(styles.active!));
    document.querySelector(`.${styles.selector}[data-value="${timeScale}"]`)?.classList.add(styles.active!);

    onTimeScaleChange(timeScale);
  }, [timeScale, onTimeScaleChange])

  return (
    <div className={styles.selectors}>
      {
        SCALES.map((scale) => (
          <button onClick={selectScale} data-value={scale.value} className={styles.selector}>{scale.label}</button>
        ))
      }
    </div>
  );
}

export default AggregationSelector;