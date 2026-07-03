import { useSyncExternalStore } from 'react';
import topHosts, { type HostsTarget } from '@/services/topHosts';

export function useTopHosts(target: HostsTarget) {
    return useSyncExternalStore(
        (callback) => topHosts.subscribe(callback, target),
        () => topHosts.getLastUpdate(),
        () => topHosts.getLastUpdate(),
    );
}
