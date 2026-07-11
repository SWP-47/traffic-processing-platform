import styles from './Dashboard.module.css';
import TopHostsTable from '@/features/TopHostsTable';
import { LineChart } from './components/LineChart/LineChart';
import { RxTxColumnChart } from './components/RxTxColumnChar';

function Dashboard() {
  return (
    <>
      <div className={styles.page}>
        <div className={styles.row}>
          <RxTxColumnChart />
          <LineChart />
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