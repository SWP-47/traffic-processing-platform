/**
 * This file provides TelemetryService singleton object that works with telemetry WebSocket.
 * Only one concurrent connection can be opened.
 * After INACTIVITY_TIMEOUT ms service updates telemetry info so that channel is inactive and metrics are zero. 
 */

import type { components } from "@/api/schema";
import websocket from "@/services/websocket";

export type TelemetryUpdate = components["schemas"]["TelemetryUpdate"];

const INACTIVITY_TIMEOUT = 6000; // in ms.

class TelemetryService {
    private inactivityTimer: number | undefined;

    private lastUpdate: TelemetryUpdate | null = null;
    private listeners = new Set<() => void>();

    constructor() {
        websocket.subscribeUpdate("telemetry_update", (update) => this.handleUpdate(update));
        websocket.subscribeState(() => {
            if (websocket.getState().connectionStatus == 'disconnected') {
                this.clearInactivityTimer();
            }
        })
    }
    
    /**
     * Add new subscriber to telemery updates
     * @param callback 
     * @returns function to unsubscribe
     */
    subscribe(callback: () => void): () => void {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }
    
    /**
     * @returns Last telemetry update
     */
    getLastUpdate(): TelemetryUpdate | null {
        return this.lastUpdate;
    }
    
    private handleUpdate(data: unknown): void {
        if (!this.validateUpdate(data)) {
            console.warn('[TelemetryService] Invalid telemetry update:', data);
            return;
        }

        this.lastUpdate = data;
        this.notifyAll();
        this.updateInactivityTimer();
    }
    
    private notifyAll(): void {
        this.listeners.forEach((callback) => callback());
    }

    private updateInactivityTimer(): void {
        this.clearInactivityTimer();

        this.inactivityTimer = setTimeout(() => {
            console.debug(`[TelemetryService] Connection was idle for ${INACTIVITY_TIMEOUT / 1000}s, updating channel activity.`);
            this.handleUpdate(this.getInactiveUpdateObject());
        }, INACTIVITY_TIMEOUT);
    }

    private clearInactivityTimer(): void {
        if (!this.inactivityTimer) return;

        clearTimeout(this.inactivityTimer);
        this.inactivityTimer = undefined;
    }

    private getInactiveUpdateObject(): TelemetryUpdate {
        return {
            ...this.lastUpdate,
            is_active: false,
            metrics: {
                direction_in: { packets: 0, packets_per_sec: 0 },
                direction_out: { packets: 0, packets_per_sec: 0 },
            },
            timestamp: new Date().toISOString(),
            received_at: new Date().toISOString(),
        };
    }

    private validateUpdate(data: unknown): data is TelemetryUpdate {
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

export default new TelemetryService();