import { useWebSocket } from "@/hooks/useWebSocket";
import { getHistory } from "@/services/history";
import { useEffect, useState } from "react";

function useAggregationPeriod(timeScale: number) {
    const [aggregationPeriod, setAggregationWindow] = useState<number>(30);
    
    const { params } = useWebSocket();
    const channelId = params?.channel_id;

    // Effect to get aggregationWindow from history response.
    useEffect(() => {
        if (!channelId || !timeScale) return;

        getHistory(channelId, timeScale).then(response => {
        setAggregationWindow(response.interval_sec);
        });
    }, [channelId, timeScale]);

    return aggregationPeriod;
}

export default useAggregationPeriod;