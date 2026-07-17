import TopTable from '@/components/TopTable';
import styles from './TopHostsTable.module.css';
import { useMemo, useState } from 'react';
import { useNavigate } from "react-router";
import { useHostsUpdate, type HostsTableParams, type HostsUpdate } from '@/hooks/useHostsUpdate';
import { useUnit } from '@/contexts/UnitContext/useUnit';
import type { UnitContextValue } from '@/contexts/UnitContext/UnitContext';
import { formatBytesPerSecond } from '@/utils/information';

function ProgressPktsValue(value: number, maxValue: number, unit: UnitContextValue['unit']) {
  const widthPercent = maxValue > 0 ? (value / maxValue) * 100 : 0;

  let formattedValue: string = '';
  if (unit === 'bytes') {
    formattedValue = formatBytesPerSecond(value);
  } else if (unit === 'packets') {
    formattedValue = value.toFixed(0) + ' pkt/s';
  }

  return (
    <div className={styles.progress}>
      <div className={styles.progress_bar}>
        <div className={styles.progress_bar_value} style={{ width: `${widthPercent}%` }}></div>
      </div>
      <p className={styles.progress_value}>{formattedValue}</p>
    </div>
  );
}

function TopHostsTable({ mode }: { mode: 'lan' | 'wan' }) {
  const navigate = useNavigate();
  const { unit } = useUnit();
  const [sorting, setSorting] = useState<HostsTableParams["sort_by"]>('last_activity');
  const [sortingDir, setSortingDir] = useState<"asc" | "desc">("desc");
  const hosts = useHostsUpdate({
    period_sec: 30,
    location: mode.toUpperCase() as HostsTableParams["location"],
    sort_by: sorting  as HostsTableParams["sort_by"],
    sort_order: sortingDir,
    limit: 5,
    ip: null,
    offset: 0
  });

  const columns = useMemo(() => [
    { id: 'ip',            name: `${mode.toUpperCase()} IP`, allowSorting: true },
    { id: 'tx',            name: 'Sent',                     allowSorting: true },
    { id: 'rx',            name: 'Received',                 allowSorting: true },
    { id: 'last_activity', name: 'Last seen',                allowSorting: true },
  ], [mode]);

  const hostsList = hosts?.hosts ?? [];
  const getUnitRxValue = (host: HostsUpdate['hosts'][number]): number => (unit === 'bytes' ? host.rx_bytes_per_sec : host.rx_per_sec) ?? 0;
  const getUnitTxValue = (host: HostsUpdate['hosts'][number]): number => (unit === 'bytes' ? host.tx_bytes_per_sec : host.tx_per_sec) ?? 0;

  const maxReceivedValue = hostsList.length > 0 
    ? Math.max(...hostsList.map(data => getUnitRxValue(data))) 
    : 0;
    
  const maxSentValue = hostsList.length > 0 
    ? Math.max(...hostsList.map(data => getUnitTxValue(data)))
    : 0;

  const data = hostsList.map(d => [
    d.ip,
    ProgressPktsValue(getUnitTxValue(d), maxSentValue, unit),
    ProgressPktsValue(getUnitRxValue(d), maxReceivedValue, unit),
    new Date(d.last_activity).toLocaleTimeString()
  ]);

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
        onSortChange={(columnId, direction) => {
          setSorting(columnId as HostsTableParams["sort_by"]);
          setSortingDir(direction);
        }}

        onExpanding={() => navigate('/hosts')}
      />
    </div>
  );
}

export default TopHostsTable;