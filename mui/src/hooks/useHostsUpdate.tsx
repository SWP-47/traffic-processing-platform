import { useSubscription } from "./useSubscription"
import type { components } from "@/api/schema";

export type HostsUpdate = components["schemas"]["HostsTableUpdate"];
export type HostsTableParams = components["schemas"]["HostsTableParams"];

export function useHostsUpdate(params: HostsTableParams): HostsUpdate | null {
    const data = useSubscription<HostsUpdate>({
        target: "hosts_table",
        params: params
    }, validateUpdate);
    
    return data;
}

function validateUpdate(data: unknown): data is HostsUpdate {
    if (!data || typeof data !== 'object') return false;

    const d = data as Record<string, unknown>;

    if (d.type !== 'hosts_table_update') return false;
    if (typeof d.id !== 'string') return false;
    if (typeof d.channel_id !== 'string') return false;
    if (d.target !== 'hosts_table') return false;
    if (typeof d.timestamp !== 'string') return false;
    if (typeof d.total_count !== 'number') return false;

    if (!Array.isArray(d.hosts)) return false;

    for (const host of d.hosts) {
        if (!host || typeof host !== 'object') return false;

        const h = host as Record<string, unknown>;

        // Check individual host properties
        if (h.location !== 'LAN' && h.location !== 'WAN') return false;
        if (typeof h.ip !== 'string') return false;
        if (typeof h.unique_destinations !== 'number') return false;
        if (typeof h.tx_per_sec !== 'number') return false;
        if (typeof h.rx_per_sec !== 'number') return false;
        if (typeof h.last_activity !== 'string') return false;
    }

    return true;
}