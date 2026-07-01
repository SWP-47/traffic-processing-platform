import styles from './PacketsLineChart.module.css';
import { useEffect, useRef, useState } from 'react';
import type { MouseEvent } from 'react';
import { init, type EChartsType } from 'echarts';
import telemetry from '@/services/telemetry';
import chartOptions from './chartOptions';
import { getHistory, type HistoryPeriod } from '@/services/history';
import { useWebSocket } from '@/hooks/useWebSocket';
import loadingIcon from '@/assets/loading.svg';
import useDelayedVisibility from '@/hooks/useDelayedVisibility';

const timeScaleMap: { [index: number]: HistoryPeriod } = {
  [3600]: '1h',
  [3600*24]: '24h',
  [3600*24*7]: '7d',
  [3600*24*30]: '30d'
}

function PacketsLineChart() {
  const chartElementRef = useRef<HTMLDivElement>(null);
  const showRealTime = useRef<boolean>(true);
  const chartRef = useRef<EChartsType>(null);
  const [ selectedSeries, setSelectedSeries ] = useState<{ [index: string] : boolean }>({ "Received": true, "Sent": true });
  const [ timeScale, setTimeScale ] = useState<number>(3600);
  const { connectionStatus, channelId } = useWebSocket();
  const [ isDataFetches, setIsDataFetches ] = useState<boolean>(false); 

  const showLoading = useDelayedVisibility(connectionStatus === 'connecting' || isDataFetches, 200);

  // Init chart
  useEffect(() => {
    if (!chartElementRef.current) return;
    if (!channelId) return;

    const chart = init(chartElementRef.current);
    chartRef.current = chart;
    
    chart.setOption(chartOptions);
    chart.setOption({
      xAxis: { dataMin: Date.now() - timeScale * 1000, dataMax: Date.now() }
    })

    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(chartElementRef.current);

    const data: { [index: string]: { name: string, value: number[] }[] } = {
      "Received": [],
      "Sent": []
    };

    let mouseOver = false;
    chartElementRef.current.addEventListener('mouseenter', () => { mouseOver = true; })
    chartElementRef.current.addEventListener('mouseleave', () => { mouseOver = false; })

    let currentStart: number | null = null;
    let currentEnd: number | null = null;
    chart.on('datazoom', function (params) {
      // @ts-expect-error Type is not defined
      const zoomData = params.batch[0];

      if (zoomData.end == 100) showRealTime.current = true;
      else showRealTime.current = false;

      // @ts-expect-error Type is not defined
      currentStart = chart.getOption().dataZoom[0].startValue;
      // @ts-expect-error Type is not defined
      currentEnd = chart.getOption().dataZoom[0].endValue;
    });

    // TODO: Make bucket system

    let isLoading = true;
    let bucketSizeMs = 0;

    const loadHistoryData = async () => {
      setIsDataFetches(true);
      const response = await getHistory(channelId, timeScaleMap[timeScale]!);
      bucketSizeMs = response.interval_sec! * 1000;

      response.points?.forEach(point => {
        const date = Date.parse(point.timestamp!);

        data.Received!.push({
          name: point.timestamp!,
          value: [date, point.packets_in_per_sec!, point.is_active! ? 1 : 0, bucketSizeMs]
        })

        data.Sent!.push({
          name: point.timestamp!,
          value: [date, point.packets_out_per_sec!, point.is_active! ? 1 : 0, bucketSizeMs]
        })
      })

      isLoading = false;
      setIsDataFetches(false);
      chart.setOption({
        xAxis: { minInterval: bucketSizeMs },
        dataZoom: [{ minValueSpan: bucketSizeMs * 2 }]
      })
    }

    loadHistoryData();

    const unsubscribeTelemetry = telemetry.subscribe(() => {
      if (isLoading) return;
      if (!chartRef.current) return;
      if (!data.Received || !data.Sent) return;

      const snapshot = telemetry.getLastUpdate();
      if (!snapshot) return;

      const min = Date.now() - timeScale * 1000;

      // Remove elements outside of the range to preserve space
      if (!mouseOver && data.Received[0] && data.Received[0].value[0]! < min) {
        data.Received = data.Received.filter(e => e.value[0]! >= min);
        data.Sent     = data.Sent.filter(e => e.value[0]! >= min);
      }

      // Collect data
      const date = Date.parse(snapshot.timestamp!);
      const packetsIn = snapshot.metrics?.direction_in?.packets_per_sec;
      const packetsOut = snapshot.metrics?.direction_out?.packets_per_sec;
      const channelActivity = snapshot.is_active ? 1 : 0;
      const windowSize = snapshot.window_ms;

      data.Received.push({
        name: snapshot.timestamp!,
        value: [date, packetsIn!, channelActivity!, windowSize!]
      })

      data.Sent.push({
        name: snapshot.timestamp!,
        value: [date, packetsOut!, channelActivity!, windowSize!]
      })

      // Update chart
      if (!showRealTime.current) {
        chart.setOption({
          series: [
            { name: "Received", data: data.Received },
            { name: "Sent", data: data.Sent }
          ],
          xAxis: { dataMin: Date.now() - timeScale * 1000, dataMax: Date.now() },
          dataZoom: { startValue: currentStart, endValue: currentEnd }
        });
      } else {
        chart.setOption({
          series: [
            { name: "Received", data: data.Received },
            { name: "Sent", data: data.Sent }
          ],
          xAxis: { dataMin: Date.now() - timeScale * 1000, dataMax: Date.now() }
        });
      }
    })

    return () => {
      unsubscribeTelemetry();
      resizeObserver.disconnect();
      chart.dispose();
    }
  }, [channelId, timeScale])

  // Configure selection
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

  useEffect(() => {
    if (!chartRef.current) return;
    
    // Update legend
    chartRef.current.setOption({ legend: { selected: selectedSeries } });
  }, [selectedSeries])

  // Configure time scale
  const selectScale = (event: MouseEvent<HTMLButtonElement>) => {
    // Update CSS classes
    document.querySelectorAll(`.${styles.filter}`).forEach(e => e.classList.remove(styles.active!));
    (event.target as HTMLElement).classList.add(styles.active!);

    const newScale = +(event.target as HTMLSpanElement).getAttribute("data-value")!;
    setTimeScale(newScale);
  };
  
  return (
    <div className={`${styles.component} card ${(connectionStatus !== 'connected' || showLoading) && styles.inactive}`}>
      <div className={styles.header}>
        <div className={styles.left}>
          <h1>RX/TX Rate over time</h1>
          <div className={styles.legend}>
            <span onClick={toggleLegend} data-series="Received">Received</span>
            <span onClick={toggleLegend} data-series="Sent">Sent</span>
          </div>
        </div>
        <div className={styles.filters}>
          <button onClick={selectScale} data-value={3600}       className={`${styles.filter} ${styles.active}`}>1h</button>
          <button onClick={selectScale} data-value={3600*24}    className={styles.filter}>24h</button>
          <button onClick={selectScale} data-value={3600*24*7}  className={styles.filter}>7d</button>
          <button onClick={selectScale} data-value={3600*24*30} className={styles.filter}>30d</button>
        </div>
      </div>
      <div className={styles.chart_wrapper}>
        { showLoading && (<img src={loadingIcon} className={styles.loading} alt="Loading..." />) }
        <div ref={chartElementRef} className={styles.chart}/>
      </div>
    </div>
  )
}

export default PacketsLineChart;