import { BaseChartDataProvider } from "./BaseChartDataProvider";
import { getHistory } from "@/services/history";
import subscriptionManager from "@/services/subscriptionManager";
import { validateTelemetryUpdate } from "@/hooks/useTelemetry";
import type { ChartDataProvider, DataPoint } from "../types";

export interface ChannelDataProviderOptions {
    channelId: string;
    windowSec?: number;
    maxPoints?: number;
}

export class ChannelDataProvider extends BaseChartDataProvider implements ChartDataProvider {
    private readonly channelId: string;
    private readonly windowSec: number;
    private unsubscribeFromTelemetry?: () => void;

    constructor(options: ChannelDataProviderOptions) {
        super({ maxPoints: options.maxPoints });
        this.channelId = options.channelId;
        this.windowSec = options.windowSec ?? 5.0;
    }

    async initialize(timeScale: number): Promise<void> {
        const response = await getHistory(this.channelId, timeScale);
        this.setBucketSize(response.interval_sec * 1000);

        if (response.points) {
            const completedPoints: DataPoint[] = response.points.map(p => ({
                timestamp: Date.parse(p.timestamp!),
                packetsInPerSec: p.packets_in_per_sec ?? 0,
                packetsOutPerSec: p.packets_out_per_sec ?? 0,
                isActive: p.is_active ?? false,
                windowMs: this.getBucketSize(),
                complete: true,
            })).filter(p => !Number.isNaN(p.timestamp));

            this.loadCompletedPoints(completedPoints);
        }

        this.unsubscribeFromTelemetry = subscriptionManager.subscribe(
            "telemetry",
            { window_sec: this.windowSec },
            (update) => this.handleTelemetryUpdate(update),
            () => {}
        );
    }

    private handleTelemetryUpdate(update: Record<string, unknown>): void {
        if (!validateTelemetryUpdate(update)) return;

        const timestamp = Date.parse(update.timestamp as string);
        if (Number.isNaN(timestamp)) return;

        const point: DataPoint = {
            timestamp,
            packetsInPerSec: update.metrics.direction_in.packets_per_sec,
            packetsOutPerSec: update.metrics.direction_out.packets_per_sec,
            isActive: update.is_active === true,
            windowMs: update.window_ms,
            complete: false,
        };

        this.processRawPoint(point);
        this.notifyListeners();
    }

    dispose(): void {
        this.unsubscribeFromTelemetry?.();
        this.unsubscribeFromTelemetry = undefined;
        super.dispose();
    }
}