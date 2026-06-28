import { useSyncExternalStore } from 'react';
import telemetryService, { type TelemetryUpdate } from '@/services/telemetry';

export function useTelemetrySelector<T>(
    selector: (data: TelemetryUpdate | null) => T
): T {
    return useSyncExternalStore(
        telemetryService.subscribe.bind(telemetryService),
        () => selector(telemetryService.getLastUpdate()),
        () => selector(telemetryService.getLastUpdate())
    );
}
