import { useState } from "react";
import { useSubscription } from "./useSubscription"
import type { components } from "@/api/schema";

export type HostDetailsUpdate = components["schemas"]["HostDetailsUpdate"];
export type HostDetailsParams = components["schemas"]["HostDetailsParams"];

export function useHostDetailsUpdate(params: HostDetailsParams): HostDetailsUpdate | null {
    const [data, setData] = useState<HostDetailsUpdate | null>(null);

    const updateCallback = (update: unknown) => validateHostDetailsUpdate(update) && setData(update);
    const inactivityCallback = () => setData(null);

    useSubscription(
        "host_details",
        params,
        updateCallback,
        inactivityCallback
    );
    
    return data;
}

export function validateHostDetailsUpdate(data: unknown): data is HostDetailsUpdate {
    if (!data || typeof data !== 'object') return false;

    const d = data as Record<string, unknown>;

    if (d.type !== 'host_details_update') return false;
    if (typeof d.id !== 'string') return false;
    if (typeof d.channel_id !== 'string') return false;
    if (typeof d.host_ip !== 'string') return false;
    if (typeof d.timestamp !== 'string') return false;
    if (typeof d.tx_per_sec !== 'number') return false;
    if (typeof d.rx_per_sec !== 'number') return false;

    return true;
}