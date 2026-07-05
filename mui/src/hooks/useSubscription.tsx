import subscriptionManager from "@/services/subscriptionManager";
import { useEffect, useState } from "react";
import { useWebSocket } from "./useWebSocket";

type Validator<T> = (data: unknown) => data is T;

export function useSubscription<T>(params: Record<string, unknown>, validator?: Validator<T>): T | null {
    const [data, setData] = useState<T | null>(null);
    const { connectionStatus } = useWebSocket();

    const key = subscriptionManager.getKeyFromParams(params);
    
    useEffect(() => {
        if (connectionStatus !== 'connected') return;
        const handleUpdate = (update: unknown) => {
            if (validator && !validator(update)) return;
            setData(update as T);
        }

        subscriptionManager.subscribe(params, handleUpdate);
        return () => subscriptionManager.unsubscribe(params, handleUpdate);

    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [key, connectionStatus]); // Key - is an object hash, it will change if object fields changed.

    return data;
}
