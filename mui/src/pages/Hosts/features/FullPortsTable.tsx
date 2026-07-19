import FullTable from "@/components/FullTable";
import { useState, useMemo, useCallback } from "react";
import { useUnit } from "@/contexts/UnitContext/useUnit";
import Progress from "@/components/Progress/Progress";
import { useHostTopPorts, type HostsTopPortsParams, type HostsTopPortsUpdate } from "@/hooks/useHostTopPorts";
import { useTtlArrayCache } from "@/hooks/useTtlArrayCache";
import { resolveSortKey, sortData } from "@/utils/sortData";

type SortColumn = Exclude<HostsTopPortsParams['sort_by'], undefined>;
type Port = HostsTopPortsUpdate['ports'][number] & { timestamp: Date };

const COLUMNS = [
  { id: 'port', name: 'Port' },
  { id: 'protocol', name: 'Protocol' },
  { id: 'pps', name: 'Packets' },
];

function FullPortsTable({ ip, timeScale, aggregationPeriod, defaultSorting }: { ip: string, timeScale: number, aggregationPeriod: number, defaultSorting: SortColumn }) {
  const { unit } = useUnit();

  const [currentPage, setCurrentPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [sortColumn, setSortColumn] = useState<SortColumn>(defaultSorting);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const portsTable = useHostTopPorts({
    host_ip: ip,
    period_sec: Math.max(aggregationPeriod, 5),
    sort_by: sortColumn,
    sort_order: sortDir,
    limit,
    offset: limit * (currentPage - 1)
  });

  const getUnitValue = useCallback((port: Port): number =>
    (unit === 'bytes' ? port.bytes_per_sec : port.packets_per_sec) ?? 0,
  [unit]);

  const maxReceivedValue = useMemo(() =>
    portsTable?.ports.length ? Math.max(...portsTable.ports.map(p => getUnitValue({ ...p, timestamp: new Date(portsTable.timestamp) }))) : 0,
  [portsTable, getUnitValue]);

  const timedPorts = useMemo(() => {
    if (!portsTable) return null;
    return portsTable.ports.map(p => ({ ...p, timestamp: new Date(portsTable.timestamp) }));
  }, [portsTable]);

  const tableData = useTtlArrayCache(
    timedPorts,
    timeScale,
    p => `${p.port}-${p.protocol}`,
    p => p.timestamp,
    (oldPort, newPort) => ({ ...oldPort, ...newPort }),
    (p) => ({ ...p, packets_per_sec: 0, bytes_per_sec: 0 })
  );

  const displayData = useMemo(() => {
    const sortKey = resolveSortKey(sortColumn, unit);
    const sorted = sortData(tableData, sortKey, sortDir);
    const start = (currentPage - 1) * limit;
    return sorted.slice(start, start + limit);
  }, [tableData, sortColumn, sortDir, limit, currentPage, unit]);

  const data = useMemo(() => displayData.map(d => [
    d.port,
    d.protocol,
    Progress(getUnitValue(d), maxReceivedValue, unit),
  ]), [displayData, getUnitValue, maxReceivedValue, unit]);

  const amountOfPages = Math.ceil(tableData.length / limit);

  return (
    <FullTable
      columns={COLUMNS}
      data={data}
      sortColumnId={sortColumn}
      sortDirection={sortDir}
      onSortChange={(col, dir) => { setSortColumn(col as SortColumn); setSortDir(dir); setCurrentPage(1); }}
      currentPage={currentPage}
      amountOfPages={amountOfPages}
      limit={limit}
      onPageChange={setCurrentPage}
      onLimitChange={(newLimit) => { setLimit(newLimit); setCurrentPage(1); }}
    />
  );
}

export default FullPortsTable;