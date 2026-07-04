import TopTable from '@/components/TopTable';
import styles from './TopHostsTable.module.css';
import { useTopHosts } from '@/hooks/useTopHosts';
import { useEffect, useState } from 'react';
import topHosts, { type HostsSorting, type HostsTarget } from '@/services/topHosts';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useNavigate } from "react-router";
import { useHostsUpdate } from '@/hooks/useHostsUpdate';

function TopHostsTable({ mode }: { mode: 'lan' | 'wan' }) {
  const navigate = useNavigate();
  const [sorting, setSorting] = useState<HostsSorting>('last_seen');
  const { connectionStatus } = useWebSocket();
  const target = `${mode}_hosts` as HostsTarget;
  const hosts = useHostsUpdate({
    period: "5m",
    location: mode.toUpperCase(),
    sort_by: sorting,
    sort_order: 'desc',
    limit: 5
  });
  console.log(hosts)

  const columns = [
    { id: 'ip',        name: `${mode.toUpperCase()} IP`, allowSorting: false },
    { id: 'sent',      name: 'Sent',                     allowSorting: true },
    { id: 'received',  name: 'Received',                 allowSorting: true },
    { id: 'last_seen', name: 'Last seen',                allowSorting: true },
  ]

  const data = hosts?.map(d => [ d.ip, d.tx_per_sec, d.rx_per_sec, d.last_activity ]) ?? [];

  return (
    <div className={`card ${styles.table}`}>
      <div className={styles.header}>
        <h1 className={styles.title}>Top {mode.toUpperCase()} hosts</h1>
        <p className={styles.stats}>
          <span className={styles.stats_number}>{hosts?.length ?? 0}</span> active {mode.toUpperCase()} hosts
        </p>
      </div>
      <TopTable
        columns={columns}
        data={data}

        defaultSortColumn={sorting}
        onSortChange={(columnId) => setSorting(columnId as HostsSorting)}

        onExpanding={() => navigate('/hosts')}
      />
    </div>
  );
}

export default TopHostsTable;