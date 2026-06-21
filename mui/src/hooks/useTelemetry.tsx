import { useSyncExternalStore } from 'react';
import telemetryService from '@/services/telemetry';
import type { TelemetryState } from '@/services/telemetry';

export function useTelemetrySelector<T>(
    selector: (data: TelemetryState | null) => T
): T {
    return useSyncExternalStore(
        telemetryService.subscribe.bind(telemetryService),
        () => selector(telemetryService.getLastUpdate()),
        () => selector(telemetryService.getLastUpdate())
    );
}
