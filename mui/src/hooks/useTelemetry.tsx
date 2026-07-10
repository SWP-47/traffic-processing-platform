

import type { components } from "@/api/schema";
import { useState } from "react";
import { useSubscription } from "./useSubscription";

export type TelemetryUpdate = components["schemas"]["TelemetryUpdate"];
export type TelemetryParams = components["schemas"]["TelemetryParams"];

export function useTelemetry(
    params: TelemetryParams = { window_sec: 5.0 }
): TelemetryUpdate | null {
    const [data, setData] = useState<TelemetryUpdate | null>(null);
    
    const updateCallback = (update: unknown) => validateTelemetryUpdate(update) && setData(update);
    const inactivityCallback = () => setData(null);

    useSubscription(
        "telemetry",
        params,
        updateCallback,
        inactivityCallback
    );
    
    return data;
}

export function validateTelemetryUpdate(data: unknown): data is TelemetryUpdate {
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