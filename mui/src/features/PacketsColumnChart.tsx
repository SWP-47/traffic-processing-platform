import ColumnChart from "@/components/ColumnChart";
import { useTelemetrySelector } from "@/hooks/useTelemetry";

function PacketsColumnChart() {
    const packets_in = useTelemetrySelector((tel) => tel?.data.metrics?.direction_in?.packets);
    const packets_out = useTelemetrySelector((tel) => tel?.data.metrics?.direction_out?.packets);

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