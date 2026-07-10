import subscriptionManager from "@/services/subscriptionManager";
import type { SubscriptionParams, SubscriptionTarget, Update } from "@/services/subscriptionManager";
import { useEffect, useRef } from "react";

export function useSubscription(
    target: SubscriptionTarget,
    params: SubscriptionParams,
    updateCallback: (update: Update) => void,
    inactivityCallback: () => void
): void {
    const key = subscriptionManager.getKey(target, params);

    const updateCallbackRef = useRef(updateCallback);
    const inactivityCallbackRef = useRef(inactivityCallback);

    useEffect(() => {
        updateCallbackRef.current = updateCallback;
        inactivityCallbackRef.current = inactivityCallback;
    }, [updateCallback, inactivityCallback]);

    useEffect(() => {
        const unsubscribe = subscriptionManager.subscribe(
            target,
            params,
            (update) => updateCallbackRef.current(update),
            () => inactivityCallbackRef.current()
        );
        return () => unsubscribe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [key]); // Key - is an object hash, it will change if object fields changed.
}