import { useWebSocket } from '@/hooks/useWebSocket';
import styles from './LineChart.module.css';
import { useEffect, useMemo, useState, type MouseEvent } from 'react';
import { ChannelDataProvider } from '@/features/PacketsLineChart/providers/ChannelDataProvider';
import { ConnectionStatus } from '@/services/websocket';
import PacketsLineChart from '@/features/PacketsLineChart';
import type { PacketsLineChartOptions } from '@/features/PacketsLineChart/PacketsLineChart';

export function LineChart() {
  const { params, connectionStatus } = useWebSocket();
  const [selectedSeries, setSelectedSeries] = useState<{ [index: string] : boolean }>({ "Received": true, "Sent": true });
  const [timeScale, setTimeScale] = useState<number>(600);

  const provider = useMemo(() => {
    if (!params?.channel_id || connectionStatus !== ConnectionStatus.Connected) {
      return null;
    }
    return new ChannelDataProvider({
      channelId: params.channel_id,
      windowSec: 5.0
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params, connectionStatus, timeScale]);


  useEffect(() => {
    return () => { provider?.dispose(); };
  }, [provider]);

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

  // Configure time scale
  const selectScale = (event: MouseEvent<HTMLButtonElement>) => {
    // Update CSS classes
    document.querySelectorAll(`.${styles.filter}`).forEach(e => e.classList.remove(styles.active!));
    (event.target as HTMLElement).classList.add(styles.active!);

    const newScale = +(event.target as HTMLSpanElement).getAttribute("data-value")!;
    setTimeScale(newScale);
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
        <div className={styles.filters}>
          <button onClick={selectScale} data-value={600} className={`${styles.filter} ${styles.active}`}>10m</button>
          <button onClick={selectScale} data-value={3600} className={`${styles.filter}`}>1h</button>
          <button onClick={selectScale} data-value={3600 * 24} className={styles.filter}>24h</button>
          <button onClick={selectScale} data-value={3600 * 24 * 7} className={styles.filter}>7d</button>
          <button onClick={selectScale} data-value={3600 * 24 * 30} className={styles.filter}>30d</button>
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