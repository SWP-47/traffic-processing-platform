import { useEffect, useState } from 'react';
import StatusIndicator from "@/features/StatusIndicator";
import ColumnChart from "@/features/ColumnChart";
import styles from './Dashboard.module.css';

const INITIAL_DATA = [
  { column_name: "TX", value: 100 },
  { column_name: "RX", value: 150 }
];

function Dashboard() {
  const [chartData, setChartData] = useState(INITIAL_DATA);

  useEffect(() => {
    const interval = setInterval(() => {
      setChartData((prev) =>
        prev.map((item) => ({
          ...item,
          value: Math.round(Math.random() * 100),
        }))
      );
    }, 1000);
    return () => clearInterval(interval);
  }, []);


  return (
    <div className={styles.page}>
      <StatusIndicator
        channel_id="TP#0"
        channel_active={true}
        channel_status_message="online"
      />
      <ColumnChart
        data={chartData}
      />
    </div>
  );
}

export default Dashboard;