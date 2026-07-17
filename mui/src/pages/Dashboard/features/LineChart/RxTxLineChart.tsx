import { useWebSocket } from '@/hooks/useWebSocket';
import styles from './RxTxLineChart.module.css';
import { useMemo, useState, type MouseEvent } from 'react';
import { ChannelDataProvider } from '@/features/PacketsLineChart/providers/ChannelDataProvider';
import { ConnectionStatus } from '@/services/websocket';
import PacketsLineChart from '@/features/PacketsLineChart';
import type { PacketsLineChartOptions } from '@/features/PacketsLineChart/PacketsLineChart';
import { useUnit } from '@/contexts/UnitContext/useUnit';

export function RxTxLineChart() {
  const { params, connectionStatus } = useWebSocket();
  const { unit } = useUnit();

  const [showReceived, setShowReceived] = useState(true);
  const [showSent, setShowSent] = useState(true);
  const [timeScale, setTimeScale] = useState<number>(60 * 5);

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
    if (!params?.channel_id || connectionStatus !== ConnectionStatus.Connected) {
      return null;
    }
    return new ChannelDataProvider({
      channelId: params.channel_id,
      windowSec: 5.0
    });
  }, [params, connectionStatus]);

  const toggleLegend = (event: MouseEvent<HTMLSpanElement>) => {
    const series = (event.target as HTMLElement).getAttribute("data-series");
    
    if (series === "Received") {
      setShowReceived(prev => !prev);
      (event.target as HTMLElement).classList.toggle(styles.inactive!);
    } else if (series === "Sent") {
      setShowSent(prev => !prev);
      (event.target as HTMLElement).classList.toggle(styles.inactive!);
    }
  };

  const selectScale = (event: MouseEvent<HTMLButtonElement>) => {
    const newScale = +(event.target as HTMLElement).getAttribute("data-value")!;
    setTimeScale(newScale);
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
        <div className={styles.filters}>
          <button onClick={selectScale} data-value={60 * 5} className={`${styles.filter} ${timeScale === 60 * 5 ? styles.active : ''}`}>5m</button>
          <button onClick={selectScale} data-value={60 * 15} className={`${styles.filter} ${timeScale === 60 * 15 ? styles.active : ''}`}>15m</button>
          <button onClick={selectScale} data-value={3600} className={`${styles.filter} ${timeScale === 3600 ? styles.active : ''}`}>1h</button>
          <button onClick={selectScale} data-value={3600 * 24} className={`${styles.filter} ${timeScale === 3600 * 24 ? styles.active : ''}`}>24h</button>
          <button onClick={selectScale} data-value={3600 * 24 * 7} className={`${styles.filter} ${timeScale === 3600 * 24 * 7 ? styles.active : ''}`}>7d</button>
          <button onClick={selectScale} data-value={3600 * 24 * 30} className={`${styles.filter} ${timeScale === 3600 * 24 * 30 ? styles.active : ''}`}>30d</button>
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