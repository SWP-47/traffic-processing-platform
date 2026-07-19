import TopTable from '@/components/TopTable';
import styles from '@/pages/Dashboard/features/TopHostsTable/TopHostsTable.module.css';
import pageStyle from '../Hosts.module.css';

import { useState, useMemo, useCallback } from 'react';
import { useUnit } from '@/contexts/UnitContext/useUnit';
import Progress from '@/components/Progress/Progress';
import Modal from '@/components/Modal';
import { useHostTopPorts, type HostsTopPortsParams, type HostsTopPortsUpdate } from '@/hooks/useHostTopPorts';
import FullPortsTable from './FullPortsTable';
import { useTtlArrayCache } from '@/hooks/useTtlArrayCache';
import { resolveSortKey, sortData } from '@/utils/sortData';

type SortColumn = Exclude<HostsTopPortsParams['sort_by'], undefined>;
type Port = HostsTopPortsUpdate['ports'][number] & { timestamp: Date };

const COLUMNS = [
  { id: 'port', name: 'Port' },
  { id: 'protocol', name: 'Protocol' },
  { id: 'pps', name: 'Packets' },
];

function TopPortsTable({ ip, timeScale, aggregationPeriod }: { ip: string, timeScale: number, aggregationPeriod: number }) {
  const { unit } = useUnit();
  const [modalOpened, setModalOpened] = useState(false);
  const [sorting, setSorting] = useState<SortColumn>('pps');
  const [sortingDir, setSortingDir] = useState<"asc" | "desc">("desc");

  const ports = useHostTopPorts({
    period_sec: Math.max(aggregationPeriod, 5),
    sort_by: sorting,
    sort_order: sortingDir,
    limit: 5,
    host_ip: ip,
    offset: 0
  });

  const getUnitValue = useCallback((port: Port): number =>
    (unit === 'bytes' ? port.bytes_per_sec : port.packets_per_sec) ?? 0,
  [unit]);

  const maxReceivedValue = useMemo(() =>
    ports?.ports.length ? Math.max(...ports.ports.map(p => getUnitValue({ ...p, timestamp: new Date(ports.timestamp) }))) : 0,
  [ports, getUnitValue]);

  const timedPorts = useMemo(() => {
    if (!ports) return null;
    return ports.ports.map(p => ({ ...p, timestamp: new Date(ports.timestamp) }));
  }, [ports]);

  const tableData = useTtlArrayCache(
    timedPorts,
    timeScale,
    p => `${p.port}-${p.protocol}`,
    p => p.timestamp,
    (oldPort, newPort) => ({ ...oldPort, ...newPort }),
    (p) => ({ ...p, packets_per_sec: 0, bytes_per_sec: 0 })
  );

  const displayData = useMemo(() => {
    const sortKey = resolveSortKey(sorting, unit);
    return sortData(tableData, sortKey, sortingDir).slice(0, 5);
  }, [tableData, sorting, sortingDir, unit]);

  const data = useMemo(() => displayData.map(d => [
    d.port,
    d.protocol,
    Progress(getUnitValue(d), maxReceivedValue, unit)
  ]), [displayData, getUnitValue, maxReceivedValue, unit]);

  return (
    <>
      <div className={`card ${styles.table}`}>
        <div className={styles.header}>
          <h1 className={styles.title}>Top ports</h1>
          <p className={styles.stats}>
            <span className={styles.stats_number}>{ports?.total_count}</span> ports is in use
          </p>
        </div>
        <TopTable
          columns={COLUMNS}
          data={data}
          defaultSortColumn={sorting}
          onSortChange={(columnId, direction) => {
            setSorting(columnId as SortColumn);
            setSortingDir(direction);
          }}
          onExpanding={() => setModalOpened(true)}
        />
      </div>
      <Modal opened={modalOpened} onClose={() => setModalOpened(false)}>
        <div className={pageStyle.wide_modal}>
          <FullPortsTable ip={ip} timeScale={timeScale} aggregationPeriod={aggregationPeriod} defaultSorting={sorting} />
        </div>
      </Modal>
    </>
  );
}

export default TopPortsTable;