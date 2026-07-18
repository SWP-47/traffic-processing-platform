import PacketsColumnChart from "@/features/PacketsColumnChart";
import { useHostDetailsUpdate } from "@/hooks/useHostDetails";

function HostPacketsColumnChart({ ip, aggregationPeriod }: { ip: string, aggregationPeriod: number }) {
  const hostDetails = useHostDetailsUpdate({
    host_ip: ip,
    period_sec: Math.max(aggregationPeriod, 5) // If aggregationPeriod is less then 5, values are not displayed
  });

  return (
    <PacketsColumnChart
      packetsIn={hostDetails?.rx_per_sec ?? 0}
      packetsOut={hostDetails?.tx_per_sec ?? 0}
      bytesIn={hostDetails?.rx_bytes_per_sec ?? 0}
      bytesOut={hostDetails?.tx_bytes_per_sec ?? 0}
    />
  );
}

export default HostPacketsColumnChart;