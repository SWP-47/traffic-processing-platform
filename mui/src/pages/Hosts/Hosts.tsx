import HostsTable from "@/pages/Hosts/features/HostsTable/HostsTable";
import styles from './Hosts.module.css';

function Hosts() {
  return (
    <div className={styles.page}>
      <HostsTable />
    </div>
  )
}

export default Hosts;