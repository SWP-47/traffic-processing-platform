import FullTable from "@/components/FullTable";
import { useState, useMemo, useCallback } from "react";
import { useUnit } from "@/contexts/UnitContext/useUnit";
import Progress from "@/components/Progress/Progress";
import { useHostTopDestinations, type HostTopDestinationsParams, type HostTopDestinationsUpdate } from "@/hooks/useHostTopDestinations";
import { useNavigate, useSearchParams } from "react-router";
import { useTtlArrayCache } from "@/hooks/useTtlArrayCache";
import { resolveSortKey, sortData } from "@/utils/sortData";

type SortColumn = Exclude<HostTopDestinationsParams['sort_by'], undefined>;
type Destination = HostTopDestinationsUpdate['destinations'][number];

const COLUMNS = [
  { id: 'location', name: 'Location' },
  { id: 'ip', name: 'IP' },
  { id: 'received', name: 'Received' },
  { id: 'last_seen', name: 'Last Seen' },
];

function FullDestinationsTable({ ip, timeScale, aggregationPeriod, defaultSorting }: { ip: string, timeScale: number, aggregationPeriod: number, defaultSorting: SortColumn }) {
  const { unit } = useUnit();
  const [searchParams] = useSearchParams(); 
  const navigate = useNavigate();

  const [currentPage, setCurrentPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [sortColumn, setSortColumn] = useState<SortColumn>(defaultSorting);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const destinationsTable = useHostTopDestinations({
    host_ip: ip,
    period_sec: Math.max(aggregationPeriod, 5),
    sort_by: sortColumn,
    sort_order: sortDir,
    limit,
    offset: limit * (currentPage - 1)
  });

  const getUnitValue = useCallback((dest: Destination): number => 
    (unit === 'bytes' ? dest.received_bytes_per_sec : dest.received_per_sec) ?? 0, 
  [unit]);

  const maxReceivedValue = useMemo(() => 
    destinationsTable?.destinations.length ? Math.max(...destinationsTable.destinations.map(getUnitValue)) : 0, 
  [destinationsTable, getUnitValue]);

  const tableData = useTtlArrayCache(
    destinationsTable?.destinations ?? null,
    timeScale,
    (dest) => dest.ip,
    (dest) => new Date(dest.last_seen),
    (oldDest, newDest) => ({ ...oldDest, ...newDest }),
    (dest) => ({ ...dest, received_bytes_per_sec: 0, received_per_sec: 0 })
  );

  const displayData = useMemo(() => {
    const sortKey = resolveSortKey(sortColumn, unit);
    const sorted = sortData(tableData, sortKey, sortDir, ['last_seen']);
    const start = (currentPage - 1) * limit;
    return sorted.slice(start, start + limit);
  }, [tableData, sortColumn, sortDir, limit, currentPage, unit]);

  const data = useMemo(() => displayData.map(d => [
    d.location,
    d.ip,
    Progress(getUnitValue(d), maxReceivedValue, unit),
    new Date(d.last_seen).toLocaleTimeString()
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
      onRowClick={(_, rowData) => {
        const clickedIp = rowData.at(COLUMNS.findIndex(el => el.id === 'ip')) as string;
        const newSearchParams = new URLSearchParams(searchParams);
        newSearchParams.set('ip', clickedIp);
        navigate(`/hosts?${newSearchParams.toString()}`);
      }}
    />
  );
}

export default FullDestinationsTable;