export interface DataPoint {
    timestamp: number;
    packetsInPerSec: number;
    packetsOutPerSec: number;
    isActive: boolean;
    windowMs: number;
    complete: boolean
};

export interface ChartDataProvider {
    initialize(timeScale: number): Promise<void>;
    getBucketSize(): number;
    getData(): DataPoint[];
    subscribe(callback: () => void): () => void;
    dispose(): void;
}