import styles from './PacketsLineChart.module.css';
import { useEffect, useRef, useState } from 'react';
import { init, type EChartsType } from 'echarts';
import chartOptions from './chartOptions';
import loadingIcon from '@/assets/loading.svg';
import useDelayedVisibility from '@/hooks/useDelayedVisibility';
import type { ChartDataProvider, DataPoint } from './types';
import type { UnitContextValue } from '@/contexts/UnitContext/UnitContext';

export interface PacketsLineChartOptions {
  dataProvider: ChartDataProvider,
  timeScale: number,
  selectedSeries: {
    Received_pkts: boolean,
    Sent_pkts: boolean,
    Received_bytes: boolean,
    Sent_bytes: boolean,
  },
  unit: UnitContextValue['unit'];
};

function PacketsLineChart({ dataProvider, timeScale, selectedSeries, unit } : PacketsLineChartOptions) {
  const chartElementRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<EChartsType>(null);
  const showRealTimeRef = useRef(true);
  const isMouseOverRef = useRef(false);
  const zoomStartRef = useRef<number | null>(null);
  const zoomEndRef = useRef<number | null>(null);
  const lastRenderedStartRef = useRef<number | null>(null);
  const [isDataFetching, setIsDataFetching] = useState<boolean>(false);

  const showLoading = useDelayedVisibility(isDataFetching, 200);

  // Init chart
  useEffect(() => {
    if (!chartElementRef.current) return;
    
    lastRenderedStartRef.current = Date.now();

    const chart = init(chartElementRef.current);
    chartRef.current = chart;

    const formatYAxis = (value: number) => {
      if (unit === 'bytes') {
        if (value >= 1_000_000_000) return (value / 1_000_000_000).toFixed(0) + ' GB/s';
        if (value >= 1_000_000) return (value / 1_000_000).toFixed(0) + ' MB/s';
        if (value >= 1_000) return (value / 1_000).toFixed(0) + ' KB/s';
        return value.toFixed(0) + ' B/s';
      }

      if (value >= 1_000_000) return (value / 1_000_000).toFixed(0) + ' M pkt/s';
      if (value >= 1_000) return (value / 1_000).toFixed(0) + ' k pkt/s';
      return value.toFixed(0) + ' pkt/s';
    };

    chart.setOption(chartOptions);
    chart.setOption({
      xAxis: { dataMin: Date.now() - timeScale * 1000, dataMax: Date.now() },
      yAxis: {
        axisLabel: {
          formatter: formatYAxis
        }
      }
    });

    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(chartElementRef.current);

    const chartElementCopy = chartElementRef.current;

    const handleMouseEnter = () => { isMouseOverRef.current = true; };
    const handleMouseLeave = () => { isMouseOverRef.current = false; };
    chartElementCopy.addEventListener('mouseenter', handleMouseEnter);
    chartElementCopy.addEventListener('mouseleave', handleMouseLeave);

    chart.on('datazoom', function (params) {
      // @ts-expect-error Type is not defined
      const zoomData = params.batch[0];

      if (zoomData.end == 100) showRealTimeRef.current = true;
      else showRealTimeRef.current = false;

      // @ts-expect-error Type is not defined
      zoomStartRef.current = chart.getOption().dataZoom[0].startValue;
      // @ts-expect-error Type is not defined
      zoomEndRef.current = chart.getOption().dataZoom[0].endValue;
    });

    let isDisposed = false;

    const updateChartFromProvider = () => {
      console.log(isDisposed, isDataFetching);
      if (isDisposed || isDataFetching) return;

      const allData = dataProvider.getData();
      let dataToRender: DataPoint[];

      if (isMouseOverRef.current) {
        // Mouse over: keep current perspective, don't trim start
        const start = lastRenderedStartRef.current!;
        dataToRender = allData.filter(p => p.timestamp >= start);
      } else if (showRealTimeRef.current) {
        // Real-time mode: sliding window
        const cutoff = Date.now() - timeScale * 1000;
        const startIdx = allData.findIndex(p => p.timestamp >= cutoff);
        dataToRender = startIdx !== -1 ? allData.slice(startIdx) : [];
        if (dataToRender.length > 0) {
          lastRenderedStartRef.current = dataToRender[0]!.timestamp;
        }
      } else {
        // Zoom mode: show visible range
        const startIdx = allData.findIndex(p => p.timestamp >= (zoomStartRef.current ?? 0));
        const endIdx = allData.findIndex(p => p.timestamp > (zoomEndRef.current ?? Infinity));

        const padding = 10;
        const paddedStart = Math.max(0, startIdx - padding);
        const paddedEnd = endIdx !== -1 
            ? Math.min(allData.length, endIdx + padding)
            : allData.length;
        
        dataToRender = allData.slice(paddedStart, paddedEnd);
      }

      // Map to ECharts format with incomplete point styling
      const receivedPktsData = dataToRender.map(p => ({
        name: p.timestamp,
        value: [p.timestamp, p.packetsInPerSec, p.isActive ? 1 : 0, p.windowMs],
        itemStyle: p.complete ? undefined : { opacity: 0.4 }
      }));

      const sentPktsData = dataToRender.map(p => ({
        name: p.timestamp,
        value: [p.timestamp, p.packetsOutPerSec, p.isActive ? 1 : 0, p.windowMs],
        itemStyle: p.complete ? undefined : { opacity: 0.4 }
      }));

      const receivedBytesData = dataToRender.map(p => ({
        name: p.timestamp,
        value: [p.timestamp, p.bytesInPerSec, p.isActive ? 1 : 0, p.windowMs],
        itemStyle: p.complete ? undefined : { opacity: 0.4 }
      }));

      const sentBytesData = dataToRender.map(p => ({
        name: p.timestamp,
        value: [p.timestamp, p.bytesOutPerSec, p.isActive ? 1 : 0, p.windowMs],
        itemStyle: p.complete ? undefined : { opacity: 0.4 }
      }));

      chart.setOption({
        series: [
          { name: 'Received_pkts', data: receivedPktsData },
          { name: 'Sent_pkts', data: sentPktsData },
          { name: 'Received_bytes', data: receivedBytesData },
          { name: 'Sent_bytes', data: sentBytesData }
        ]
      });

      if (showRealTimeRef.current) {
        chart.setOption({
          xAxis: { dataMin: Date.now() - timeScale * 1000, dataMax: Date.now() }
        });
      } else {
        chart.setOption({
          xAxis: { dataMin: Date.now() - timeScale * 1000, dataMax: Date.now() },
          dataZoom: { startValue: zoomStartRef.current, endValue: zoomEndRef.current }
        });
      }
    };

    const initializeChart = async () => {
      setIsDataFetching(true);
      try {
        await dataProvider.initialize(timeScale);
        const bucketSizeMs = dataProvider.getBucketSize()!;
        
        if (isDisposed) return;

        chart.setOption({
          xAxis: {
            minInterval: bucketSizeMs,
            dataMin: Date.now() - timeScale * 1000,
            dataMax: Date.now()
          },
          dataZoom: [{ minValueSpan: bucketSizeMs * 2 }]
        });

        // Initialize lastRenderedStart after data is loaded
        const allData = dataProvider.getData();
        if (allData.length > 0) {
          const cutoff = Date.now() - timeScale * 1000;
          const startIdx = allData.findIndex(p => p.timestamp >= cutoff);
          if (startIdx !== -1) {
            lastRenderedStartRef.current = allData[startIdx]!.timestamp;
          }
        }

        // Initial render
        updateChartFromProvider();

      } finally {
        setIsDataFetching(false);
      }
    };

    initializeChart();

    const unsubscribeData = dataProvider.subscribe(() => updateChartFromProvider());

    return () => {
      isDisposed = true;
      unsubscribeData();
      dataProvider.dispose();
      resizeObserver.disconnect();
      chart.dispose();
      chartElementCopy?.removeEventListener('mouseenter', handleMouseEnter);
      chartElementCopy?.removeEventListener('mouseleave', handleMouseLeave);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataProvider, timeScale, unit]);

  // Update legend
  useEffect(() => {
    if (!chartRef.current) return;
    chartRef.current.setOption({ legend: { selected: selectedSeries } });
  }, [selectedSeries, timeScale]);

  return (
    <div className={styles.chart_wrapper}>
      {showLoading && (<img src={loadingIcon} className={styles.loading} alt="Loading..." />)}
      <div ref={chartElementRef} className={styles.chart} />
    </div>
  );
}

export default PacketsLineChart;