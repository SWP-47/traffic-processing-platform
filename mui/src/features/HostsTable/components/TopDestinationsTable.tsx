import TopTable from '@/components/TopTable';
import styles from '@/pages/Dashboard/components/TopHostsTable/TopHostsTable.module.css';
import { useState } from 'react';
import { useHostTopDestinations, type HostTopDestinationsParams } from '@/hooks/useHostTopDestinations';

function ProgressPktsValue(value: number, maxValue: number) {
  const widthPercent = maxValue > 0 ? (value / maxValue) * 100 : 0;
  return (
    <div className={styles.progress}>
      <div className={styles.progress_bar}>
        <div className={styles.progress_bar_value} style={{ width: `${widthPercent}%` }}></div>
      </div>
      <p className={styles.progress_value}>{Math.round(value)} pkt/s</p>
    </div>
  );
}

const columns = [
  { id: 'ip',         name: 'IP',          allowSorting: true },
  { id: 'location',   name: 'Location',    allowSorting: true },
  { id: 'received',         name: 'Received',    allowSorting: true },
  { id: 'last_seen',   name: 'Last seen',  allowSorting: true },
];

function TopDestinationsTable({ ip }: { ip: string }) {
  const [sorting, setSorting] = useState<HostTopDestinationsParams["sort_by"]>('received');
  const [sortingDir, setSortingDir] = useState<"asc" | "desc">("desc");
  const hosts = useHostTopDestinations({
    period_sec: 30,
    sort_by: sorting as HostTopDestinationsParams["sort_by"],
    sort_order: sortingDir,
    limit: 10,
    host_ip: ip,
    offset: 0
  });

  const destinationsList = hosts?.destinations ?? [];

  const maxReceivedValue = destinationsList.length > 0 
    ? Math.max(...destinationsList.map(data => data.received_per_sec ?? 0)) 
    : 0;

  console.log(sorting);

  const sortedTable = [...destinationsList].sort((a, b) => {
    const valA = a[sorting as keyof typeof a];
    const valB = b[sorting as keyof typeof b];

    if (valA == null) return 1;
    if (valB == null) return -1;

    if (sorting === 'last_seen') {
      const dateA = new Date(valA).getTime();
      const dateB = new Date(valB).getTime();
      return sortingDir === 'asc' ? dateA - dateB : dateB - dateA;
    }

    if (typeof valA === 'number' && typeof valB === 'number') {
      return sortingDir === 'asc' ? valA - valB : valB - valA;
    }

    if (typeof valA === 'string' && typeof valB === 'string') {
      return sortingDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }

    return 0;
  });

  const data = sortedTable.map(d => [
    d.ip,
    d.location,
    ProgressPktsValue(d.received_per_sec ?? 0, maxReceivedValue),
    new Date(d.last_seen).toLocaleTimeString()
  ]);

  return (
    <div className={`card ${styles.table}`}>
      <div className={styles.header}>
        <h1 className={styles.title}>Top destinations</h1>
        <p className={styles.stats}>
          <span className={styles.stats_number}>{destinationsList.length}</span> destinations hosts
        </p>
      </div>
      <TopTable
        columns={columns}
        data={data}

        defaultSortColumn={sorting!}
        onSortChange={(columnId, direction) => {
          setSorting(columnId as HostTopDestinationsParams["sort_by"]);
          setSortingDir(direction);
        }}
      />
    </div>
  );
}

export default TopDestinationsTable;