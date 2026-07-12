import PacketsColumnChart from "@/features/PacketsColumnChart";
import { useHostDetailsUpdate } from "@/hooks/useHostDetails";

function HostPacketsColumnChart({ ip }: { ip: string }) {
    const hostDetails = useHostDetailsUpdate({
        host_ip: ip,
        period_sec: 5
    });
    
    return (
        <PacketsColumnChart
            packetsIn={hostDetails?.rx_per_sec ?? 0}
            packetsOut={hostDetails?.tx_per_sec ?? 0}
        />
    );
}

export default HostPacketsColumnChart;