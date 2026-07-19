import PacketsColumnChart from "@/features/PacketsColumnChart";
import { useTelemetry } from "@/hooks/useTelemetry";

export function RxTxColumnChart() {
    const update = useTelemetry();

    return (
        <PacketsColumnChart
            packetsIn={update?.metrics.direction_in.packets_per_sec ?? 0}
            packetsOut={update?.metrics.direction_out.packets_per_sec ?? 0}
            bytesIn={update?.metrics.direction_in.bytes_per_sec ?? 0}
            bytesOut={update?.metrics.direction_out.bytes_per_sec ?? 0}
        />
    );
}