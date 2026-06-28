import StatusIndicator from "@/features/StatusIndicator";
import styles from './Dashboard.module.css';
import PacketsColumnChart from "@/features/PacketsColumnChart";
import Header from "@/components/Header/Header";
import PacketsLineChart from "@/features/PacketsLineChart";

function Dashboard() {
  return (
    <>
      <Header />
      <div className={styles.page}>
        <StatusIndicator />
        <div className={styles.row}>
          <PacketsColumnChart />
          <PacketsLineChart />
        </div>
      </div>
    </>
  );
}

export default Dashboard;