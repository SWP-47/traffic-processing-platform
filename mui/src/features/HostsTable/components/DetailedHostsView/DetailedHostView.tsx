import { useEffect, useState, type MouseEvent } from 'react';
import styles from './DetailedHostView.module.css';
import closeIcon from '@/assets/close.svg';
import HostPacketsColumnChart from '../HostPacketsColumnChart';
import HostPacketsLineChart from '../HostPacketsLineChart';
import TopDestinationsTable from '../TopDestinationsTable';

interface DetailedHostsViewOptions {
  onClose: () => void,
  ip: string
};

function DetailedHostView({ ip, onClose }: DetailedHostsViewOptions) {
  const [timeScale, setTimeScale] = useState<number>(60 * 5);

  // Configure time scale
  const selectScale = (event: MouseEvent<HTMLButtonElement>) => {
    const newScale = +(event.target as HTMLSpanElement).getAttribute("data-value")!;
    setTimeScale(newScale);
  };

  useEffect(() => {
    // Update CSS classes
    document.querySelectorAll(`.${styles.selector}`).forEach(e => e.classList.remove(styles.active!));
    document.querySelector(`.${styles.selector}[data-value="${timeScale}"]`)?.classList.add(styles.active!);
  }, [timeScale])

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
        <div className={styles.selectors}>
          <button onClick={selectScale} data-value={60 * 5} className={styles.selector}>5m</button>
          <button onClick={selectScale} data-value={60 * 15} className={styles.selector}>15m</button>
          <button onClick={selectScale} data-value={3600} className={`${styles.selector}`}>1h</button>
          <button onClick={selectScale} data-value={3600 * 24} className={styles.selector}>24h</button>
          <button onClick={selectScale} data-value={3600 * 24 * 7} className={styles.selector}>7d</button>
          <button onClick={selectScale} data-value={3600 * 24 * 30} className={styles.selector}>30d</button>
        </div>
      </div>

      <div className={styles.body}>
        <div className={styles.row}>
          <HostPacketsColumnChart ip={ip} />
          <HostPacketsLineChart ip={ip} timeScale={timeScale} />
        </div>
        <div className={styles.row}>
          <TopDestinationsTable ip={ip} />
        </div>
      </div>
    </>
  );
}

export default DetailedHostView;