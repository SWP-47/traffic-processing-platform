import auth from '@/services/authentication';

export interface ConnectionData {
    channel_id: string
};

export type ConnectionStatus = 
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'disconnecting'
  | 'disconnected';

export type ConnectionState = {
    connectionStatus: ConnectionStatus,
    message: string | null,
    channelId: string | null
};

const WS_ERROR_CODE = {
    'invalid_token': 4001,
    'missing_channel': 4002,
    'channel_forbidden': 4003,
    'channel_not_found': 4004,
    'internal_error': 1011
}

class WebSocketConnectionService {
    private stateListeners = new Set<() => void>();
    private updatesListeners: { [index: string]: Set<(update: unknown) => void> } = {};
    
    subscribeState(callback: () => void): () => void {
        this.stateListeners.add(callback);
        return () => this.stateListeners.delete(callback);
    }

    subscribeUpdate(updateType: string, callback: (update: unknown) => void): () => void {
        if (this.updatesListeners[updateType] === undefined) {
            this.updatesListeners[updateType] = new Set<(update: unknown) => void>;
        }

        this.updatesListeners[updateType].add(callback);
        return () => this.updatesListeners[updateType]?.delete(callback);
    }
    
    getState(): ConnectionState {
        return this.state;
    }
    
    private notifyAllStateListeners(): void {
        this.stateListeners.forEach((callback) => callback());
    }

    private notifyAllUpdateListeners(updateType: string, update: unknown): void {
        this.updatesListeners[updateType]?.forEach((callback) => callback(update));
    }

    // Connection
    private connection: WebSocket | null = null;
    private lastConnectionData: ConnectionData | null = null;
    private followingConnectionData: ConnectionData | null = null;

    private reconnectionAttempt: number = 0;
    private reconnectionTimeout: number | undefined;

    private state: ConnectionState = {
        connectionStatus: 'idle',
        message: null,
        channelId: null
    }

    send(payload: string) {
        if (!this.connection) {
            console.error("[WebSocketService] Failed to sent payload through WS connection! Connection is not established.");
            return;
        }
        this.connection?.send(payload);
        console.debug("[WebSocketService] Sent payload through WS connection. Payload: " + payload);
    }

    /**
     * Connect to WebSocket
     * This service handles only one connection in a time.
     * If new connection was initiated, previous closes.
     * @param data connection data
     */
    connect(data: ConnectionData): void {
        // If connection is already established OR is not fully closed
        // Schedule new connection after closing of the current one.
        if (this.connection) {
            this.followingConnectionData = data;
            if (this.connection.readyState != WebSocket.CLOSING && this.connection.readyState != WebSocket.CLOSED)
                this.disconnect();    
            return;
        }
        
        this._connect(data);
    }

    private _connect(data: ConnectionData) {
        console.debug("[WebSocketService] Connecting to a WebSocket.", data);
        this.lastConnectionData = data;
        this.connection = new WebSocket(`/api/v1/ws/telemetry?channel_id=${data.channel_id}&token=${auth.getToken()}`);
        this.setListeners();

        this.state = {
            ...this.state,
            connectionStatus: 'connecting',
            channelId: data.channel_id
        };
        this.notifyAllStateListeners();
    }

    private setListeners() {
        if (!this.connection) return;
        
        this.connection.onopen = () => this.onOpen();
        this.connection.onclose = (event) => this.onClose(event);
        this.connection.onmessage = (event) => this.onMessage(event);
        this.connection.onerror = (error) => {
            console.error('[WebSocketService] WebSocket error:', error);
        };
    }

    private onOpen() {
        console.debug("[WebSocketService] Connected!");
        this.stopReconnection();

        this.state = {
            ...this.state,
            connectionStatus: 'connected'
        };
        this.notifyAllStateListeners();
    }

    private reconnect() {
        this.reconnectionAttempt++;

        const getBackoffDelay = () => {
            const base = 500; // 0.5 second
            const max = 60000; // 60 seconds
            const jitter = Math.random() * 1000;
            return Math.min(base * (2 ** this.reconnectionAttempt) + jitter, max);
        }

        this.reconnectionTimeout = setTimeout(() => {
            console.debug(`[WebSocketService] Reconnection attempt #${this.reconnectionAttempt}.`);
            this._connect(this.lastConnectionData!);
        }, getBackoffDelay());
    }

    /**
     * Disconenct from WebSocket
     * @returns 
     */
    disconnect(): void {
        if (!this.connection) return;
        console.debug("[WebSocketService] Disconnecting from a WebSocket.", this.lastConnectionData);

        this.stopReconnection();
        this.connection.close();

        this.state = {
            ...this.state,
            connectionStatus: 'disconnecting'
        };
        this.notifyAllStateListeners();
    }
    
    private onClose(event: CloseEvent) {
        console.debug(`[WebSocketService] WebSocket closed with code ${event.code}.`, this.lastConnectionData);

        this.connection = null;

        // If the user manually disconnected, set IDLE satus, otherwise DISCONNECTED
        this.state = {
            connectionStatus: this.state.connectionStatus === 'disconnecting' ? 'idle' : 'disconnected',
            message: event.reason || null,
            channelId: null
        };
        this.notifyAllStateListeners();

        // If new connection is scheduled, connect.
        if (this.followingConnectionData) {
            this.stopReconnection();
            this._connect(this.followingConnectionData);
            this.followingConnectionData = null;
            return;
        }

        // If connection failed before handshake, try to reconnect.
        if (!event.wasClean) {
            this.reconnect();
            return;
        }

        if (event.code === WS_ERROR_CODE.invalid_token) {
            auth.requestTokenRenewal();
            // this.reconnect();
            return;
        }

        // Reconnect on server error
        const NOT_RECONNECT_CODES = [4001, 4002, 4003, 4004]
        if (!NOT_RECONNECT_CODES.includes(event.code)) {
            this.reconnect();
            return;
        }
    }

    private onMessage(event: MessageEvent) {
        // Ping/pong
        if (event.data === "ping") {
            this.connection!.send("pong");
            return;
        }

        try {
            console.debug(`[WebSocketService] WebSocket received an update.`);
            const data = JSON.parse(event.data);
            if (!data.type) return;

            this.notifyAllUpdateListeners(data.type, data);
        } catch (e) {
            console.error('[WebSocketService] Failed to parse an update:', e);
        }
    }

    private stopReconnection() {
        if (this.reconnectionTimeout) {
            clearTimeout(this.reconnectionTimeout);
            this.reconnectionTimeout = undefined;
        }
        this.reconnectionAttempt = 0;
    }
}

export default new WebSocketConnectionService();