import FullTable from "@/components/FullTable";
import { useMemo, useState } from "react";
import { useUnit } from "@/contexts/UnitContext/useUnit";
import Progress from "@/components/Progress/Progress";
import { useHostTopPorts, type HostsTopPortsParams, type HostsTopPortsUpdate } from "@/hooks/useHostTopPorts";
import { useTtlArrayCache } from "@/hooks/useTtlArrayCache";

type SortColumn = Exclude<HostsTopPortsParams['sort_by'], undefined>;

function FullPortsTable({ ip, timeScale, aggregationPeriod, defaultSorting }: { ip: string, timeScale: number, aggregationPeriod: number,defaultSorting: SortColumn }) {
  const { unit } = useUnit();
  const [currentPage, setCurrentPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [sortColumn, setSortColumn] = useState<SortColumn>(defaultSorting);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const columns = [
    { id: 'port',      sortId: 'ip', name: 'Port', allowSorting: true },
    { id: 'protocol',  sortId: 'protocol', name: 'Protocol', allowSorting: true },
    { id: 'pps',       sortId: unit === 'bytes' ? 'bytes_per_sec' : 'packets_per_sec', name: 'Packets', allowSorting: true },
  ];

  const portsTable = useHostTopPorts({
    host_ip: ip,
    period_sec: Math.max(aggregationPeriod, 5),
    sort_by: sortColumn,
    sort_order: sortDir,
    limit: limit,
    offset: limit * (currentPage - 1)
  });

  const getUnitRxValue = (host: HostsTopPortsUpdate['ports'][number]): number => (unit === 'bytes' ? host.bytes_per_sec : host.packets_per_sec) ?? 0;

  const maxReceivedValue = portsTable && portsTable.ports.length > 0
    ? Math.max(...portsTable.ports.map(data => getUnitRxValue(data)))
    : 0;

  const timedPorts = useMemo(() => {
    if (!portsTable) return null;
    
    return portsTable.ports.map(p => ({
      ...p,
      timestamp: new Date(portsTable.timestamp) 
    }));
  }, [portsTable]);

  const tableData = useTtlArrayCache(
    timedPorts,
    timeScale,
    p =>  `${p.port}-${p.protocol}`,
    p => p.timestamp,
    (oldPort, newPort) => ({ ...oldPort, ...newPort }),
    (p) => ({ ...p, packets_per_sec: 0, bytes_per_sec: 0 })
  )

  const sortedHosts = tableData.toSorted((a, b) => {
    const sortKey = columns.find(c => c.id == sortColumn)?.sortId ?? sortColumn;

    const valA = a[sortKey as keyof typeof a];
    const valB = b[sortKey as keyof typeof b];

    if (valA == null) return 1;
    if (valB == null) return -1;

    if (typeof valA === 'number' && typeof valB === 'number') {
      return sortDir === 'asc' ? valA - valB : valB - valA;
    }

    if (typeof valA === 'string' && typeof valB === 'string') {
      return sortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }

    return 0;
  }).slice(0, limit);

  const data = sortedHosts.map(d => 
    [
      d.port,
      d.protocol,
      Progress(getUnitRxValue(d), maxReceivedValue, unit),
    ]
  );

  const maxPages = Math.max(portsTable?.total_count ?? 0, tableData.length);

  return (
    <FullTable
      columns={columns}
      
      data={data}
      sortColumnId={sortColumn}
      sortDirection={sortDir}
      onSortChange={(col, dir) => { setSortColumn(col as SortColumn); setSortDir(dir); setCurrentPage(1); }}

      // Pagination
      currentPage={currentPage}
      amountOfPages={Math.ceil(maxPages / limit)}
      limit={limit}
      onPageChange={setCurrentPage}
      onLimitChange={(newLimit) => { setLimit(newLimit); setCurrentPage(1); }}
    />
  );
}

export default FullPortsTable;