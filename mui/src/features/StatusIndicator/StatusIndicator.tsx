import { useTelemetrySelector } from '@/hooks/useTelemetry';
import styles from './StatusIndicator.module.css';

function StatusIndicator() {
  const channelId = useTelemetrySelector((tel) => tel?.data.channel_id);
  const isActive = useTelemetrySelector((tel) => tel?.data.is_active);

  const WSStatus = useTelemetrySelector((tel) => tel?.status);
  const WSError = useTelemetrySelector((tel) => tel?.error);

  let cardStyle: string = 'card';
  let message: string = '';

  if (WSStatus == 'disconnected') {
    cardStyle = styles.error!;
    message = WSError!;
  } else if (WSStatus == 'connecting') {
    cardStyle = 'card';
    message = 'connecting to CnSS...';
  } else if (WSStatus == 'connected' && isActive) {
    cardStyle = styles.active!;
    message = 'online';
  } else if (WSStatus == 'connected' && !isActive) {
    cardStyle = 'card';
    message = 'no traffic';
  }

  return (
    <div className={`${styles.status_indicator} ${cardStyle}`}>
      <h1 className={styles.channel_id}>{channelId || 'Select a channel'}</h1>
      <h1 className={styles.channel_status}>{message}</h1>
    </div>
  );
}

export default StatusIndicator;