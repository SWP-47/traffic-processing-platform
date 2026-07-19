import FullTable from "@/components/FullTable";
import { useState } from "react";
import { useUnit } from "@/contexts/UnitContext/useUnit";
import Progress from "@/components/Progress/Progress";
import { useHostTopDestinations, type HostTopDestinationsParams, type HostTopDestinationsUpdate } from "@/hooks/useHostTopDestinations";
import { useNavigate, useSearchParams } from "react-router";

type SortColumn = Exclude<HostTopDestinationsParams['sort_by'], undefined>;

function FullDestinationsTable({ ip, aggregationPeriod, defaultSorting }: { ip: string, aggregationPeriod: number,defaultSorting: SortColumn }) {
  const { unit } = useUnit();
  const [searchParams] = useSearchParams(); 
  const navigate = useNavigate();

  const [currentPage, setCurrentPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [sortColumn, setSortColumn] = useState<SortColumn>(defaultSorting);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const columns: { id: SortColumn, name: string, allowSorting: boolean, sortId?: string }[] = [
    { id: 'location', name: 'Location', allowSorting: true },
    { id: 'ip', name: 'IP', allowSorting: true },
    { id: 'received', sortId: unit === 'bytes' ? 'received_bytes_per_sec' : 'received_per_sec', name: 'Received', allowSorting: true },
    { id: 'last_seen', name: 'Last Seen', allowSorting: true },
  ];

  const destinationsTable = useHostTopDestinations({
    host_ip: ip,
    period_sec: Math.max(aggregationPeriod, 5),
    sort_by: sortColumn,
    sort_order: sortDir,
    limit: limit,
    offset: limit * (currentPage - 1)
  });

  const maxPages = destinationsTable?.total_count ?? 0;
  const getUnitRxValue = (host: HostTopDestinationsUpdate['destinations'][number]): number => (unit === 'bytes' ? host.received_bytes_per_sec : host.received_per_sec) ?? 0;

  const maxReceivedValue = destinationsTable && destinationsTable.destinations.length > 0
    ? Math.max(...destinationsTable.destinations.map(data => getUnitRxValue(data)))
    : 0;

  const sortedHosts = destinationsTable ? [...destinationsTable.destinations].sort((a, b) => {
    const sortKey = columns.find(c => c.id == sortColumn)?.sortId ?? sortColumn;

    const valA = a[sortKey as keyof typeof a];
    const valB = b[sortKey as keyof typeof b];

    if (valA == null) return 1;
    if (valB == null) return -1;

    if (sortColumn === 'last_seen') {
      const dateA = new Date(valA as string).getTime();
      const dateB = new Date(valB as string).getTime();
      return sortDir === 'asc' ? dateA - dateB : dateB - dateA;
    }

    if (typeof valA === 'number' && typeof valB === 'number') {
      return sortDir === 'asc' ? valA - valB : valB - valA;
    }

    if (typeof valA === 'string' && typeof valB === 'string') {
      return sortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }

    return 0;
  }) : [];

  const data = sortedHosts.map(d => 
    [
      d.location,
      d.ip,
      Progress(getUnitRxValue(d), maxReceivedValue, unit),
      new Date(d.last_seen).toLocaleTimeString()
    ]
  );

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

      // Interactions
      onRowClick={(_, rowData) => {
        const clickedIp = rowData.at(columns.findIndex(el => el.id === 'ip')) as string;
        
        const newSearchParams = new URLSearchParams(searchParams);
        newSearchParams.set('ip', clickedIp);
        
        navigate(`/hosts?${newSearchParams.toString()}`);
      }}
    />
  );
}

export default FullDestinationsTable;