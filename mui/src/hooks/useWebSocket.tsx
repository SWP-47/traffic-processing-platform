import { useSyncExternalStore } from 'react';
import websocket from '@/services/websocket';

export function useWebSocket() {
    return useSyncExternalStore(
        (callback) => websocket.subscribeState(callback),
        () => websocket.getState(),
        () => websocket.getState(),
    );
}
