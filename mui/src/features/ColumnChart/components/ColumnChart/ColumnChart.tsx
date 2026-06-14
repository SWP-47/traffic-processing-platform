import type { ColumnChartData } from "../../types";
import Column from "../Column/Column";
import styles from "./ColumnChart.module.css";

function ColumnChart({ data }: { data: ColumnChartData[] }) {
  const maxValue = Math.max(...data.map(d => d.value));

  return (
    <div className={`${styles.chart} card`}>
      <h1 className={styles.title}>Rx/Tx Rate</h1>
      <div className={styles.columns}>
        {
          data.map(d => (
            <Column
              value={d.value}
              height={d.value / maxValue}
              column_name={d.column_name}
            />
          ))
        }
      </div>
    </div>
  );
}

export default ColumnChart;