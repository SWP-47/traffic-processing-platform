import type { ColumnData } from "./types";
import Column from "./components/Column/Column";
import styles from "./ColumnChart.module.css";

export type ColumnRenderData = ColumnData & {
  heightFactor: number
}

function ColumnChart({ title, data }: { title: string, data: ColumnData[] }) {
  const maxValue = Math.max(...data.map(d => d.value));

  return (
    <div className={`${styles.chart} card`}>
      <h1 className={styles.title}>{title}</h1>
      <div className={styles.columns}>
        {
          data.map((d, i) => (
            <Column
              key={i}
              value={d.value}
              label={d.label}
              legend={d.legend}
              heightFactor={maxValue > 0 ? d.value / maxValue : 0}
            />
          ))
        }
      </div>
    </div>
  );
}

export default ColumnChart;