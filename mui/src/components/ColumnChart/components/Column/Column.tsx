import type { ColumnRenderData } from "../../ColumnChart";
import styles from './Column.module.css';

function Column({ value, label, legend, heightFactor }: ColumnRenderData) {
  return (
    <div className={styles.column}>
      <div className={styles.data}>
        <p className={styles.value}>{label ?? value}</p>
        <div
          className={styles.data_representation}
          style={{ height: `${heightFactor * 100}%` }}>
        </div>
      </div>
      <p className={styles.name}>{legend}</p>
    </div>
  );
}

export default Column;