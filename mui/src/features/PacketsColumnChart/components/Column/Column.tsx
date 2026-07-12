import type { ColumnRenderData } from "../ColumnChart/ColumnChart";
import styles from './Column.module.css';

function Column({ value, label, formatter, heightFactor }: ColumnRenderData) {
  return (
    <div className={styles.column}>
      <div className={styles.data}>
        <div
          className={styles.data_representation}
          style={{ height: `${heightFactor * 100}%` }}>
        </div>
      </div>
      <p className={styles.value}>{formatter ? formatter(value) : value}</p>
      <p className={styles.label}>{label}</p>
    </div>
  );
}

export default Column;