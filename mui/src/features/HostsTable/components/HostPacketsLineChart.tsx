import styles from '@/pages/Dashboard/components/LineChart/RxTxLineChart.module.css'; 
import { useWebSocket } from "@/hooks/useWebSocket";
import { ConnectionStatus } from "@/services/websocket";
import { useMemo, useState, type MouseEvent } from "react";
import PacketsLineChart from '@/features/PacketsLineChart';
import type { PacketsLineChartOptions } from '@/features/PacketsLineChart/PacketsLineChart';
import { HostDataProvider } from '@/features/PacketsLineChart/providers/HostDataProvider';

function HostPacketsLineChart({
    ip, timeScale
}: { ip: string, timeScale: number }) {

    const { params, connectionStatus } = useWebSocket();
    const [selectedSeries, setSelectedSeries] = useState<{ [index: string]: boolean }>({ "Received": true, "Sent": true });

    const id = params?.channel_id;

    const provider = useMemo(() => {
        if (!id) {
            return null;
        }
        return new HostDataProvider({
            channelId: id,
            windowSec: timeScale,
            hostIp: ip
        });
    }, [id, timeScale, ip]);

    const toggleLegend = (event: MouseEvent<HTMLSpanElement>) => {
        const series = (event.target as HTMLSpanElement).getAttribute("data-series")!;
        if (selectedSeries[series] === undefined) return;

        // Update CSS classes
        (event.target as HTMLElement).classList.toggle(styles.inactive!);

        // Toggle selection
        setSelectedSeries({
            ...selectedSeries,
            [series]: !selectedSeries[series]
        });
    };

    return (
        <div className={`${styles.component} card ${(connectionStatus !== ConnectionStatus.Connected) && styles.inactive}`}>
            <div className={styles.header}>
                <div className={styles.left}>
                    <h1>RX/TX Rate over time</h1>
                    <div className={styles.legend}>
                        <span onClick={toggleLegend} data-series="Received">Received</span>
                        <span onClick={toggleLegend} data-series="Sent">Sent</span>
                    </div>
                </div>
            </div>
            {
                provider &&
                <PacketsLineChart
                    dataProvider={provider}
                    timeScale={timeScale}
                    selectedSeries={selectedSeries as PacketsLineChartOptions["selectedSeries"]}
                />
            }
        </div>
    );
}

export default HostPacketsLineChart;