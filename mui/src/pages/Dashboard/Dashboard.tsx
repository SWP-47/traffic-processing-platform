import styles from './Dashboard.module.css';
import PacketsColumnChart from "@/features/PacketsColumnChart/PacketsColumnChart";
import PacketsLineChart from "@/features/PacketsLineChart";
import TopHostsTable from '@/features/TopHostsTable';

function Dashboard() {
  return (
    <>
      <div className={styles.page}>
        <div className={styles.row}>
          <PacketsColumnChart />
          <PacketsLineChart />
        </div>
        <div className={styles.row}>
          <TopHostsTable mode='lan' />
          <TopHostsTable mode='wan' />
        </div>
      </div>
    </>
  );
}

export default Dashboard;