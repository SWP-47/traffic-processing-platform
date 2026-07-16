import { useState } from 'react';
import styles from './DetailedHostView.module.css';
import closeIcon from '@/assets/close.svg';
import HostPacketsColumnChart from '../HostPacketsColumnChart';
import HostPacketsLineChart from '../HostPacketsLineChart';
import TopDestinationsTable from '../TopDestinationsTable';
import AggregationSelector from '../AggregationSelector/AggregationSelector';
import useAggregationPeriod from '../../hooks/useAggregationPeriod';
import { secondsToHumanReadable } from '@/utils/time';
import UnitToggle from '@/components/Header/components/UnitToggle/UnitToggle';

interface DetailedHostsViewOptions {
  onClose: () => void,
  ip: string,
  defaultTimeScale?: number
};

function DetailedHostView({ ip, onClose, defaultTimeScale }: DetailedHostsViewOptions) {
  const [timeScale, setTimeScale] = useState<number>(defaultTimeScale ?? 600);
  const aggregationPeriod = useAggregationPeriod(timeScale ?? 1);

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
          <UnitToggle />
        </div>
        <div className={styles.right}>
          <p
            className={styles.aggregaion_period}
            title={`Data is aggregated for the last ${secondsToHumanReadable(aggregationPeriod)}`}
          >
            AG: {secondsToHumanReadable(aggregationPeriod)}
          </p>
          <AggregationSelector onTimeScaleChange={(value) => setTimeScale(value)} defaultValue={timeScale} />
        </div>
      </div>

      <div className={styles.body}>
        <div className={styles.row}>
          <HostPacketsColumnChart ip={ip} aggregationPeriod={aggregationPeriod} />
          <HostPacketsLineChart ip={ip} timeScale={timeScale} />
        </div>
        <div className={styles.row}>
          <TopDestinationsTable ip={ip} aggregationPeriod={aggregationPeriod} />
        </div>
      </div>
    </>
  );
}

export default DetailedHostView;