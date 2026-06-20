import type { components } from "@/api/schema";
export type TelemetryUpdate = components["schemas"]["TelemetryUpdate"];

export interface TelemetryConnectionData {
    channel_id: string
};