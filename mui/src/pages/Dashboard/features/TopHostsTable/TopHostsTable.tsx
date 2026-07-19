import TopTable from '@/components/TopTable';
import styles from './TopHostsTable.module.css';
import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from "react-router";
import { useHostsUpdate, type HostsTableParams, type HostsUpdate } from '@/hooks/useHostsUpdate';
import { useUnit } from '@/contexts/UnitContext/useUnit';
import Progress from '@/components/Progress/Progress';
import Modal from '@/components/Modal';
import DetailedHostView from '@/pages/Hosts/features/DetailedHostsView/DetailedHostView';
import { useTtlArrayCache } from '@/hooks/useTtlArrayCache';
import { resolveSortKey, sortData } from '@/utils/sortData';

type Host = HostsUpdate['hosts'][number];

function TopHostsTable({ mode }: { mode: 'lan' | 'wan' }) {
  const navigate = useNavigate();
  const { unit } = useUnit();

  const [modalOpened, setModalOpened] = useState(false);
  const [selectedIp, setSelectedIp] = useState<string>();
  const [sorting, setSorting] = useState<HostsTableParams["sort_by"]>('last_activity');
  const [sortingDir, setSortingDir] = useState<"asc" | "desc">("desc");

  const hosts = useHostsUpdate({
    period_sec: 5,
    location: mode.toUpperCase() as HostsTableParams["location"],
    sort_by: sorting,
    sort_order: sortingDir,
    limit: 5,
    ip: null,
    offset: 0
  });

  const columns = useMemo(() => [
    { id: 'ip' as const, name: `${mode.toUpperCase()} IP` },
    { id: 'tx' as const, name: 'Sent' },
    { id: 'rx' as const, name: 'Received' },
    { id: 'last_activity' as const, name: 'Last seen' },
  ], [mode]);

  const getUnitValue = useCallback((host: Host, type: 'rx' | 'tx'): number => {
    const isBytes = unit === 'bytes';
    return type === 'rx'
      ? (isBytes ? host.rx_bytes_per_sec : host.rx_per_sec) ?? 0
      : (isBytes ? host.tx_bytes_per_sec : host.tx_per_sec) ?? 0;
  }, [unit]);

  const maxReceivedValue = useMemo(() => 
    hosts?.hosts.length ? Math.max(...hosts.hosts.map(h => getUnitValue(h, 'rx'))) : 0, 
  [hosts, getUnitValue]);
    
  const maxSentValue = useMemo(() => 
    hosts?.hosts.length ? Math.max(...hosts.hosts.map(h => getUnitValue(h, 'tx'))) : 0, 
  [hosts, getUnitValue]);

  const tableData = useTtlArrayCache(
    hosts?.hosts ?? null,
    60,
    h => h.ip,
    h => new Date(h.last_activity),
    (oldHost, newHost) => ({ ...oldHost, ...newHost }),
    h => ({ ...h, unique_destinations: 0, tx_per_sec: 0, rx_per_sec: 0, tx_bytes_per_sec: 0, rx_bytes_per_sec: 0 })
  );

  const displayData = useMemo(() => {
    const sortKey = resolveSortKey(sorting, unit);
    return sortData(tableData, sortKey, sortingDir, ['last_activity']).slice(0, 5);
  }, [tableData, sorting, sortingDir, unit]);

  const data = useMemo(() => displayData.map(d => [
    d.ip,
    Progress(getUnitValue(d, 'tx'), maxSentValue, unit),
    Progress(getUnitValue(d, 'rx'), maxReceivedValue, unit),
    new Date(d.last_activity).toLocaleTimeString()
  ]), [displayData, getUnitValue, maxSentValue, maxReceivedValue, unit]);

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
          setSelectedIp(rowData[0] as string);
          setModalOpened(true);
        }}
        onExpanding={() => navigate('/hosts')}
      />
      <Modal opened={modalOpened} onClose={() => setModalOpened(false)}>
        {selectedIp && <DetailedHostView ip={selectedIp} />}
      </Modal>
    </div>
  );
}

export default TopHostsTable;