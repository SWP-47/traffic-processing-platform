import ColumnChart from "@/components/ColumnChart";
import { useTelemetrySelector } from "@/hooks/useTelemetry";

function PacketsColumnChart() {
    const packets_in = useTelemetrySelector((tel) => tel?.metrics?.direction_in?.packets_per_sec);
    const packets_out = useTelemetrySelector((tel) => tel?.metrics?.direction_out?.packets_per_sec);

    return (
        <ColumnChart
            title="Rx/Tx chart"
            data={[
                {
                    value: packets_in ?? 0,
                    legend: 'IN'
                },
                {
                    value: packets_out ?? 0,
                    legend: 'OUT'
                }
            ]}
        />
    );
}

export default PacketsColumnChart;