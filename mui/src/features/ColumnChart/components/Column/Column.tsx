import type { ColumnData } from "../../types";
import styles from './Column.module.css';

function Column({ value, height, column_name: name }: ColumnData) {
  return (
    <div className={styles.column}>
      <div className={styles.data}>
        <p className={styles.value}>{value}</p>
        <div
          className={styles.data_representation}
          style={{ height: `${height * 100}%` }}>
        </div>
      </div>
      <p className={styles.name}>{name}</p>
    </div>
  );
}

export default Column;