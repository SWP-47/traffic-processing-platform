import { useSyncExternalStore } from 'react';
import telemetryService from '@/services/telemetry';
import type { TelemetryUpdate } from '@/services/telemetry/types';

export function useTelemetrySelector<T>(
    selector: (data: TelemetryUpdate | null) => T
): T {
    return useSyncExternalStore(
        telemetryService.subscribe.bind(telemetryService),
        () => selector(telemetryService.getLastUpdate()),
        () => selector(telemetryService.getLastUpdate())
    );
}
