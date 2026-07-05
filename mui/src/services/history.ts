import apiClient from '@/api/client';
import type { paths, components } from '@/api/schema';

export type HistoryPeriod = paths["/api/v1/channel/{channel_id}/history"]["get"]["parameters"]["query"]["period"];
export type HistoryResponse = components["schemas"]["ChannelHistoryResponse"];

export async function getHistory(channelId: string, period: HistoryPeriod): Promise<HistoryResponse> {
    const { data, error } = await apiClient.GET('/api/v1/channel/{channel_id}/history', {
        params: {
            path: { channel_id: channelId },
            query: { period: period }
        }
    });
    
    if (error) throw error;
    
    return data!;
}