import auth from '@/services/authentication';

export interface ConnectionParams { channel_id: string };

export const ConnectionStatus = {
    Connecting:    "CONNECTING",
    Connected:     "CONNECTED",
    Disconnecting: "DISCONNECTING",
    Disconnected:  "DISCONNECTED",
    Reconnecting:  "RECONNECTING"
} as const;
export type ConnectionStatus = typeof ConnectionStatus[keyof typeof ConnectionStatus];

export const ActivityStatus = {
    Active:   "ACTIVE",
    Inactive: "INACTIVE"
} as const;
export type ActivityStatus = typeof ActivityStatus[keyof typeof ActivityStatus];

export type ConnectionState = {
    params?: ConnectionParams,
    connectionStatus: ConnectionStatus,
    activityStatus?: ActivityStatus,
    message?: string
};

// This error codes will cause WebSocket reconnection process
const ReconnectionCodes: number[] = [
    1001, // Going Away
    1005, // No Status Rcvd
    1006, // Abnormal Closure
    1011, // Internal Server Error
] as const;

const AutenticationErrorCode = 4001;

const InactivityDelay = 6000; // in ms

/**
 * This singleton service is responsible for WebSocket connection lifecycle 
 */
class WebSocketConnectionService {

    // Connection
    private connection: WebSocket | null = null;
    private scheduledConnectionData: ConnectionParams | null = null;

    private reconnectionAttempt: number = 0;
    private reconnectionTimeout?: number;

    private inactivityTimeout?: number;

    private state: ConnectionState = {
        connectionStatus: ConnectionStatus.Disconnected,
    };

    /**
     * Connect to WebSocket
     * This service handles only one connection in a time.
     * If new connection was initiated, previous closes.
     * @param data connection data
     */
    connect(data: ConnectionParams): void {
        // If connection is already established OR is not fully closed
        // Schedule new connection after closing of the current one.
        if (this.connection) {
            this.scheduledConnectionData = data;
            if (this.connection.readyState !== WebSocket.CLOSING && this.connection.readyState !== WebSocket.CLOSED)
                this.disconnect();
            return;
        }
        
        this.stopReconnection();
        this._connect(data, true);
    }

    /**
     * Helper function to websocket state and notify its listeners
     * @param state Partial state object
     */
    private updateState(state: Partial<ConnectionState>) {
        this.state = {
            ...this.state,
            ...state
        };
        this.stateUpdateListeners.forEach((callback) => callback());
    }

    /**
     * Helper function to create WebSocket connection.
     * @param data connectip parameters
     * @param manually set true whenever connection is requested manually
     */
    private _connect(data: ConnectionParams, manually: boolean = false) {
        console.debug("[WebSocketService] Creating WebSocket connection...");
        this.connection = new WebSocket(`/api/v1/ws/telemetry?channel_id=${data.channel_id}&token=${auth.getToken()}`);
        this.setListeners();

        const newStatus = this.state.connectionStatus === ConnectionStatus.Reconnecting && !manually
                          ? ConnectionStatus.Reconnecting : ConnectionStatus.Connecting;

        this.updateState({
            params: data,
            connectionStatus: newStatus,
            activityStatus: undefined,
            message: undefined
        });
    }

    /**
     * Set listeners for WebSocket connection
     */
    private setListeners() {
        if (!this.connection) return;
        
        this.connection.onopen = () => this.onOpen();
        this.connection.onclose = (event) => this.onClose(event);
        this.connection.onmessage = (event) => this.onMessage(event);
        this.connection.onerror = (error) => {
            if (error instanceof Error) {
                console.error('[WebSocketService] Error: ' + error.message, error.stack);
            }
        };
    }

    private onOpen() {
        console.debug(`[WebSocketService] WebSocket conencted to ${this.state.params?.channel_id}!`);
        this.stopReconnection();
        this.setInactivityTimeout();

        this.updateState({
            connectionStatus: ConnectionStatus.Connected,
            activityStatus: ActivityStatus.Active,
            message: undefined
        });
    }

    /**
     * Initiate reconnection
     */
    private reconnect() {
        this.updateState({
            connectionStatus: ConnectionStatus.Reconnecting,
            activityStatus: undefined,
        });

        this.reconnectionAttempt++;

        const getBackoffDelay = () => {
            const base = 500; // 0.5 second
            const max = 60000; // 60 seconds
            const jitter = Math.random() * 1000;
            return Math.min(base * (2 ** this.reconnectionAttempt) + jitter, max);
        }

        this.reconnectionTimeout = setTimeout(() => {
            console.debug(`[WebSocketService] Reconnection attempt #${this.reconnectionAttempt}.`);
            this._connect(this.state.params!);
        }, getBackoffDelay());
    }

    /**
     * Disconnect from a WebSocket
     * @returns 
     */
    disconnect(): void {
        const isReconnecting = this.state.connectionStatus === ConnectionStatus.Reconnecting;

        // If servies is in the reconnection process but connection is still not initiated
        if (isReconnecting && !this.connection) {
            this.stopReconnection();
            this.updateState({
                connectionStatus: ConnectionStatus.Disconnecting,
                activityStatus: undefined,
                message: undefined
            });
            return;
        }

        if (!this.connection) return;

        console.debug("[WebSocketService] Disconnecting from a WebSocket...");

        this.stopReconnection();
        this.connection.close();

        this.updateState({
            connectionStatus: ConnectionStatus.Disconnecting,
            activityStatus: undefined,
            message: undefined
        });
    }
    
    private onClose(event: CloseEvent) {
        console.debug(`[WebSocketService] WebSocket conenction closed with reason ${event.code}: ${event.reason}.`);

        this.connection = null;
        this.clearInactivityTimeout();

        // If new connection is scheduled, connect.
        if (this.scheduledConnectionData) {
            this.stopReconnection();
            this._connect(this.scheduledConnectionData);
            this.scheduledConnectionData = null;
            return;
        }

        // If reconnection is required, reconnect.
        if (!event.wasClean || ReconnectionCodes.includes(event.code)) {
            this.reconnect();
            return;
        }

        // Otherwise update state to "Disconnected"
        this.updateState({
            params: undefined,
            connectionStatus: ConnectionStatus.Disconnected,
            activityStatus: undefined,
            message: event.reason
        });

        // In case of authentication error
        if (event.code === AutenticationErrorCode) {
            auth.handleAuthError().then(isRenewed => {
                if (!isRenewed) return;

                // Try to reconnect with new access token
                this._connect(this.state.params!);
            });
        }
    }

    private onMessage(event: MessageEvent<string>) {
        if (!this.connection) return;

        this.setInactivityTimeout();

        // Ping/pong
        if (event.data === "ping") {
            this.connection.send("pong");
            return;
        }

        console.debug(`[WebSocketService] WebSocket received a message.`);
        this.messageListeners.forEach((callback) => callback(event.data));
    }

    private stopReconnection() {
        if (this.reconnectionTimeout) {
            clearTimeout(this.reconnectionTimeout);
            this.reconnectionTimeout = undefined;
        }
        this.reconnectionAttempt = 0;
    }

    send(payload: string) {
        if (!this.connection) {
            console.error("[WebSocketService] Failed to send payload through WebSocket connection! Connection is not established.");
            return;
        }
        this.connection.send(payload);
        console.debug("[WebSocketService] Sent payload through WebSocket connection. Payload: " + payload);
    }

    private setInactivityTimeout() {
        this.clearInactivityTimeout();

        this.inactivityTimeout = setTimeout(() => {
            console.debug(`[WebSocketService] Connection was idle for ${Math.floor(InactivityDelay / 1000)}s!`);
            this.updateState({ activityStatus: ActivityStatus.Inactive });
        }, InactivityDelay);
    }

    private clearInactivityTimeout() {
        if (this.inactivityTimeout) clearTimeout(this.inactivityTimeout);
    }


    // Update listeners

    private stateUpdateListeners = new Set<() => void>();
    private messageListeners = new Set<(message: string) => void>;
    
    /**
     * Add listener to WebSocket state updates
     * @param callback Callback function (will be called)
     * @returns Function to unsubscribe
     */
    subscribeState(callback: () => void): () => void {
        this.stateUpdateListeners.add(callback);
        return () => this.stateUpdateListeners.delete(callback);
    }

    /**
     * Add listener to WebSocket message updates
     * @param callback Callback function (will be called) with `message` parameter
     * @returns Function to unsubscribe
     */
    subscribeMessages(callback: (message: string) => void): () => void {
        this.messageListeners.add(callback);
        return () => this.messageListeners.delete(callback);
    }
    
    /**
     * @returns ConnectionState object
     */
    getState(): ConnectionState {
        return this.state;
    }
}

export default new WebSocketConnectionService();