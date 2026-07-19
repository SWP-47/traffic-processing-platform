import styles from './Dashboard.module.css';
import TopHostsTable from '@/pages/Dashboard/features/TopHostsTable';
import { RxTxLineChart } from './features/LineChart/RxTxLineChart';
import { RxTxColumnChart } from './features/RxTxColumnChar';

function Dashboard() {
  return (
    <div className={styles.page}>
      <div className={styles.row}>
        <RxTxColumnChart />
        <RxTxLineChart />
      </div>
      <div className={styles.row}>
        <TopHostsTable mode='lan' />
        <TopHostsTable mode='wan' />
      </div>
    </div>
  );
}

export default Dashboard;