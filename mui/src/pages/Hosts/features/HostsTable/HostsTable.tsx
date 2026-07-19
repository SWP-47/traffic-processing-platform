import FullTable from "@/components/FullTable";
import { useHostsUpdate, type HostsTableParams, type HostsUpdate } from "@/hooks/useHostsUpdate";
import { useEffect, useRef, useState } from "react";
import styles from './HostsTable.module.css';
import Modal from "@/components/Modal";
import DetailedHostView from "../DetailedHostsView/DetailedHostView";
import AggregationSelector from "../../components/AggregationSelector/AggregationSelector";
import Select from "./components/Select/Select";
import useAggregationPeriod from "../../hooks/useAggregationPeriod";
import { secondsToHumanReadable } from "@/utils/time";
import { useUnit } from "@/contexts/UnitContext/useUnit";
import Progress from "@/components/Progress/Progress";
import { useSearchParams } from "react-router";
import { useTtlArrayCache } from "@/hooks/useTtlArrayCache";

type Host = HostsUpdate['hosts'][number];

function HostsTable() {
  const { unit } = useUnit();
  const [searchParams] = useSearchParams();

  const columns: { id: HostsTableParams["sort_by"], name: string, sortId?: string, allowSorting: boolean }[] = [
    { id: 'location', name: 'Location', allowSorting: true },
    { id: 'ip', name: 'IP', allowSorting: true },
    { id: 'unique_destinations', name: 'Unique Destinations', allowSorting: true },
    { id: 'rx', sortId: 'rx', name: 'RX Rate', allowSorting: true },
    { id: 'tx', sortId: 'tx', name: 'TX Rate', allowSorting: true },
    { id: 'last_activity', name: 'Last Seen', allowSorting: true },
  ];

  const prevUrlIpRef = useRef(searchParams.get("ip"));
  const prevUrlLocationRef = useRef(searchParams.get("location"));

  const [currentPage, setCurrentPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [sortColumn, setSortColumn] = useState<HostsTableParams["sort_by"]>('ip');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  
  const [ipFilter, setIpFilter] = useState<string | null>(searchParams.get("ip"));
  const initialLocation = searchParams.get("location");
  const [locationFilter, setLocationFilter] = useState<string | null>(
    (initialLocation === 'LAN' || initialLocation === 'WAN') ? initialLocation : null
  );

  const [selectedIP, setSelectedIp] = useState<string>();
  const [modalOpened, setModalOpened] = useState<boolean>(false);

  const [timeScale, setTimeScale] = useState<number>(600);
  const aggregationPeriod = useAggregationPeriod(timeScale);

  const hostsTable = useHostsUpdate({
    period_sec: Math.max(aggregationPeriod, 5),
    sort_by: sortColumn,
    sort_order: sortDir,
    limit: limit,
    ip: ipFilter,
    location: locationFilter as HostsTableParams["location"],
    offset: limit * (currentPage - 1)
  });

  const getUnitRxValue = (host: Host): number => (unit === 'bytes' ? host.rx_bytes_per_sec : host.rx_per_sec) ?? 0;
  const getUnitTxValue = (host: Host): number => (unit === 'bytes' ? host.tx_bytes_per_sec : host.tx_per_sec) ?? 0;

  const maxReceivedValue = hostsTable && hostsTable.hosts.length > 0
    ? Math.max(...hostsTable.hosts.map(data => getUnitRxValue(data)))
    : 0;
    
  const maxSentValue = hostsTable && hostsTable.hosts.length > 0
    ? Math.max(...hostsTable.hosts.map(data => getUnitTxValue(data)))
    : 0;

  const resetHost = (host: Host): Host => ({
    ...host,
    unique_destinations: 0,
    tx_per_sec: 0,
    rx_per_sec: 0,
    tx_bytes_per_sec: 0,
    rx_bytes_per_sec: 0,
  });

  const tableData = useTtlArrayCache(
    hostsTable?.hosts ?? null,
    timeScale,
    (host) => host.ip,
    (host) => new Date(host.last_activity),
    (oldHost, newHost) => ({ ...oldHost, ...newHost }),
    resetHost
  );

  const sortedHosts = (ipFilter ? (hostsTable?.hosts || []) : tableData).toSorted((a, b) => {
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
  }).slice(0, limit);

  const data = sortedHosts.map(d => 
    [
      d.location,
      d.ip,
      d.unique_destinations,
      Progress(getUnitRxValue(d), maxReceivedValue, unit),
      Progress(getUnitTxValue(d), maxSentValue, unit),
      new Date(d.last_activity).toLocaleTimeString()
    ]
  );

  const maxPages = Math.max(hostsTable?.total_count ?? 0, tableData.length);

  useEffect(() => {
    const currentUrlIp = searchParams.get("ip");
    const currentUrlLocation = searchParams.get("location");

    const urlChanged = prevUrlIpRef.current !== currentUrlIp || prevUrlLocationRef.current !== currentUrlLocation;

    if (urlChanged) {
      prevUrlIpRef.current = currentUrlIp;
      prevUrlLocationRef.current = currentUrlLocation;

      setIpFilter(currentUrlIp);
      const validLocation = (currentUrlLocation === 'LAN' || currentUrlLocation === 'WAN') ? currentUrlLocation : null;
      setLocationFilter(validLocation);
      setCurrentPage(1);

      setModalOpened(false);
    }
  }, [searchParams]);

  return (
    <>
      <div className={styles.header}>
        <input
          type="text"
          className={styles.filter}
          value={ipFilter || ""}
          onChange={(e) => {
            setIpFilter(e.target.value.trim() || null);
            setCurrentPage(1);
          }}
          placeholder="Enter IP address"
        />
        <Select
          elements={['Both', 'LAN', 'WAN']}
          value={locationFilter || 'Both'}
          onSelect={(v) => {
            const newValue = (v === 'LAN' || v === 'WAN') ? v : null;
            
            setLocationFilter(newValue);
            setCurrentPage(1);
          }}
        />
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
        onSortChange={(col, dir) => { setSortColumn(col as HostsTableParams["sort_by"]); setSortDir(dir); setCurrentPage(1); }}

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
          selectedIP && (
            <DetailedHostView
              ip={selectedIP}
              defaultTimeScale={timeScale}
            />
          )
        }
      </Modal>
    </>
  )
}

export default HostsTable;