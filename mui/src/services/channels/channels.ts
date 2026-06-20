import apiClient from '@/api/client';
import type { ChannelsResponse, ChannelStatusResponse } from './types';

export async function getChannels(): Promise<ChannelsResponse> {
    const { data, error } = await apiClient.GET('/api/v1/channels');
    
    if (error) throw error;
    
    return data;
}

export async function getChannelStatus(channelId: string): Promise<ChannelStatusResponse> {
    const { data, error } = await apiClient.GET(
        '/api/v1/channel/{channel_id}/status',
        { params: { path: { channel_id: channelId } } }
    );
    
    if (error) throw error;
    
    return data;
}