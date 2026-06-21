import apiClient from '@/api/client';
import type { components } from '@/api/schema';

export type HealthResponse = components["schemas"]["HealthResponse"];

export async function getHealth(): Promise<HealthResponse> {
    const { data, error } = await apiClient.GET('/api/v1/health');
    
    if (error) throw error;
    
    return data;
}