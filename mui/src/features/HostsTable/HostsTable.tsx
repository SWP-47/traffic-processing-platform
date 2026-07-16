import FullTable from "@/components/FullTable";
import { useHostsUpdate, type HostsTableParams, type HostsUpdate } from "@/hooks/useHostsUpdate";
import { useState } from "react";
import styles from './HostsTable.module.css';
import Modal from "@/components/Modal";
import DetailedHostView from "./components/DetailedHostsView/DetailedHostView";
import AggregationSelector from "./components/AggregationSelector/AggregationSelector";
import Select from "./components/Select/Select";
import useAggregationPeriod from "./hooks/useAggregationPeriod";
import { secondsToHumanReadable } from "@/utils/time";
import { formatBytesPerSecond } from "@/utils/information";
import type { UnitContextValue } from "@/contexts/UnitContext/UnitContext";
import { useUnit } from "@/contexts/UnitContext/useUnit";

function ProgressPktsValue(value: number, maxValue: number, unit: UnitContextValue['unit']) {
  const widthPercent = maxValue > 0 ? (value / maxValue) * 100 : 0;

  let formattedValue: string = '';
  if (unit === 'bytes') {
    formattedValue = formatBytesPerSecond(value);
  } else if (unit === 'packets') {
    formattedValue = value.toFixed(0) + ' pkt/s';
  }

  return (
    <div className={styles.progress}>
      <div className={styles.progress_bar}>
        <div className={styles.progress_bar_value} style={{ width: `${widthPercent}%` }}></div>
      </div>
      <p className={styles.progress_value}>{formattedValue}</p>
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
  const { unit } = useUnit();

  const [currentPage, setCurrentPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [sortColumn, setSortColumn] = useState('ip');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [ipFilter, setIpFilter] = useState<string | null>(null);
  const [locationFilter, setLocationFilter] = useState<string | null>(null);

  const [selectedIP, setSelectedIp] = useState<string>();
  const [modalOpened, setModalOpened] = useState<boolean>(false);

  const [timeScale, setTimeScale] = useState<number>(600);
  const aggregationPeriod = useAggregationPeriod(timeScale);

  const hostsTable = useHostsUpdate({
    period_sec: Math.max(aggregationPeriod, 5),
    sort_by: (columns.find(c => c.id === sortColumn)?.sortId || sortColumn) as HostsTableParams["sort_by"],
    sort_order: sortDir,
    limit: limit,
    ip: ipFilter,
    location: locationFilter as HostsTableParams["location"],
    offset: limit * (currentPage - 1)
  });

  const maxPages = hostsTable?.total_count ?? 0;
  const getUnitRxValue = (host: HostsUpdate['hosts'][number]): number => (unit === 'bytes' ? host.rx_bytes_per_sec : host.rx_per_sec) ?? 0;
  const getUnitTxValue = (host: HostsUpdate['hosts'][number]): number => (unit === 'bytes' ? host.tx_bytes_per_sec : host.tx_per_sec) ?? 0;

  const maxReceivedValue = hostsTable && hostsTable.hosts.length > 0
    ? Math.max(...hostsTable.hosts.map(data => getUnitRxValue(data)))
    : 0;
    
  const maxSentValue = hostsTable && hostsTable.hosts.length > 0
    ? Math.max(...hostsTable.hosts.map(data => getUnitTxValue(data)))
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
      ProgressPktsValue(getUnitRxValue(d), maxReceivedValue, unit),
      ProgressPktsValue(getUnitTxValue(d), maxSentValue, unit),
      new Date(d.last_activity).toLocaleTimeString()
    ]
  );

  return (
    <>
      <div className={styles.header}>
        <input type="text" className={styles.filter} onChange={(e) => setIpFilter(e.target.value ?? null)} placeholder="Enter IP address" />
        <Select elements={['Both', 'LAN', 'WAN']} onSelect={(v) => setLocationFilter((v == 'LAN' || v == 'WAN') ? v : null)}/>
        <p
          className={styles.aggregaion_period}
          title={`Data is aggregated for the last ${secondsToHumanReadable(aggregationPeriod)}`}
        >
          AG: {secondsToHumanReadable(aggregationPeriod)}
        </p>
        <AggregationSelector onTimeScaleChange={(value) => setTimeScale(value)} />
      </div>
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
              defaultTimeScale={timeScale}
            />
          )
        }
      </Modal>
    </>
  )
}

export default HostsTable;