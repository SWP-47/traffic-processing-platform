import FullTable from "@/components/FullTable";
import { useHostsUpdate, type HostsTableParams } from "@/hooks/useHostsUpdate";
import { useState } from "react";
import styles from './HostsTable.module.css';

function ProgressPktsValue(value: number, maxValue: number) {
  return (
    <div className={styles.progress}>
      <div className={styles.progress_bar}>
        <div className={styles.progress_bar_value} style={{ width: value / maxValue * 100 + '%' }}></div>
      </div>
      <p className={styles.progress_value}>{Math.round(value)} pkt/s</p>
    </div>
  );
}

const columns = [
  { id: 'location', name: 'Location', allowSorting: false },
  { id: 'ip', name: 'IP', allowSorting: true },
  { id: 'unique_destinations', name: 'Unique Destinations', allowSorting: true },
  { id: 'rx_per_sec', name: 'RX Rate', allowSorting: true },
  { id: 'rx_per_sec', name: 'TX Rate', allowSorting: true },
  { id: 'last_activity', name: 'Last Seen', allowSorting: true },
]

function HostsTable() {
  const [currentPage, setCurrentPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [sortColumn, setSortColumn] = useState('ip');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [filter, setFilter] = useState<string>();

  const ipRegexp = /((?<=ip: )\S*)/;
  const ipFilter = filter?.match(ipRegexp) ? filter?.match(ipRegexp)![0] : null;
  const locationRegexp = /((?<=location: )\S*)/;
  let locationFilter = filter?.match(locationRegexp) ? filter?.match(locationRegexp)![0] : null;
  if (!['LAN', 'WAN', null].includes(locationFilter)) locationFilter = null;


  const hostsTable = useHostsUpdate({
    period: "5m",
    sort_by: sortColumn as HostsTableParams["sort_by"],
    sort_order: sortDir,
    limit: limit,
    ip: ipFilter,
    location: locationFilter as HostsTableParams["location"],
    offset: limit * (currentPage - 1)
  });

  const maxPages = hostsTable?.total_count ?? 0;

  const maxReceivedValue = Math.max(
    ...(hostsTable ? hostsTable.hosts.map(data => data.rx_per_sec!) : [0])
  );
  const maxSentValue = Math.max(
    ...(hostsTable ? hostsTable.hosts.map(data => data.tx_per_sec!) : [0])
  );

  const data = hostsTable ? hostsTable.hosts.map(d => 
    [
      d.location,
      d.ip,
      d.unique_destinations,
      ProgressPktsValue(d.tx_per_sec!, maxSentValue),
      ProgressPktsValue(d.rx_per_sec!, maxReceivedValue),
      new Date(d.last_activity).toLocaleTimeString()
    ]
  ) : [];

  return (
    <>
      <input type="text" className={styles.filter} onChange={(e) => setFilter(e.target.value)} />
      <FullTable
        columns={columns}
        
        data={data}
        sortColumnId={sortColumn}
        sortDirection={sortDir}
        onSortChange={(col, dir) => { setSortColumn(col); setSortDir(dir); setCurrentPage(1); }}

        // Pagination
        currentPage={currentPage}
        amountOfPages={Math.ceil(maxPages / limit)}
        limit={limit}
        onPageChange={setCurrentPage}
        onLimitChange={(newLimit) => { setLimit(newLimit); setCurrentPage(1); }}

        // Interactions
        onRowClick={(index, rowData) => console.log(`Clicked row ${index}:`, rowData)}
      />
    </>
  )
}

export default HostsTable;