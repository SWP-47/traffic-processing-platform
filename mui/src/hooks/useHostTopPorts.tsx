import { useState } from "react";
import { useSubscription } from "./useSubscription"
import type { components } from "@/api/schema";

export type HostsTopPortsUpdate = components["schemas"]["HostTopPortsUpdate"];
export type HostsTopPortsParams = components["schemas"]["HostTopPortsParams"];

export function useHostTopPorts(params: HostsTopPortsParams): HostsTopPortsUpdate | null {
    const [data, setData] = useState<HostsTopPortsUpdate | null>(null);

    const updateCallback = (update: unknown) => validateHostsTopPortsUpdate(update) && setData(update);
    const inactivityCallback = () => setData(null);

    useSubscription(
        "host_top_ports",
        params,
        updateCallback,
        inactivityCallback
    );
    
    return data;
}

function validateHostsTopPortsUpdate(data: unknown): data is HostsTopPortsUpdate {
    if (!data || typeof data !== 'object') return false;

    const d = data as Record<string, unknown>;

    if (d.type !== 'host_top_ports_update') return false;
    if (typeof d.id !== 'string') return false;
    if (typeof d.channel_id !== 'string') return false;
    if (typeof d.host_ip !== 'string') return false;
    if (typeof d.timestamp !== 'string') return false;
    if (typeof d.total_count !== 'number') return false;

    if (!Array.isArray(d.ports)) return false;

    for (const port of d.ports) {
        if (!port || typeof port !== 'object') return false;

        const p = port as Record<string, unknown>;

        if (typeof p.port !== 'number') return false;
        if (typeof p.protocol !== 'string') return false;
        if (typeof p.packets_per_sec !== 'number') return false;
        if (typeof p.bytes_per_sec !== 'number') return false;
    }

    return true;
}