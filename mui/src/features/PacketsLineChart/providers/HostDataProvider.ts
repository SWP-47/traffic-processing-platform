import { BaseChartDataProvider } from "./BaseChartDataProvider";
import { getHostHistory } from "@/services/history";
import subscriptionManager from "@/services/subscriptionManager";
import type { ChartDataProvider, DataPoint } from "../types";
import { validateHostDetailsUpdate } from "@/hooks/useHostDetails";

export interface HostDataProviderOptions {
    channelId: string;
    hostIp: string;
    windowSec?: number;
    maxPoints?: number;
}

export class HostDataProvider extends BaseChartDataProvider implements ChartDataProvider {
    private readonly channelId: string;
    private readonly hostIp: string;
    private isInitialized: boolean = false;
    private unsubscribeFromTelemetry?: () => void;

    constructor(options: HostDataProviderOptions) {
        super({ maxPoints: options.maxPoints });
        this.channelId = options.channelId;
        this.hostIp = options.hostIp;
    }

    async initialize(timeScale: number): Promise<void> {
        if (this.isInitialized) return;

        this.isInitialized = true;
        const response = await getHostHistory(this.channelId, this.hostIp, timeScale);
        this.setBucketSize(response.interval_sec * 1000);

        if (response.points) {
            const completedPoints: DataPoint[] = response.points.map(p => ({
                timestamp: Date.parse(p.timestamp!),
                packetsInPerSec: p.packets_in_per_sec ?? 0,
                packetsOutPerSec: p.packets_out_per_sec ?? 0,
                isActive: true,
                windowMs: this.getBucketSize(),
                complete: true,
            })).filter(p => !Number.isNaN(p.timestamp));

            this.loadCompletedPoints(completedPoints);
        }

        this.unsubscribeFromTelemetry = subscriptionManager.subscribe(
            "host_details",
            {
                host_ip: this.hostIp,
                period_sec: 5
            },
            (update) => this.handleHostDetailsUpdate(update),
            () => {}
        );
    }

    private handleHostDetailsUpdate(update: Record<string, unknown>): void {
        if (!validateHostDetailsUpdate(update)) return;

        const timestamp = Date.parse(update.timestamp as string);
        if (Number.isNaN(timestamp)) return;

        const point: DataPoint = {
            timestamp,
            packetsInPerSec: update.rx_per_sec,
            packetsOutPerSec: update.tx_per_sec,
            isActive: true,
            windowMs: 5,
            complete: false,
        };

        this.processRawPoint(point);
        this.notifyListeners();
    }

    dispose(): void {
        if (!this.isInitialized) return;

        this.unsubscribeFromTelemetry?.();
        this.unsubscribeFromTelemetry = undefined;
        super.dispose();
    }
}