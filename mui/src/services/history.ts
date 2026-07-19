import apiClient from '@/api/client';
import type { paths, components } from '@/api/schema';

export type HistoryRequest = paths["/api/v1/channel/{channel_id}/history"]["get"]["parameters"]["query"];
export type HistoryResponse = components["schemas"]["ChannelHistoryResponse"];

export async function getHistory(channelId: string, period: HistoryRequest["period_sec"], startTime?: HistoryRequest["start_time"]): Promise<HistoryResponse> {
    const { data, error } = await apiClient.GET('/api/v1/channel/{channel_id}/history', {
        params: {
            path: { channel_id: channelId },
            query: { period_sec: period, start_time: startTime }
        }
    });
    
    if (error) throw error;
    
    return data;
}

export type HostHistoryRequest = paths["/api/v1/channel/{channel_id}/hosts/{host_ip}/history"]["get"]["parameters"]["query"];
export type HostHistoryResponse = components["schemas"]["HostHistoryResponse"];

export async function getHostHistory(channelId: string, hostIp: string, period: HistoryRequest["period_sec"], startTime?: HistoryRequest["start_time"]): Promise<HostHistoryResponse> {
    const { data, error } = await apiClient.GET('/api/v1/channel/{channel_id}/hosts/{host_ip}/history', {
        params: {
            path: { channel_id: channelId, host_ip: hostIp },
            query: { period_sec: period, start_time: startTime }
        }
    });
    
    if (error) throw error;
    
    return data;
}

export type BucketIntervalRequest = paths["/api/v1/utils/bucket-interval"]["get"]["parameters"]["query"];
export type BucketIntervalResponse = components["schemas"]["BucketIntervalResponse"];

export async function getBucketInterval(period: BucketIntervalRequest["period_sec"]): Promise<BucketIntervalResponse> {
    const { data, error } = await apiClient.GET('/api/v1/utils/bucket-interval', {
        params: {
            query: { period_sec: period }
        }
    });
    
    if (error) throw error;
    
    return data;
}