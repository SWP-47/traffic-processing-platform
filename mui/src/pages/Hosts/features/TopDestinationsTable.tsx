import TopTable from '@/components/TopTable';
import styles from '@/pages/Dashboard/features/TopHostsTable/TopHostsTable.module.css';
import pageStyle from '../Hosts.module.css';
import { useState, useMemo, useCallback } from 'react';
import { useHostTopDestinations, type HostTopDestinationsParams, type HostTopDestinationsUpdate } from '@/hooks/useHostTopDestinations';
import { useUnit } from '@/contexts/UnitContext/useUnit';
import Progress from '@/components/Progress/Progress';
import Modal from '@/components/Modal';
import FullDestinationsTableModal from './FullDestinationsTable';
import { useNavigate, useSearchParams } from 'react-router';
import { useTtlArrayCache } from '@/hooks/useTtlArrayCache';
import { resolveSortKey, sortData } from '@/utils/sortData';

type SortColumn = Exclude<HostTopDestinationsParams['sort_by'], undefined>;
type Destination = HostTopDestinationsUpdate['destinations'][number];

const COLUMNS = [
  { id: 'ip', name: 'IP' },
  { id: 'received', name: 'Received' },
  { id: 'last_seen', name: 'Last Seen' },
];

function TopDestinationsTable({ ip, timeScale, aggregationPeriod }: { ip: string, timeScale: number, aggregationPeriod: number }) {
  const { unit } = useUnit();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [modalOpened, setModalOpened] = useState(false);

  const [sorting, setSorting] = useState<SortColumn>('received');
  const [sortingDir, setSortingDir] = useState<"asc" | "desc">("desc");

  const hosts = useHostTopDestinations({
    period_sec: Math.max(aggregationPeriod, 5),
    sort_by: sorting,
    sort_order: sortingDir,
    limit: 5,
    host_ip: ip,
    offset: 0
  });

  const getUnitValue = useCallback((dest: Destination): number =>
    (unit === 'bytes' ? dest.received_bytes_per_sec : dest.received_per_sec) ?? 0,
  [unit]);

  const maxReceivedValue = useMemo(() =>
    hosts?.destinations.length ? Math.max(...hosts.destinations.map(getUnitValue)) : 0,
  [hosts, getUnitValue]);

  const tableData = useTtlArrayCache(
    hosts?.destinations ?? null,
    timeScale,
    (dest) => dest.ip,
    (dest) => new Date(dest.last_seen),
    (oldDest, newDest) => ({ ...oldDest, ...newDest }),
    (dest) => ({ ...dest, received_bytes_per_sec: 0, received_per_sec: 0 })
  );

  const displayData = useMemo(() => {
    const sortKey = resolveSortKey(sorting, unit);
    return sortData(tableData, sortKey, sortingDir, ['last_seen']).slice(0, 5);
  }, [tableData, sorting, sortingDir, unit]);

  const data = useMemo(() => displayData.map(d => [
    d.ip,
    Progress(getUnitValue(d), maxReceivedValue, unit),
    new Date(d.last_seen).toLocaleTimeString()
  ]), [displayData, getUnitValue, maxReceivedValue, unit]);

  return (
    <>
      <div className={`card ${styles.table}`}>
        <div className={styles.header}>
          <h1 className={styles.title}>Top destinations</h1>
          <p className={styles.stats}>
            <span className={styles.stats_number}>{hosts?.total_count}</span> destinations hosts
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
          onRowClick={(_, rowData) => {
            const clickedIp = rowData.at(COLUMNS.findIndex(el => el.id === 'ip')) as string;
            const newSearchParams = new URLSearchParams(searchParams);
            newSearchParams.set('ip', clickedIp);
            navigate(`/hosts?${newSearchParams.toString()}`);
          }}
          onExpanding={() => setModalOpened(true)}
        />
      </div>
      <Modal opened={modalOpened} onClose={() => setModalOpened(false)}>
        <div className={pageStyle.wide_modal}>
          <FullDestinationsTableModal ip={ip} timeScale={timeScale} aggregationPeriod={aggregationPeriod} defaultSorting={sorting} />
        </div>
      </Modal>
    </>
  );
}

export default TopDestinationsTable;