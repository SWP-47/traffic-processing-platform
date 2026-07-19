import TopTable from '@/components/TopTable';
import styles from './TopHostsTable.module.css';
import { useMemo, useState } from 'react';
import { useNavigate } from "react-router";
import { useHostsUpdate, type HostsTableParams, type HostsUpdate } from '@/hooks/useHostsUpdate';
import { useUnit } from '@/contexts/UnitContext/useUnit';
import Progress from '@/components/Progress/Progress';
import Modal from '@/components/Modal';
import DetailedHostView from '@/pages/Hosts/features/DetailedHostsView/DetailedHostView';
import { useTtlArrayCache } from '@/hooks/useTtlArrayCache';

function TopHostsTable({ mode }: { mode: 'lan' | 'wan' }) {
  const navigate = useNavigate();
  const { unit } = useUnit();

  const [modalOpened, setModalOpened] = useState<boolean>(false);
  const [selectedIp, setSelectedIp] = useState<string>();

  const [sorting, setSorting] = useState<HostsTableParams["sort_by"]>('last_activity');
  const [sortingDir, setSortingDir] = useState<"asc" | "desc">("desc");
  const hosts = useHostsUpdate({
    period_sec: 5,
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

  const tableData = useTtlArrayCache(
    hosts?.hosts ?? null,
    60,
    h => h.ip,
    h => new Date(h.last_activity),
    (oldHost, newHost) => ({ ...oldHost, ...newHost }),
    h => ({
      ...h,
      unique_destinations: 0,
      tx_per_sec: 0,
      rx_per_sec: 0,
      tx_bytes_per_sec: 0,
      rx_bytes_per_sec: 0,
    })
  );

  const sortedHosts = tableData.toSorted((a, b) => {
    const valA = a[sorting as keyof typeof a];
    const valB = b[sorting as keyof typeof b];

    if (valA == null) return 1;
    if (valB == null) return -1;

    if (sorting === 'last_activity') {
      const dateA = new Date(valA as string).getTime();
      const dateB = new Date(valB as string).getTime();
      return sortingDir === 'asc' ? dateA - dateB : dateB - dateA;
    }

    if (typeof valA === 'number' && typeof valB === 'number') {
      return sortingDir === 'asc' ? valA - valB : valB - valA;
    }

    if (typeof valA === 'string' && typeof valB === 'string') {
      return sortingDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }

    return 0;
  }).slice(0, 5);

  const data = sortedHosts.map(d => [
    d.ip,
    Progress(getUnitTxValue(d), maxSentValue, unit),
    Progress(getUnitRxValue(d), maxReceivedValue, unit),
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
        onRowClick={(_, rowData) => {
          const destinationIp = rowData[0] as string; 
          setSelectedIp(destinationIp);
          setModalOpened(true);
        }}

        onExpanding={() => navigate('/hosts')}
      />

      {/* Detailed Host's statistics modal */}
      <Modal opened={modalOpened} onClose={() => setModalOpened(false)}>
        {
          selectedIp && (
            <DetailedHostView ip={selectedIp} />
          )
        }
      </Modal>
    </div>
  );
}

export default TopHostsTable;