import StatusIndicator from "@/features/StatusIndicator";
import ColumnChart from "@/features/ColumnChart";
import styles from './Dashboard.module.css';

const INITIAL_DATA = [
  { column_name: "TX", value: 100 },
  { column_name: "RX", value: 150 }
];

function Dashboard() {
  return (
    <div className={styles.page}>
      <StatusIndicator />
      <ColumnChart
        data={INITIAL_DATA}
      />
    </div>
  );
}

export default Dashboard;