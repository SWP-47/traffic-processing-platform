/**
 * This file provides TelemetryService singleton object that works with telemetry WebSocket.
 * Only one concurrent connection can be opened.
 * After INACTIVITY_TIMEOUT ms service updates telemetry info so that channel is inactive and metrics are zero. 
 */

import type { components } from "@/api/schema";
import auth from "./authentication";

export type TelemetryUpdate = components["schemas"]["TelemetryUpdate"];
export type TelemetryConnectionStatus = 
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'error';


export interface TelemetryState {
    data: TelemetryUpdate,
    status: TelemetryConnectionStatus,
    error: string | null 
}

export interface TelemetryConnectionData {
    channel_id: string
};

const WS_ERROR_CODE = {
    'invalid_token': 4001,
    'missing_channel': 4002,
    'channel_forbidden': 4003,
    'channel_not_found': 4004,
    'internal_error': 1011
}

const INACTIVITY_TIMEOUT = 6000; // in ms.

class TelemetryStateManager {
    private lastUpdate: TelemetryState | null = null;
    private listeners = new Set<() => void>();
    
    subscribe(callback: () => void): () => void {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }
    
    getLastUpdate(): TelemetryState | null {
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
    
    validate(data: unknown): data is TelemetryState {
        if (!data || typeof data !== 'object') return false;

        const a = data as Record<string, unknown>;

        if (typeof a.status !== 'string') return false;
        if (!a.data || typeof a.data !== 'object') return false;

        const d = a.data as Record<string, unknown>;

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
     * @returns function to unsubscribe
     */
    subscribe(callback: () => void): () => void {
        return this.stateManager.subscribe(callback);
    }
    
    /**
     * @returns last update of telemetry
     */
    getLastUpdate(): TelemetryState | null {
        return this.stateManager.getLastUpdate();
    }

    // WebSocket handling
    /**
     * Connect to WebSocket
     * This service handles only one connection in a time.
     * If new connection was initiated, previous closes.
     * @param data connection data
     */
    connect(data: TelemetryConnectionData): void {
        // If connection is already established OR is not fully closed
        // Schedule new connection after closing of the current one.
        if (this.connection) {
            this.followingConnectionData = data;
            if (this.connection.readyState != WebSocket.CLOSING) this.disconnect();    
            return;
        }
        
        this._connect(data);
    }

    private _connect(data: TelemetryConnectionData) {
        console.debug("[TelemetryService] Connecting to a WebSocket.", data);
        this.lastConnectionData = data;
        this.connection = new WebSocket(`/api/v1/ws/telemetry?channel_id=${data.channel_id}&token=${auth.getToken()}`);
        this.setListeners();

        this.stateManager.update({
            ...this.getInactiveUpdateObject(),
            status: 'connecting',
            error: null
        } as TelemetryState)
    }

    private setListeners() {
        if (!this.connection) return;
        
        this.connection.onopen = () => this.onOpen();
        this.connection.onclose = (event) => this.onClose(event);
        this.connection.onmessage = (event) => this.onMessage(event);
        this.connection.onerror = (error) => {
            console.error('[TelemetryService] WebSocket error:', error);
        };
    }

    private onOpen() {
        console.debug("[TelemetryService] Connected!");
        this.updateInactivityTimer();
        this.stopReconnection();

        this.stateManager.update({
            ...this.getInactiveUpdateObject(),
            status: 'connected',
            error: null
        } as TelemetryState)
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
            console.debug(`[TelemetryService] Reconnection attempt #${this.reconnectionAttempt}.`);
            this._connect(this.lastConnectionData!);
        }, getBackoffDelay());
    }

    /**
     * Disconenct from WebSocket
     * @returns 
     */
    disconnect(): void {
        console.debug("[TelemetryService] Disconnecting from a WebSocket.", this.lastConnectionData);
        if (!this.connection) return;
        this.stopReconnection();
        this.connection.close();
    }
    
    private onClose(event: CloseEvent) {
        console.debug(`[TelemetryService] WebSocket closed with code ${event.code}.`, this.lastConnectionData);

        this.connection = null;
        this.clearInactivityTimer();

        this.stateManager.update({
            ...this.getInactiveUpdateObject(),
            status: 'disconnected',
            error: event.reason
        } as TelemetryState)

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

        // Ping/pong
        if (event.data === "ping") {
            console.debug(`[TelemetryService] WebSocket received Ping packet.`);
            this.connection!.send("pong");
            return;
        }

        // TelemetryUpdate
        try {
            console.debug(`[TelemetryService] WebSocket received telemetry update.`);
            const data = JSON.parse(event.data);
            this.stateManager.update(data);            
        } catch (e) {
            console.error('[TelemetryService] Failed to parse telemetry:', e);
        }
    }

    private updateInactivityTimer(): void {
        this.clearInactivityTimer();

        this.inactivityTimer = setTimeout(() => {
            console.debug(`[TelemetryService] Connection was idle for ${INACTIVITY_TIMEOUT / 1000} s, updating channel activity.`);
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

    private getInactiveUpdateObject(): TelemetryState {
        return {
            ...this.getInactiveUpdateObject(),
            data: {
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
            }
        };
    }
}

export default new TelemetryService();