import { getChannels } from '@/services/channels';
import { useState, useEffect } from 'react';
import styles from './ChannelSelector.module.css';
import telemetry from '@/services/telemetry';

function ChannelSelector() {
  const [channels, setChannels] = useState<string[]>([]);
  const [selectedChannelId, setSelectedChannelId] = useState<string>('');

  const updateChannelsList = async () => {
    const response = await getChannels();

    const idsList = response.channels!.map(ch => ch.channel_id!);
    if (channels.length > 0 && idsList.length === 0) setSelectedChannelId(''); 
    setChannels(idsList);
  };

  useEffect(() => {
    const connectChannel = async (channelId: string) => {
      if (channelId === '') return;
      telemetry.connect({ channel_id: channelId });
    };
    connectChannel(selectedChannelId);
  }, [selectedChannelId]);

  useEffect(() => {
    // TODO: fix loading
    updateChannelsList();
  }, []);

  return (
    <select
      className={styles.select}
      defaultValue=""
      value={selectedChannelId}
      onFocus={updateChannelsList}
      onChange={(e) => setSelectedChannelId(e.target.value)}>
        <option value="" disabled className={styles.option} style={{display: 'none'}}>Select a channel</option>
        {
          channels.map((channelId, i) => (
            <option key={i} value={channelId} className={styles.option}>{channelId}</option>
          ))
        }
    </select>
  );
}

export default ChannelSelector;