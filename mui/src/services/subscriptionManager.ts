import websocket, { ActivityStatus, ConnectionStatus } from "./websocket";
import type { components } from '@/api/schema';

type WSControlMessage = components["schemas"]["WSControlMessage"];
export type Update = Record<string, unknown>;
export type SubscriptionTarget = WSControlMessage["target"];
export type SubscriptionParams = Record<string, unknown>;

export interface SubscriptionData {
    id: WSControlMessage["id"]
    target: WSControlMessage["target"]
    params: WSControlMessage["params"]
    updateCallbacks: Set<(update: Update) => void>,
    inactivityCallbacks: Set<() => void>,
    lastUpdate: Update | null
};

class SubscriptionManager {
    private subscriptions: Record<string, SubscriptionData> = {};
    private keyToId: Record<string, string> = {};

    constructor() {
        websocket.subscribeState(() => {
            const state = websocket.getState();

            // If new WebSocket state is Connected, reconnect all active subscriptions
            if (state.connectionStatus === ConnectionStatus.Connected) {
                Object.values(this.subscriptions).forEach(sub => this.requestWebsocketAction('subscribe', sub));
            }

            // Otherwise there will be no new updates until connection is restored, notify listeners about inactivity
            if (state.connectionStatus !== ConnectionStatus.Connected || state.activityStatus === ActivityStatus.Inactive) {
                Object.values(this.subscriptions).forEach(sub => {
                    sub.inactivityCallbacks.forEach(cb => cb());
                });
            }
        });

        websocket.subscribeMessages(message => {
            try {
                const update = JSON.parse(message) as Update;

                if (!update.type || typeof update.type !== 'string') return;
                if (!update.id || typeof update.id !== 'string') return;

                if (this.subscriptions[update.id] === undefined) {
                    console.warn("[SubscriptionManager] Cannot route the update, such ID is not registered!");
                    return;
                }
                
                this.subscriptions[update.id]!.lastUpdate = update;
                this.subscriptions[update.id]!.updateCallbacks.forEach(cb => cb(update));
            } catch (error) {
                if (error instanceof Error) {
                    console.error("[SubscriptionManager] Error occur while parsing an update: " + error.message, error.stack);
                }
            }
        })
    }

    subscribe(
        target: SubscriptionTarget,
        params: SubscriptionParams,
        updateCallback: (update: Update) => void,
        inactivityCallback: () => void
    ): () => void {
        const key = this.getKey(target, params);
        const webSocketState = websocket.getState();

        let id = this.keyToId[key];

        if (id === undefined) {
            id = crypto.randomUUID();
            this.keyToId[key] = id;
        }

        let sub = this.subscriptions[id];

        if (sub === undefined) {
            sub = {
                id: id,
                target: target,
                params: params as WSControlMessage["params"],
                updateCallbacks: new Set(),
                inactivityCallbacks: new Set(),
                lastUpdate: null
            };

            this.subscriptions[id] = sub;

            // Request a subscription if WebSocket conenction is established.
            if (webSocketState.connectionStatus === ConnectionStatus.Connected) {
                this.requestWebsocketAction('subscribe', sub);
            }
        }

        sub.updateCallbacks.add(updateCallback);

        // If lastUpdate exist, send it to updateCallback to prevent delays
        if (sub.lastUpdate !== null) {
            updateCallback(sub.lastUpdate);
        }

        // Subscription is inactive, call inactivity callback
        if (webSocketState.connectionStatus !== ConnectionStatus.Connected) {
            inactivityCallback();
        }

        const unsubscribe = () => {
            const currentSub = this.subscriptions[id];
            if (currentSub === undefined) return;

            currentSub.updateCallbacks.delete(updateCallback);
            currentSub.inactivityCallbacks.delete(inactivityCallback);

            // If no one listens, clear subscription
            if (currentSub.updateCallbacks.size === 0) {
                const webSocketState = websocket.getState();
                if (webSocketState.connectionStatus === ConnectionStatus.Connected) {
                    this.requestWebsocketAction('unsubscribe', currentSub);
                }

                delete this.subscriptions[id];
                delete this.keyToId[key];

                console.debug(`[SubscriptionManager] Subscription ${key.slice(0, 10)}... is removed as there is no listeners.`);
            }
        };

        return unsubscribe; 
    }

    getKey(target: SubscriptionTarget, params: SubscriptionParams): string {
        return this.getObjectHash({ target, params });
    }

    private getObjectHash(obj: unknown): string {
        // Primitives and null
        if (obj === null || obj === undefined) {
            return JSON.stringify(obj);
        }
    
        if (typeof obj === 'string' || typeof obj === 'number' || typeof obj === 'boolean') {
            return JSON.stringify(obj);
        }
    
        // Arrays
        if (Array.isArray(obj)) {
            return '[' + obj.map(item => this.getObjectHash(item)).join(',') + ']';
        }
    
        // Objects
        if (typeof obj === 'object') {
            const record = obj as Record<string, unknown>;
            const sortedKeys = Object.keys(record).sort();
            const sortedObj: Record<string, unknown> = {};
        
            for (const key of sortedKeys) {
                sortedObj[key] = this.getObjectHash(record[key]);
            }
        
            return JSON.stringify(sortedObj);
        }
    
        // Fallback for other types
        return '';
    }

    private requestWebsocketAction(action: WSControlMessage["action"], data: SubscriptionData): void {
        const webSocketState = websocket.getState();

        if (webSocketState.connectionStatus !== ConnectionStatus.Connected || !webSocketState.params) {
            console.warn(`[SubscriptionManager] Cannot request a ${action} action until the WebSocket connection is established!`);
            return;
        }

        const payload: WSControlMessage = {
            action: action,
            id: data.id,
            channel_id: webSocketState.params.channel_id,
            target: data.target,
            params: data.params
        }

        websocket.send(JSON.stringify(payload));
    }
}

export default new SubscriptionManager();