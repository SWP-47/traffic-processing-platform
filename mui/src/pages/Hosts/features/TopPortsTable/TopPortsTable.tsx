import TopTable from '@/components/TopTable';
import styles from '@/pages/Dashboard/features/TopHostsTable/TopHostsTable.module.css';
import mstyles from './TopPortsTable.module.css';

import { useState } from 'react';
import { useUnit } from '@/contexts/UnitContext/useUnit';
import Progress from '@/components/Progress/Progress';
import Modal from '@/components/Modal';
import { useHostTopPorts, type HostsTopPortsParams, type HostsTopPortsUpdate } from '@/hooks/useHostTopPorts';
import FullPortsTable from '../FullPortsTable';

function TopPortsTable({ ip, aggregationPeriod }: { ip: string, aggregationPeriod: number }) {
  const { unit } = useUnit();

  const columns = [
    { id: 'port',      sortId: 'ip', name: 'Port', allowSorting: true },
    { id: 'protocol',  sortId: 'protocol', name: 'Protocol', allowSorting: true },
    { id: 'pps',       sortId: unit === 'bytes' ? 'bytes_per_sec' : 'packets_per_sec', name: 'Packets', allowSorting: true },
  ];

  const [modalOpened, setModalOpened] = useState<boolean>(false);

  const [sorting, setSorting] = useState<HostsTopPortsParams['sort_by']>('pps');
  const [sortingDir, setSortingDir] = useState<"asc" | "desc">("desc");
  const ports = useHostTopPorts({
    period_sec: Math.max(aggregationPeriod, 5), // If aggregationPeriod is less then 5, values are not displayed
    sort_by: sorting,
    sort_order: sortingDir,
    limit: 5,
    host_ip: ip,
    offset: 0
  });

  const portsList = ports?.ports ?? [];
  const getUnitRxValue = (host: HostsTopPortsUpdate['ports'][number]): number => (unit === 'bytes' ? host.bytes_per_sec : host.packets_per_sec) ?? 0;

  const maxReceivedValue = portsList.length > 0
    ? Math.max(...portsList.map(data => getUnitRxValue(data)))
    : 0;

  const sortedTable = [...portsList].sort((a, b) => {
    const sortId = columns.find(c => c.id == sorting)?.sortId;
    const valA = a[sortId as keyof typeof a];
    const valB = b[sortId as keyof typeof b];

    if (valA == null) return 1;
    if (valB == null) return -1;

    if (typeof valA === 'number' && typeof valB === 'number') {
      return sortingDir === 'asc' ? valA - valB : valB - valA;
    }

    if (typeof valA === 'string' && typeof valB === 'string') {
      return sortingDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }

    return 0;
  });

  const data = sortedTable.map(d => [
    d.port,
    d.protocol,
    Progress(getUnitRxValue(d), maxReceivedValue, unit)
  ]);

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
          columns={columns}
          data={data}

          defaultSortColumn={sorting!}
          onSortChange={(columnId, direction) => {
            setSorting(columnId as HostsTopPortsParams["sort_by"]);
            setSortingDir(direction);
          }}

          onExpanding={() => setModalOpened(true)}
        />
      </div>

      <Modal opened={modalOpened} onClose={() => setModalOpened(false)}>
        <div className={mstyles.full_table_modal}>
            <FullPortsTable ip={ip} aggregationPeriod={aggregationPeriod} defaultSorting={sorting!} />
        </div>
      </Modal>
    </>
  );
}

export default TopPortsTable;