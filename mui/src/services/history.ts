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