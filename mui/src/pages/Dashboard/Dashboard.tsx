import styles from './Dashboard.module.css';
import TopHostsTable from '@/pages/Dashboard/components/TopHostsTable';
import { RxTxLineChart } from './components/LineChart/RxTxLineChart';
import { RxTxColumnChart } from './components/RxTxColumnChar';

function Dashboard() {
  return (
    <>
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
    </>
  );
}

export default Dashboard;