import styles from './StatusIndicator.module.css';
import type { StatusIndicatorData } from '../../types';

function StatusIndicator({ channel_id, channel_active, channel_status_message }: StatusIndicatorData) {
  return (
    <div className={`${styles.status_indicator} ${channel_active ? styles.active : "card"}`}>
      <h1 className={styles.channel_id}>{channel_id}</h1>
      <h1 className={styles.channel_status}>{channel_status_message}</h1>
    </div>
  );
}

export default StatusIndicator;