import Column from "../Column/Column";
import styles from "./ColumnChart.module.css";

export interface ColumnData {
  value: number,
  formatter?: (value: number) => string,
  label: string
}

export type ColumnRenderData = ColumnData & {
  heightFactor: number
}

function ColumnChart({ data }: { data: ColumnData[] }) {
  const maxValue = Math.max(...data.map(d => d.value));

  return (
    <div className={styles.columns}>
      {
        data.map((d, i) => (
          <Column
            key={i}
            {...d}
            heightFactor={maxValue > 0 ? d.value / maxValue : 0}
          />
        ))
      }
    </div>
  );
}

export default ColumnChart;