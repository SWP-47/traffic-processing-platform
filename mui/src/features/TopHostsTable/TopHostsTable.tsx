import TopTable from '@/components/TopTable';
import styles from './TopHostsTable.module.css';
import { useTopHosts } from '@/hooks/useTopHosts';
import { useEffect, useState } from 'react';
import topHosts, { type HostsSorting, type HostsTarget } from '@/services/topHosts';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useNavigate } from "react-router";
import { useHostsUpdate } from '@/hooks/useHostsUpdate';

function ProgressPktsValue(value: number, maxValue: number) {
  return (
    <div className={styles.progress}>
      <div className={styles.progress_bar}>
        <div className={styles.progress_bar_value} style={{ width: value / maxValue * 100 + '%' }}></div>
      </div>
      <p className={styles.progress_value}>{value} pkt/s</p>
    </div>
  );
}

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

  const maxReceivedValue = Math.max(...(hosts?.map(data => data.received_per_sec!) ?? [0]));
  const maxSentValue = Math.max(...(hosts?.map(data => data.sent_per_sec!) ?? [0]));

  const data = hosts?.map(d => 
    [
      d.ip,
      ProgressPktsValue(d.sent_per_sec!, maxSentValue),
      ProgressPktsValue(d.received_per_sec!, maxReceivedValue),
      d.last_seen
    ]
  ) ?? [];

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