import FullTable from "@/components/FullTable";
import { useHostsUpdate, type HostsTableParams } from "@/hooks/useHostsUpdate";
import { useState } from "react";
import styles from './HostsTable.module.css';
import Modal from "@/components/Modal";
import DetailedHostView from "./components/DetailedHostsView/DetailedHostView";

function ProgressPktsValue(value: number, maxValue: number) {
  const widthPercent = maxValue > 0 ? (value / maxValue) * 100 : 0;
  return (
    <div className={styles.progress}>
      <div className={styles.progress_bar}>
        <div className={styles.progress_bar_value} style={{ width: `${widthPercent}%` }}></div>
      </div>
      <p className={styles.progress_value}>{Math.round(value)} pkt/s</p>
    </div>
  );
}

const columns = [
  { id: 'location', name: 'Location', allowSorting: true },
  { id: 'ip', name: 'IP', allowSorting: true },
  { id: 'unique_destinations', name: 'Unique Destinations', allowSorting: true },
  { id: 'rx_per_sec', sortId: 'rx', name: 'RX Rate', allowSorting: true },
  { id: 'tx_per_sec', sortId: 'tx', name: 'TX Rate', allowSorting: true },
  { id: 'last_activity', name: 'Last Seen', allowSorting: true },
];

function HostsTable() {
  const [currentPage, setCurrentPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [sortColumn, setSortColumn] = useState('ip');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [filter, setFilter] = useState<string>();

  const [selectedIP, setSelectedIp] = useState<string>();
  const [modalOpened, setModalOpened] = useState<boolean>(false);

  const ipRegexp = /((?<=ip: )\S*)/;
  const ipFilter = filter?.match(ipRegexp) ? filter?.match(ipRegexp)![0] : null;
  const locationRegexp = /((?<=location: )\S*)/;
  let locationFilter = filter?.match(locationRegexp) ? filter?.match(locationRegexp)![0] : null;
  if (!['LAN', 'WAN', null].includes(locationFilter)) locationFilter = null;

  const hostsTable = useHostsUpdate({
    period_sec: 30,
    sort_by: (columns.find(c => c.id === sortColumn)?.sortId || sortColumn) as HostsTableParams["sort_by"],
    sort_order: sortDir,
    limit: limit,
    ip: ipFilter,
    location: locationFilter as HostsTableParams["location"],
    offset: limit * (currentPage - 1)
  });

  const maxPages = hostsTable?.total_count ?? 0;

  const maxReceivedValue = hostsTable && hostsTable.hosts.length > 0
    ? Math.max(...hostsTable.hosts.map(data => data.rx_per_sec ?? 0))
    : 0;
    
  const maxSentValue = hostsTable && hostsTable.hosts.length > 0
    ? Math.max(...hostsTable.hosts.map(data => data.tx_per_sec ?? 0))
    : 0;

  const sortedHosts = hostsTable ? [...hostsTable.hosts].sort((a, b) => {
    const valA = a[sortColumn as keyof typeof a];
    const valB = b[sortColumn as keyof typeof b];

    if (valA == null) return 1;
    if (valB == null) return -1;

    if (sortColumn === 'last_activity') {
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
      d.unique_destinations,
      ProgressPktsValue(d.rx_per_sec!, maxReceivedValue),
      ProgressPktsValue(d.tx_per_sec!, maxSentValue),
      new Date(d.last_activity).toLocaleTimeString()
    ]
  );

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
        onRowClick={(_, rowData) => {
          setSelectedIp(rowData.at(columns.findIndex(el => el.id === 'ip')) as string);
          setModalOpened(true);
        }}
      />

      {/* Detailed Host's statistics modal */}
      <Modal opened={modalOpened} onClose={() => setModalOpened(false)}>
        {
          selectedIP && modalOpened && (
            <DetailedHostView
              ip={selectedIP}
              onClose={() => setModalOpened(false)}
            />
          )
        }
      </Modal>
    </>
  )
}

export default HostsTable;