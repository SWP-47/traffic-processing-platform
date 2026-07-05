import { useEffect, useSyncExternalStore } from 'react';
import telemetryService, { type TelemetryUpdate } from '@/services/telemetry';
import subscriptionManager from '@/services/subscriptionManager';
import { useWebSocket } from './useWebSocket';

export function useTelemetrySelector<T>(
    selector: (data: TelemetryUpdate | null) => T
): T {
    const { connectionStatus } = useWebSocket();
    useEffect(() => {
        if (connectionStatus !== 'connected') return;
        const handleUpdate = () => {};
        const params = {
            target: 'telemetry',
            params: {
                "window_sec": 5.0
            }
        }
        console.log('lasllas')
        subscriptionManager.subscribe(params, handleUpdate)
        return () => subscriptionManager.unsubscribe(params, handleUpdate);
    }, [connectionStatus])
    
    return useSyncExternalStore(
        telemetryService.subscribe.bind(telemetryService),
        () => selector(telemetryService.getLastUpdate()),
        () => selector(telemetryService.getLastUpdate())
    );
}
