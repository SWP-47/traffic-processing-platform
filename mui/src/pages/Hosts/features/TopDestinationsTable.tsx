import TopTable from '@/components/TopTable';
import styles from '@/pages/Dashboard/features/TopHostsTable/TopHostsTable.module.css';
import { useState } from 'react';
import { useHostTopDestinations, type HostTopDestinationsParams, type HostTopDestinationsUpdate } from '@/hooks/useHostTopDestinations';
import { useUnit } from '@/contexts/UnitContext/useUnit';
import Progress from '@/components/Progress/Progress';
import Modal from '@/components/Modal';
import FullDestinationsTableModal from './FullDestinationsTable';
import { useNavigate, useSearchParams } from 'react-router';
import { useTtlArrayCache } from '@/hooks/useTtlArrayCache';

function TopDestinationsTable({ ip, timeScale, aggregationPeriod }: { ip: string, timeScale: number,  aggregationPeriod: number }) {
  const { unit } = useUnit();

  const columns = [
    { id: 'ip',        sortId: 'ip', name: 'IP', allowSorting: true },
    { id: 'received',  sortId: unit === 'bytes' ? 'received_bytes_per_sec' : 'received_per_sec', name: 'Received', allowSorting: true },
    { id: 'last_seen', sortId: 'last_seen', name: 'Last seen', allowSorting: true },
  ];

  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [modalOpened, setModalOpened] = useState<boolean>(false);

  const [sorting, setSorting] = useState<HostTopDestinationsParams["sort_by"]>('received');
  const [sortingDir, setSortingDir] = useState<"asc" | "desc">("desc");
  const hosts = useHostTopDestinations({
    period_sec: Math.max(aggregationPeriod, 5), // If aggregationPeriod is less then 5, values are not displayed
    sort_by: sorting as HostTopDestinationsParams["sort_by"],
    sort_order: sortingDir,
    limit: 5,
    host_ip: ip,
    offset: 0
  });

  const destinationsList = hosts?.destinations ?? [];
  const getUnitRxValue = (host: HostTopDestinationsUpdate['destinations'][number]): number => (unit === 'bytes' ? host.received_bytes_per_sec : host.received_per_sec) ?? 0;

  const maxReceivedValue = destinationsList.length > 0
    ? Math.max(...destinationsList.map(data => getUnitRxValue(data)))
    : 0;

  const tableData = useTtlArrayCache(
    hosts?.destinations ?? null,
    timeScale,
    (dest) => dest.ip,
    (dest) => new Date(dest.last_seen),
    (oldDest, newDest) => ({ ...oldDest, ...newDest }),
    (dest) => ({ ...dest, received_bytes_per_sec: 0, received_per_sec: 0 })
  );

  const sortedTable = tableData.toSorted((a, b) => {
    const sortId = columns.find(c => c.id == sorting)?.sortId;
    const valA = a[sortId as keyof typeof a];
    const valB = b[sortId as keyof typeof b];

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
  }).slice(0, 5);

  const data = sortedTable.map(d => [
    d.ip,
    Progress(getUnitRxValue(d), maxReceivedValue, unit),
    new Date(d.last_seen).toLocaleTimeString()
  ]);

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
          columns={columns}
          data={data}

          defaultSortColumn={sorting!}
          onSortChange={(columnId, direction) => {
            setSorting(columnId as HostTopDestinationsParams["sort_by"]);
            setSortingDir(direction);
          }}
          onRowClick={(_, rowData) => {
            const clickedIp = rowData.at(columns.findIndex(el => el.id === 'ip')) as string;

            const newSearchParams = new URLSearchParams(searchParams);
            newSearchParams.set('ip', clickedIp);

            navigate(`/hosts?${newSearchParams.toString()}`);
          }}

          onExpanding={() => setModalOpened(true)}
        />
      </div>

      <Modal opened={modalOpened} onClose={() => setModalOpened(false)}>
        <FullDestinationsTableModal ip={ip} timeScale={timeScale} aggregationPeriod={aggregationPeriod} defaultSorting={sorting!} />
      </Modal>
    </>
  );
}

export default TopDestinationsTable;