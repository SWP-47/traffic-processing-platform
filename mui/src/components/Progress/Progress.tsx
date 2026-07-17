import styles from './Progress.module.css';
import type { UnitContextValue } from "@/contexts/UnitContext/UnitContext";
import { formatBytesPerSecond } from "@/utils/information";

function Progress(value: number, maxValue: number, unit: UnitContextValue['unit']) {
  const widthPercent = maxValue > 0 ? (value / maxValue) * 100 : 0;

  let formattedValue: string = '';
  if (unit === 'bytes') {
    formattedValue = formatBytesPerSecond(value);
  } else if (unit === 'packets') {
    formattedValue = value.toFixed(0) + ' pkt/s';
  }

  return (
    <div className={styles.progress}>
      <div className={styles.progress_bar}>
        <div className={styles.progress_bar_value} style={{ width: `${widthPercent}%` }}></div>
      </div>
      <p className={styles.progress_value}>{formattedValue}</p>
    </div>
  );
}

export default Progress;