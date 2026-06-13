import StatusIndicator from "@/features/StatusIndicator";
import ColumnChart from "@/features/ColumnChart";
import styles from './Dashboard.module.css';

function Dashboard() {
  return (
    <div className={styles.page}>
      <StatusIndicator
        channel_id="TP#0"
        channel_active={true}
        channel_status_message="online"
      />
      <ColumnChart
        data={[
          {
            column_name: "TX",
            value: 100
          },
          {
            column_name: "RX",
            value: 150
          }
        ]}
      />
    </div>
  );
}

export default Dashboard;