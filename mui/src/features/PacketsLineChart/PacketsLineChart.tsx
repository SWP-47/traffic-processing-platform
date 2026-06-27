import style from './PacketsLineChart.module.css';
import { useEffect, useRef, useState } from 'react';
import type { MouseEvent } from 'react';
import { init, type EChartsType } from 'echarts';
import telemetry from '@/services/telemetry';
import chartOptions from './chartOptions';

function PacketsLineChart() {
  const chartElementRef = useRef<HTMLDivElement>(null);
  const showRealTime = useRef<boolean>(true);
  const chartRef = useRef<EChartsType>(null);
  const [ selectedSeries, setSelectedSeries ] = useState<{ [index: string] : boolean }>({ "Received": true, "Sent": true });
  const [ timeScale, setTimeScale ] = useState<number>(3600);

  // Init chart
  useEffect(() => {
    if (!chartElementRef.current) return;

    const chart = init(chartElementRef.current);
    chartRef.current = chart;
    
    chart.setOption(chartOptions);

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
      console.log(chart.getOption());

      // @ts-expect-error Type is not defined
      currentStart = chart.getOption().dataZoom[0].startValue;
      // @ts-expect-error Type is not defined
      currentEnd = chart.getOption().dataZoom[0].endValue;
    });

    // TODO: Get previous points, then subscribe to telemetry
    // Chart already have loading animation.
    // TODO: Make bucket system

    const unsubscribeTelemetry = telemetry.subscribe(() => {
      if (!chartRef.current) return;
      if (!data.Received || !data.Sent) return;

      const snapshot = telemetry.getLastUpdate();
      if (!snapshot?.data) return;

      const min = Date.now() - timeScale * 1000;

      // Remove elements outside of the range to preserve space
      if (!mouseOver && data.Received[0] && data.Received[0].value[0]! < min) {
        data.Received = data.Received.filter(e => e.value[0]! >= min);
        data.Sent     = data.Sent.filter(e => e.value[0]! >= min);
      }

      // Collect data
      const date = Date.parse(snapshot.data.timestamp!);
      const packetsIn = snapshot.data.metrics?.direction_in?.packets_per_sec;
      const packetsOut = snapshot.data.metrics?.direction_out?.packets_per_sec;
      const channelActivity = snapshot.data.is_active ? 1 : 0;
      const windowSize = snapshot.data.window_ms;

      data.Received.push({
        name: snapshot.data.timestamp!,
        value: [date, packetsIn!, channelActivity!, windowSize!]
      })

      data.Sent.push({
        name: snapshot.data.timestamp!,
        value: [date, packetsOut!, channelActivity!, windowSize!]
      })

      // Update chart
      if (!showRealTime.current) {
        chart.setOption({
          series: [
            { name: "Received", data: data.Received },
            { name: "Sent", data: data.Sent }
          ],
          xAxis: { dataMin: Date.now() - timeScale * 1000 },
          dataZoom: { startValue: currentStart, endValue: currentEnd }
        });
      } else {
        chart.setOption({
          series: [
            { name: "Received", data: data.Received },
            { name: "Sent", data: data.Sent }
          ],
          xAxis: { dataMin: Date.now() - timeScale * 1000 }
        });
      }
    })

    return () => {
      unsubscribeTelemetry();
      resizeObserver.disconnect();
      chart.dispose();
    }
  }, [timeScale])


  // Configure selection
  const toggleLegend = (event: MouseEvent<HTMLSpanElement>) => {
    const series = (event.target as HTMLSpanElement).getAttribute("data-series")!;
    if (selectedSeries[series] === undefined) return;

    // Update CSS classes
    (event.target as HTMLElement).classList.toggle(style.inactive!);

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
    document.querySelectorAll(`.${style.filter}`).forEach(e => e.classList.remove(style.active!));
    (event.target as HTMLElement).classList.add(style.active!);

    const newScale = +(event.target as HTMLSpanElement).getAttribute("data-value")!;
    setTimeScale(newScale);
  };
  

  return (
    <div className={style.component}>
      <div className={style.header}>
        <div className={style.left}>
          <h1>RX/TX Rate over time</h1>
          <div className={style.legend}>
            <span onClick={toggleLegend} data-series="Received">Received</span>
            <span onClick={toggleLegend} data-series="Sent">Sent</span>
          </div>
        </div>
        <div className={style.filters}>
          <button onClick={selectScale} data-value={3600}       className={`${style.filter} ${style.active}`}>1h</button>
          <button onClick={selectScale} data-value={3600*24}    className={style.filter}>1d</button>
          <button onClick={selectScale} data-value={3600*24*7}  className={style.filter}>1w</button>
          <button onClick={selectScale} data-value={3600*24*30} className={style.filter}>1m</button>
        </div>
      </div>
      <div ref={chartElementRef} className={style.chart} />
    </div>
  )
}

export default PacketsLineChart;