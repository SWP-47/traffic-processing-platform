import { getChannels } from '@/services/channels';
import { useState, useEffect, useRef, useCallback } from 'react';
import styles from './ChannelSelector.module.css';
import websocket from '@/services/websocket';
import selectIcon from '@/assets/select.svg';
import infoIcon from '@/assets/info.svg';
import loadingIcon from '@/assets/loading.svg';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useTelemetrySelector } from '@/hooks/useTelemetry';
import useDelayedVisibility from '../../hooks/useDelayedVisibility';

type Channel = { id: string; active: boolean };

const LOADING_DELAY_MS = 300;

// ---------- Tooltip ----------
interface StatusTooltipProps {
  connectionStatus: string;
  message: string | null;
  selectedChannelId: string;
  channelIsActive?: boolean;
  batchesLoss?: number;
}

function StatusTooltip({
  connectionStatus,
  message,
  selectedChannelId,
  channelIsActive,
  batchesLoss,
}: StatusTooltipProps) {
  const isConnected = connectionStatus === 'connected';
  const isConnecting = connectionStatus === 'connecting';
  console.log(message)

  const fields = [
    { key: 'Channel ID', value: selectedChannelId },
    { key: 'WebSocket', value: isConnected || isConnecting ? connectionStatus : message ?? 'unknown' },
    {
      key: 'Channel Status',
      value: isConnected
        ? channelIsActive ? 'active' : 'inactive'
        : '-',
    },
    { key: 'Batches Loss', value: isConnected ? (batchesLoss ?? 0) : '-' },
  ];

  return (
    <div className={styles.tooltip}>
      {fields.map(({ key, value }) => (
        <div key={key} className={styles.field}>
          <span className={styles.key}>{key}:</span>
          <span className={styles.value}>{value}</span>
        </div>
      ))}
    </div>
  );
}

// ---------- Selector ----------
function ChannelSelector() {
  const [isOpened, setIsOpened] = useState(false);
  const [showError, setShowError] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannelId, setSelectedChannelId] = useState('');

  const { connectionStatus, message } = useWebSocket();

  const channelIsActive = useTelemetrySelector((tel) => tel?.is_active);
  const batchesLoss = useTelemetrySelector((tel) => tel?.dropped_batches);

  const selectorRef = useRef<HTMLDivElement>(null);

  const showLoadingIndicator = useDelayedVisibility(isLoading, LOADING_DELAY_MS);

  // ---- Fetch channels ----
  const fetchChannels = useCallback(async () => {
    setIsLoading(true);

    try {
      const response = await getChannels();
      const list: Channel[] = (response.channels ?? []).map((ch) => ({
        id: ch.channel_id!,
        active: ch.is_active!,
      }));

      setChannels(list);
      setShowError(false);

      if (list.length === 0) setSelectedChannelId('');
    } catch {
      setShowError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ---- WebSocket connection ----
  useEffect(() => {
    if (!selectedChannelId) return;
    websocket.connect({ channel_id: selectedChannelId });

    return () => {
      websocket.disconnect();
    };
  }, [selectedChannelId]);

  // ---- Close on events ----
  useEffect(() => {
    if (!isOpened) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (selectorRef.current && !selectorRef.current.contains(event.target as Node)) {
        setIsOpened(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpened(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpened]);

  // ---- Render helpers ----
  const hasConnection = connectionStatus !== 'idle';
  const isConnected = connectionStatus === 'connected';

  let badgeClass: string;
  let badgeLabel: string;

  if (isConnected) {
    badgeClass = channelIsActive ? styles.active_badge! : styles.inactive_badge!;
    badgeLabel = channelIsActive ? 'active' : 'inactive';
  } else {
    badgeClass = styles.error_badge!;
    badgeLabel = 'error';
  }

  const handleHeaderClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpened((prev) => !prev);
    fetchChannels();
  };

  const handleChannelSelect = (id: string) => {
    setSelectedChannelId(id);
    setIsOpened(false);
  };

  // ---- Render ----
  return (
    <div ref={selectorRef} className={`${styles.selector} ${isOpened ? styles.opened : ''}`}>
      <div className={styles.header} onClick={handleHeaderClick}>
        <img src={selectIcon} className={styles.select_icon} alt="" />
        <span className={styles.channel_name}>
          {selectedChannelId || 'Select a channel'}
        </span>

        {hasConnection && (
          <>
            {connectionStatus === 'connecting' || connectionStatus === 'disconnecting' ? (
              <span className={`${styles.activity_badge} ${styles.inactive_badge}`}>
                <img src={loadingIcon} className={styles.connecting_icon} alt="Connecting..." />
              </span>
            ) : (
              <span className={`${styles.activity_badge} ${badgeClass}`}>
                {badgeLabel}
              </span>
            )}
            <div className={styles.info}>
              <img src={infoIcon} className={styles.info_icon} alt="" />
              <StatusTooltip
                connectionStatus={connectionStatus}
                message={message!}
                selectedChannelId={selectedChannelId}
                channelIsActive={channelIsActive}
                batchesLoss={batchesLoss}
              />
            </div>
          </>
        )}
      </div>

      <div className={styles.content}>
        {showError ? (
          <p className={styles.message}>Error: could not connect to CnSS</p>
        ) : showLoadingIndicator ? (
          <img src={loadingIcon} className={styles.loading} alt="Loading..." />
        ) : (
          channels.map((channel) => (
            <p
              key={channel.id}
              className={styles.item}
              data-active={channel.active}
              onClick={() => handleChannelSelect(channel.id)}
            >
              {channel.id}
            </p>
          ))
        )}
      </div>
    </div>
  );
}

export default ChannelSelector;