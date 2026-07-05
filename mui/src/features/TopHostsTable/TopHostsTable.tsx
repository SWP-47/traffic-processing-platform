import TopTable from '@/components/TopTable';
import styles from './TopHostsTable.module.css';
import { useState } from 'react';
import { useNavigate } from "react-router";
import { useHostsUpdate, type HostsTableParams } from '@/hooks/useHostsUpdate';

function ProgressPktsValue(value: number, maxValue: number) {
  return (
    <div className={styles.progress}>
      <div className={styles.progress_bar}>
        <div className={styles.progress_bar_value} style={{ width: value / maxValue * 100 + '%' }}></div>
      </div>
      <p className={styles.progress_value}>{Math.round(value)} pkt/s</p>
    </div>
  );
}

function TopHostsTable({ mode }: { mode: 'lan' | 'wan' }) {
  const navigate = useNavigate();
  const [sorting, setSorting] = useState<HostsTableParams["sort_by"]>('last_activity');
  const hosts = useHostsUpdate({
    period: "5m",
    location: mode.toUpperCase() as HostsTableParams["location"],
    sort_by: sorting  as HostsTableParams["sort_by"],
    sort_order: 'desc',
    limit: 5,
    ip: null,
    offset: 0
  });

  const columns = [
    { id: 'ip',        name: `${mode.toUpperCase()} IP`, allowSorting: false },
    { id: 'tx',      name: 'Sent',                     allowSorting: true },
    { id: 'rx',  name: 'Received',                 allowSorting: true },
    { id: 'last_activity', name: 'Last seen',                allowSorting: true },
  ]

  const maxReceivedValue = Math.max(...(hosts ? hosts.hosts!.map(data => data.rx_per_sec) : [0]));
  const maxSentValue = Math.max(...(hosts ? hosts.hosts!.map(data => data.tx_per_sec) : [0]));

  const data = hosts ? hosts.hosts!.map(d => 
    [
      d.ip,
      ProgressPktsValue(d.tx_per_sec!, maxSentValue),
      ProgressPktsValue(d.rx_per_sec!, maxReceivedValue),
      new Date(d.last_activity).toLocaleTimeString()
    ]
  ) : [];

  return (
    <div className={`card ${styles.table}`}>
      <div className={styles.header}>
        <h1 className={styles.title}>Top {mode.toUpperCase()} hosts</h1>
        <p className={styles.stats}>
          <span className={styles.stats_number}>{hosts?.hosts.length ?? 0}</span> active {mode.toUpperCase()} hosts
        </p>
      </div>
      <TopTable
        columns={columns}
        data={data}

        defaultSortColumn={sorting}
        onSortChange={(columnId) => setSorting(columnId as HostsTableParams["sort_by"])}

        onExpanding={() => navigate('/hosts')}
      />
    </div>
  );
}

export default TopHostsTable;