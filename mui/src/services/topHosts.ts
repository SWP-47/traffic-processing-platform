import type { components } from "@/api/schema";
import websocket from "@/services/websocket";

export type HostsUpdate = components["schemas"]["HostsUpdate"];
export type HostEntry = components["schemas"]["HostEntry"];

export type HostsTarget = "lan_hosts" | "wan_hosts";
export type HostsSorting = "sent" | "received" | "last_seen";

class TopHostsService {
    private lastUpdate: HostEntry[] | null = null;
    private listeners = {
        lan_hosts: new Set<() => void>(),
        wan_hosts: new Set<() => void>()
    };

    private setting : {
        lan_hosts: {
            target: HostsTarget,
            sort_by: HostsSorting,
            limit: number
        } | null,
        wan_hosts: {
            target: HostsTarget,
            sort_by: HostsSorting,
            limit: number
        } | null
    } = {
        lan_hosts: null,
        wan_hosts: null
    };

    constructor() {
        websocket.subscribeUpdate("hosts_update", (update) => this.handleUpdate(update));
    }

    requestSubscription(target: HostsTarget, sort_by: HostsSorting, limit: number) {
        this.setting[target] = { target, sort_by, limit };
        const subscriptionPayload = { action: "subscribe", ...this.setting[target] }

        websocket.send(JSON.stringify(subscriptionPayload));
        console.debug(`[TopHostsService] Requested a subscripton to ${target} updates (sort by ${sort_by}, limit ${limit}).`);
    }

    requestUnsubscription(target: HostsTarget) {
        this.setting[target] = null;
        const subscriptionPayload = { action: "unsubscribe", target }

        websocket.send(JSON.stringify(subscriptionPayload));
        console.debug(`[TopHostsService] Requested an unsubscripton from ${target}.`);
    }

    subscribe(callback: () => void, target: HostsTarget): () => void {
        this.listeners[target].add(callback);
        return () => this.listeners[target].delete(callback);
    }

    getLastUpdate(): HostEntry[] | null {
        return this.lastUpdate;
    }
    
    private handleUpdate(data: unknown): void {
        if (!this.validateUpdate(data)) {
            console.warn('[TopHostsService] Invalid hosts update:', data);
            return;
        }

        this.lastUpdate = data.hosts!;
        this.notifyAll(data.target!);
    }
    
    private notifyAll(target: HostsTarget): void {
        this.listeners[target].forEach((callback) => callback());
    }

    private validateUpdate(data: unknown): data is HostsUpdate {
        if (!data || typeof data !== 'object') return false;

        const d = data as Record<string, unknown>;

        if (d.type !== 'hosts_update') return false;
        if (typeof d.target !== 'string') return false;
        if (typeof d.channel_id !== 'string') return false;
        if (typeof d.timestamp !== 'string') return false;

        if (!Array.isArray(d.hosts)) return false;

        for (const host of d.hosts) {
            if (!host || typeof host !== 'object') return false;

            const h = host as Record<string, unknown>;

            if (typeof h.ip !== 'string') return false;
            if (typeof h.sent_per_sec !== 'number') return false;
            if (typeof h.received_per_sec !== 'number') return false;
            if (typeof h.last_seen !== 'string') return false;
        }

        return true;
    }
}

export default new TopHostsService();