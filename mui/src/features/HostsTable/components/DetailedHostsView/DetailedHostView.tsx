import { useEffect, useState } from 'react';
import styles from './DetailedHostView.module.css';
import closeIcon from '@/assets/close.svg';
import HostPacketsColumnChart from '../HostPacketsColumnChart';
import HostPacketsLineChart from '../HostPacketsLineChart';
import TopDestinationsTable from '../TopDestinationsTable';
import AggregationSelector from '../AggregationSelector/AggregationSelector';
import { getHostHistory } from '@/services/history';
import { useWebSocket } from '@/hooks/useWebSocket';

interface DetailedHostsViewOptions {
  onClose: () => void,
  ip: string
};

function DetailedHostView({ ip, onClose }: DetailedHostsViewOptions) {
  const [timeScale, setTimeScale] = useState<number | undefined>();
  const [aggregationPeriod, setAggregationWindow] = useState<number>(30);

  const { params } = useWebSocket();
  const channelId = params?.channel_id;

  // Effect to get aggregationWindow from history response.
  useEffect(() => {
    if (!channelId || !timeScale) return;

    getHostHistory(channelId, ip, timeScale).then(response => {
      setAggregationWindow(response.interval_sec);
    });
    
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channelId, timeScale]); // Change only on timeScale or channelId change to prevent redundant requests.

  return (
    <>
      <div className={styles.header}>
        <div className={styles.left}>
          <div className={styles.close_button} onClick={() => onClose()}>
            <img src={closeIcon} alt="Close" />
          </div>
          <h1 className={styles.title}>
            {ip}
          </h1>
        </div>
        <AggregationSelector onTimeScaleChange={(value) => setTimeScale(value)} />
      </div>

      <div className={styles.body}>
        <div className={styles.row}>
          <HostPacketsColumnChart ip={ip} aggregationPeriod={aggregationPeriod} />
          <HostPacketsLineChart ip={ip} timeScale={timeScale ?? 300} />
        </div>
        <div className={styles.row}>
          <TopDestinationsTable ip={ip} aggregationPeriod={aggregationPeriod} />
        </div>
      </div>
    </>
  );
}

export default DetailedHostView;