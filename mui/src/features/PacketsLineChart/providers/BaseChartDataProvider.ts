
import type { DataPoint } from "../types";

export abstract class BaseChartDataProvider {
    protected data: Map<number, DataPoint> = new Map();
    protected listeners = new Set<() => void>();
    
    protected bucketSizeMs: number = 0;
    protected minTs: number = Number.MAX_SAFE_INTEGER;
    protected maxTs: number = Number.MIN_SAFE_INTEGER;
    protected lastIncompleteTs?: number;

    protected currentBucketPoints: DataPoint[] = [];
    protected bucketStartTime: number | null = null;

    protected readonly maxPoints: number | undefined;

    constructor(options: { maxPoints?: number }) {
        this.maxPoints = options.maxPoints;
    }

    // === Public API ===

    getData(): DataPoint[] {
        return [...this.data.values()].sort((a, b) => a.timestamp - b.timestamp);
    }

    getBucketSize(): number {
        return this.bucketSizeMs;
    }

    subscribe(callback: () => void): () => void {
        this.listeners.add(callback);
        return () => { this.listeners.delete(callback); };
    }

    dispose(): void {
        this.listeners.clear();
        this.data.clear();
        this.currentBucketPoints = [];
    }

    // === Protected API ===

    /**
     * Set the bucket size. Called by the inheritor after loading the history.
     */
    protected setBucketSize(ms: number): void {
        this.bucketSizeMs = ms;
    }

    /**
     * Notify subscribers about the data change.
     */
    protected notifyListeners(): void {
        for (const cb of this.listeners) {
            try { cb(); } catch (err) { console.error("Listener error:", err); }
        }
    }

    /**
     * The inheritor calls this method when it receives a new raw point from its source.
     */
    protected processRawPoint(point: DataPoint): void {
        // First backet initialization
        if (this.bucketStartTime === null) {
            this.bucketStartTime = point.timestamp;
        }

        // Remove the previous incomplete point
        if (this.lastIncompleteTs !== undefined) {
            this.data.delete(this.lastIncompleteTs);
        }

        // If bucket is full - close it
        if (point.timestamp >= this.bucketStartTime + this.bucketSizeMs 
            && this.currentBucketPoints.length > 0) {
            
            const completedPoint = this.calculateAverage(this.currentBucketPoints);
            completedPoint.complete = true;
            this.insertPoint(completedPoint);

            // Reset bucket
            this.currentBucketPoints = [];
            this.bucketStartTime = point.timestamp;
            this.lastIncompleteTs = undefined;
        }

        // Add a point to the bucket
        this.currentBucketPoints.push(point);

        // Compute and insert incomplete average
        const averagePoint = this.calculateAverage(this.currentBucketPoints);
        averagePoint.complete = false;
        this.lastIncompleteTs = averagePoint.timestamp;
        this.insertPoint(averagePoint);
    }

    /**
     * Load an array of completed points (for example, from the history).
     */
    protected loadCompletedPoints(points: DataPoint[]): void {
        for (const point of points) {
            this.insertPoint({ ...point, complete: true });
        }
        if (this.data.size > 0) {
            this.bucketStartTime = this.maxTs;
        }
    }

    // === Private helpers ===

    private calculateAverage(points: DataPoint[]): DataPoint {
        const sum = points.reduce((acc, p) => ({
            packetsInPerSec: acc.packetsInPerSec + p.packetsInPerSec,
            packetsOutPerSec: acc.packetsOutPerSec + p.packetsOutPerSec,
        }), { packetsInPerSec: 0, packetsOutPerSec: 0 });

        const last = points[points.length - 1]!;
        return {
            timestamp: last.timestamp,
            packetsInPerSec: sum.packetsInPerSec / points.length,
            packetsOutPerSec: sum.packetsOutPerSec / points.length,
            isActive: points.some(p => p.isActive),
            windowMs: this.bucketSizeMs,
            complete: false,
        };
    }

    private insertPoint(point: DataPoint): void {
        this.data.set(point.timestamp, point);

        if (point.timestamp < this.minTs) this.minTs = point.timestamp;
        if (point.timestamp > this.maxTs) this.maxTs = point.timestamp;

        // Eviction по лимиту
        if (this.maxPoints !== undefined && this.data.size > this.maxPoints) {
            const oldestKey = this.data.keys().next().value;
            if (oldestKey !== undefined) {
                this.data.delete(oldestKey);
                this.minTs = this.data.size > 0
                    ? this.data.keys().next().value ?? Number.MAX_SAFE_INTEGER
                    : Number.MAX_SAFE_INTEGER;
            }
        }
    }
}