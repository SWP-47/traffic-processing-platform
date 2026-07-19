import { useWebSocket } from "@/hooks/useWebSocket";
import { getBucketInterval } from "@/services/history";
import { useEffect, useState } from "react";

function useAggregationPeriod(timeScale: number) {
    const [aggregationPeriod, setAggregationWindow] = useState<number>(30);
    
    const { params } = useWebSocket();
    const channelId = params?.channel_id;

    useEffect(() => {
        if (!channelId || !timeScale) return;

        getBucketInterval(timeScale).then(response => {
            setAggregationWindow(response.interval_sec);
        });
    }, [channelId, timeScale]);

    return aggregationPeriod;
}

export default useAggregationPeriod;