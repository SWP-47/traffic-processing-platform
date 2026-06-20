/**
 * This file provieds TelemetryService singleton object that works with telemetry WebSocket.
 * Only one concurrent conenction can be opened.
 * After INACTIVITY_TIMEOUT ms servise updates telemetry info so that channel is inactive and metrics are zero. 
 */

import type { TelemetryConnectionData, TelemetryUpdate } from "./types";

const WS_ERROR_CODE = {
    'invalid_token': 4001,
    'missing_channel': 4002,
    'channel_forbidden': 4003,
    'channel_not_found': 4004,
    'internal_error': 1011
}

const INACTIVITY_TIMEOUT = 6000; // in ms.

export class TelemetryStateManager {
    private lastUpdate: TelemetryUpdate | null = null;
    private listeners = new Set<() => void>();
    
    subscribe(callback: () => void): () => void {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }
    
    getLastUpdate(): TelemetryUpdate | null {
        return this.lastUpdate;
    }
    
    update(data: unknown): void {
        if (!this.validate(data)) {
            console.warn('Invalid telemetry update:', data);
            return;
        }

        this.lastUpdate = data;
        this.notifyAll();
    }
    
    private notifyAll(): void {
        this.listeners.forEach((callback) => callback());
    }
    
    validate(data: unknown): data is TelemetryUpdate {
        if (!data || typeof data !== 'object') return false;

        const d = data as Record<string, unknown>;

        if (d.type !== 'telemetry_update') return false;
        if (typeof d.channel_id !== 'string') return false;
        if (typeof d.is_active !== 'boolean') return false;
        if (typeof d.window_ms !== 'number') return false;
        if (typeof d.dropped_batches !== 'number') return false;
        if (typeof d.timestamp !== 'string') return false;
        if (typeof d.received_at !== 'string') return false;

        const m = d.metrics as Record<string, unknown>;
        if (typeof m !== 'object' || m === null) return false;

        const out = m.direction_out as Record<string, unknown>;
        if (typeof out !== 'object' || out === null) return false;
        if (out.packets_per_sec !== undefined && typeof out.packets_per_sec !== 'number') return false;
        if (out.packets !== undefined && typeof out.packets !== 'number') return false;

        const inn = m.direction_in as Record<string, unknown>;
        if (typeof inn !== 'object' || inn === null) return false;
        if (inn.packets_per_sec !== undefined && typeof inn.packets_per_sec !== 'number') return false;
        if (inn.packets !== undefined && typeof inn.packets !== 'number') return false;
          
        return true;
    }
}

class TelemetryService {
    // Authentication
    private token: string = "";

    // Connection
    private connection: WebSocket | null = null;

    private lastConnectionData: TelemetryConnectionData | null = null;
    private followingConnectionData: TelemetryConnectionData | null = null;

    private reconnectionAttempt: number = 0;
    private reconnectionTimeout: number | undefined;

    private inactivityTimer: number | undefined;
    
    // State
    private stateManager = new TelemetryStateManager();

    /**
     * Add new subscriber to telemery updates
     * @param callback 
     * @returns function to unsibscribe
     */
    subscribe(callback: () => void): () => void {
        return this.stateManager.subscribe(callback);
    }
    
    /**
     * @returns last update of telemetry
     */
    getLastUpdate(): TelemetryUpdate | null {
        return this.stateManager.getLastUpdate();
    }

    /**
     * Set token that is used when connecting to WebSocket 
     * @param token Bareer token
     * @see /api/README.md
     */
    setAuthenticationToken(token: string): void {
        this.token = token;
    }


    // WebSocket handling
    /**
     * Connect to WebSocket
     * This service handles only one conenction in a time.
     * If new conenction was initiated, previous closes.
     * @param data connection data
     */
    connect(data: TelemetryConnectionData): void {
        // If connection is already established OR is not fully closed
        // Schedule new conenction after closing of the current one.
        if (this.connection) {
            this.followingConnectionData = data;
            if (this.connection.readyState != WebSocket.CLOSING) this.disconnect();    
            return;
        }
        
        this._connect(data);
    }

    private _connect(data: TelemetryConnectionData) {
        this.lastConnectionData = data;
        this.connection = new WebSocket(`/api/v1/ws/telemetry?channel_id=${data.channel_id}&token=${this.token}`);
        this.setListeners();
    }

    private setListeners() {
        if (!this.connection) return;
        
        this.connection.onopen = () => this.onOpen();
        this.connection.onclose = (event) => this.onClose(event);
        this.connection.onmessage = (event) => this.onMessage(event);
        this.connection.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    onOpen() {
        this.updateInactivityTimer();
        this.stopReconnection();
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
            this._connect(this.lastConnectionData!);
        }, getBackoffDelay());
    }

    /**
     * Disconenct from WebSocket
     * @returns 
     */
    disconnect(): void {
        if (!this.connection) return;
        this.stopReconnection();
        this.connection.close();
    }
    
    private onClose(event: CloseEvent) {
        console.warn(`WebSocket closed with code ${event.code}.`);

        this.connection = null;
        this.clearInactivityTimer();

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
        
        // Reconnect on server error
        if (event.code === WS_ERROR_CODE.internal_error) {
            this.reconnect();
            return;
        }
    }

    private onMessage(event: MessageEvent) {
        this.updateInactivityTimer();
        try {
            const data = JSON.parse(event.data);
            this.stateManager.update(data);            
        } catch (e) {
            console.error('Failed to parse telemetry:', e);
        }
    }

    private updateInactivityTimer(): void {
        this.clearInactivityTimer();

        this.inactivityTimer = window.setTimeout(() => {
            this.stateManager.update(this.getInactiveUpdateObject());
        }, INACTIVITY_TIMEOUT);
    }

    private clearInactivityTimer(): void {
        if (!this.inactivityTimer) return;

        clearTimeout(this.inactivityTimer);
        this.inactivityTimer = undefined;
    }

    private stopReconnection() {
        if (this.reconnectionTimeout) {
            clearTimeout(this.reconnectionTimeout);
            this.reconnectionTimeout = undefined;
        }
        this.reconnectionAttempt = 0;
    }

    private getInactiveUpdateObject(): TelemetryUpdate {
        return {
            type: 'telemetry_update',
            channel_id: this.lastConnectionData?.channel_id || '',
            is_active: false,
            window_ms: 0,
            dropped_batches: 0,
            metrics: {
                direction_in: { packets: 0, packets_per_sec: 0 },
                direction_out: { packets: 0, packets_per_sec: 0 },
            },
            timestamp: new Date().toISOString(),
            received_at: new Date().toISOString(),
        };
    }
}

export default new TelemetryService();