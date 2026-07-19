import { useState } from "react";
import { useSubscription } from "./useSubscription"
import type { components } from "@/api/schema";

export type HostTopDestinationsUpdate = components["schemas"]["HostTopDestinationsUpdate"];
export type HostTopDestinationsParams = components["schemas"]["HostTopDestinationsParams"];

export function useHostTopDestinations(params: HostTopDestinationsParams): HostTopDestinationsUpdate | null {
    const [data, setData] = useState<HostTopDestinationsUpdate | null>(null);

    const updateCallback = (update: unknown) => setData(update as HostTopDestinationsUpdate);
    const inactivityCallback = () => setData(null);

    useSubscription(
        "host_top_destinations",
        params,
        updateCallback,
        inactivityCallback
    );
    
    return data;
}