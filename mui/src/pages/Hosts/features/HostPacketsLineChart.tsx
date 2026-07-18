import styles from '@/pages/Dashboard/features/LineChart/RxTxLineChart.module.css';
import { useWebSocket } from "@/hooks/useWebSocket";
import { ConnectionStatus } from "@/services/websocket";
import { useMemo, useState, type MouseEvent } from "react";
import PacketsLineChart from '@/features/PacketsLineChart';
import type { PacketsLineChartOptions } from '@/features/PacketsLineChart/PacketsLineChart';
import { HostDataProvider } from '@/features/PacketsLineChart/providers/HostDataProvider';
import { useUnit } from '@/contexts/UnitContext/useUnit';

function HostPacketsLineChart({
  ip,
  timeScale
}: { ip: string, timeScale: number }) {

  const { params, connectionStatus } = useWebSocket();
  const { unit } = useUnit();

  const [showReceived, setShowReceived] = useState(true);
  const [showSent, setShowSent] = useState(true);

  const id = params?.channel_id;

  const selectedSeries = useMemo<PacketsLineChartOptions["selectedSeries"]>(() => {
    if (unit === 'bytes') {
      return {
        Received_bytes: showReceived,
        Sent_bytes: showSent,
        Received_pkts: false,
        Sent_pkts: false
      };
    }
    return {
      Received_bytes: false,
      Sent_bytes: false,
      Received_pkts: showReceived,
      Sent_pkts: showSent
    };
  }, [unit, showReceived, showSent]);

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
    const series = (event.target as HTMLElement).getAttribute("data-series");

    if (series === "Received") {
      setShowReceived(prev => !prev);
    } else if (series === "Sent") {
      setShowSent(prev => !prev);
    }
  };

  return (
    <div className={`${styles.component} card ${(connectionStatus !== ConnectionStatus.Connected) && styles.inactive}`}>
      <div className={styles.header}>
        <div className={styles.left}>
          <h1>RX/TX Rate over time</h1>
          <div className={styles.legend}>
            <span
              onClick={toggleLegend}
              data-series="Received"
              className={!showReceived ? styles.inactive : ''}
            >
              Received
            </span>
            <span
              onClick={toggleLegend}
              data-series="Sent"
              className={!showSent ? styles.inactive : ''}
            >
              Sent
            </span>
          </div>
        </div>
      </div>
      {
        provider &&
        <PacketsLineChart
          dataProvider={provider}
          timeScale={timeScale}
          selectedSeries={selectedSeries}
          unit={unit}
        />
      }
    </div>
  );
}

export default HostPacketsLineChart;