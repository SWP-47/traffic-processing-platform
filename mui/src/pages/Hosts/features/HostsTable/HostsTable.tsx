import FullTable from "@/components/FullTable";
import { useHostsUpdate, type HostsTableParams, type HostsUpdate } from "@/hooks/useHostsUpdate";
import { useEffect, useRef, useState, useMemo, useCallback } from "react";
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
import { resolveSortKey, sortData } from "@/utils/sortData";

type Host = HostsUpdate['hosts'][number];

const COLUMNS = [
  { id: 'location', name: 'Location' },
  { id: 'ip', name: 'IP' },
  { id: 'unique_destinations', name: 'Unique Destinations' },
  { id: 'rx', name: 'RX Rate' },
  { id: 'tx', name: 'TX Rate' },
  { id: 'last_activity', name: 'Last Seen' },
];

// Robust IPv4 validation regex
const isValidIpAddress = (ip: string): boolean => {
  const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
  return ipv4Regex.test(ip);
};

function HostsTable() {
  const { unit } = useUnit();
  const [searchParams] = useSearchParams();

  const [currentPage, setCurrentPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [sortColumn, setSortColumn] = useState<HostsTableParams["sort_by"]>('ip');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  
  // Separate UI input state from the actual applied filter state
  const initialIp = searchParams.get("ip") || "";
  const [ipInput, setIpInput] = useState<string>(initialIp);
  const [ipFilter, setIpFilter] = useState<string | null>(
    initialIp && isValidIpAddress(initialIp) ? initialIp : null
  );

  const [locationFilter, setLocationFilter] = useState<string | null>(
    ((initial) => initial === 'LAN' || initial === 'WAN' ? initial : null)(searchParams.get("location"))
  );

  const [selectedIP, setSelectedIp] = useState<string>();
  const [modalOpened, setModalOpened] = useState(false);
  const [timeScale, setTimeScale] = useState(600);
  
  const aggregationPeriod = useAggregationPeriod(timeScale);

  const hostsTable = useHostsUpdate({
    period_sec: Math.max(aggregationPeriod, 5),
    sort_by: sortColumn,
    sort_order: sortDir,
    limit,
    ip: ipFilter,
    location: locationFilter as HostsTableParams["location"],
    offset: limit * (currentPage - 1)
  });

  const getUnitValue = useCallback((host: Host, type: 'rx' | 'tx'): number => {
    const isBytes = unit === 'bytes';
    return type === 'rx' 
      ? (isBytes ? host.rx_bytes_per_sec : host.rx_per_sec) ?? 0
      : (isBytes ? host.tx_bytes_per_sec : host.tx_per_sec) ?? 0;
  }, [unit]);

  const maxReceivedValue = useMemo(() => 
    hostsTable?.hosts.length ? Math.max(...hostsTable.hosts.map(h => getUnitValue(h, 'rx'))) : 0, 
  [hostsTable, getUnitValue]);

  const maxSentValue = useMemo(() => 
    hostsTable?.hosts.length ? Math.max(...hostsTable.hosts.map(h => getUnitValue(h, 'tx'))) : 0, 
  [hostsTable, getUnitValue]);

  const tableData = useTtlArrayCache(
    hostsTable?.hosts ?? null,
    timeScale,
    (host) => host.ip,
    (host) => new Date(host.last_activity),
    (oldHost, newHost) => ({ ...oldHost, ...newHost }),
    (host) => ({ ...host, unique_destinations: 0, tx_per_sec: 0, rx_per_sec: 0, tx_bytes_per_sec: 0, rx_bytes_per_sec: 0 })
  );

  const displayData = useMemo(() => {
    const sourceData = ipFilter ? (hostsTable?.hosts || []) : tableData;
    
    const filteredData = locationFilter 
      ? sourceData.filter(host => host.location === locationFilter)
      : sourceData;
    
    const sortKey = resolveSortKey(sortColumn, unit);
    const start = (currentPage - 1) * limit;
    return sortData(filteredData, sortKey, sortDir, ['last_activity']).slice(start, start + limit);
  }, [ipFilter, hostsTable, tableData, sortColumn, sortDir, limit, locationFilter, currentPage, unit]);

  const data = useMemo(() => displayData.map(d => [
    d.location,
    d.ip,
    d.unique_destinations,
    Progress(getUnitValue(d, 'rx'), maxReceivedValue, unit),
    Progress(getUnitValue(d, 'tx'), maxSentValue, unit),
    new Date(d.last_activity).toLocaleTimeString()
  ]), [displayData, getUnitValue, maxReceivedValue, maxSentValue, unit]);

  const amountOfPages = ipFilter
    ? Math.ceil((hostsTable?.total_count ?? 0) / limit)
    : Math.ceil(tableData.length / limit);

  const prevIpRef = useRef(searchParams.get("ip"));
  const prevLocationRef = useRef(searchParams.get("location"));

  useEffect(() => {
    const currentIp = searchParams.get("ip");
    const currentLocation = searchParams.get("location");
    const validLocation = (currentLocation === 'LAN' || currentLocation === 'WAN') ? currentLocation : null;

    if (prevIpRef.current !== currentIp || prevLocationRef.current !== currentLocation) {
      prevIpRef.current = currentIp;
      prevLocationRef.current = currentLocation;

      setIpInput(currentIp || "");
      setIpFilter(currentIp && isValidIpAddress(currentIp) ? currentIp : null);
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
          className={`${styles.filter} ${(ipInput && !isValidIpAddress(ipInput)) ? styles.error : ''}`}
          value={ipInput}
          onChange={(e) => {
            const value = e.target.value.trim();
            setIpInput(value);
            
            // Only apply the filter if the input is a valid IP or completely empty
            if (value && isValidIpAddress(value)) {
              setIpFilter(value);
              setCurrentPage(1);
            } else if (!value) {
              setIpFilter(null);
              setCurrentPage(1);
            } else {
              setIpFilter(null);
            }
          }}
          placeholder="Enter IP address"
        />
        <Select
          elements={['Both', 'LAN', 'WAN']}
          value={locationFilter || 'Both'}
          onSelect={(v) => {
            setLocationFilter((v === 'LAN' || v === 'WAN') ? v : null);
            setCurrentPage(1);
          }}
        />
        <p className={styles.aggregaion_period} title={`Data is aggregated for the last ${secondsToHumanReadable(aggregationPeriod)}`}>
          AG: {secondsToHumanReadable(aggregationPeriod)}
        </p>
        <AggregationSelector onTimeScaleChange={setTimeScale} />
      </div>
      <FullTable
        columns={COLUMNS}
        data={data}
        sortColumnId={sortColumn}
        sortDirection={sortDir}
        onSortChange={(col, dir) => { setSortColumn(col as HostsTableParams["sort_by"]); setSortDir(dir); setCurrentPage(1); }}
        currentPage={currentPage}
        amountOfPages={amountOfPages}
        limit={limit}
        onPageChange={setCurrentPage}
        onLimitChange={(newLimit) => { setLimit(newLimit); setCurrentPage(1); }}
        onRowClick={(_, rowData) => {
          setSelectedIp(rowData.at(COLUMNS.findIndex(el => el.id === 'ip')) as string);
          setModalOpened(true);
        }}
      />
      <Modal opened={modalOpened} onClose={() => setModalOpened(false)}>
        {selectedIP && <DetailedHostView ip={selectedIP} defaultTimeScale={timeScale} />}
      </Modal>
    </>
  );
}

export default HostsTable;