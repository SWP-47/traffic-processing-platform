import styles from './Dashboard.module.css';
import PacketsColumnChart from "@/features/PacketsColumnChart/PacketsColumnChart";
import PacketsLineChart from "@/features/PacketsLineChart";

function Dashboard() {
  return (
    <>
      <div className={styles.page}>
        <div className={styles.row}>
          <PacketsColumnChart />
          <PacketsLineChart />
        </div>
      </div>
    </>
  );
}

export default Dashboard;