import apiClient from '@/api/client';

import type { components } from '@/api/schema';
export type LoginRequest = components["schemas"]["LoginRequest"]; 
export type Role = components["schemas"]["TokenResponse"]["role"];

export interface UserData {
    isAuthenticated: boolean,
    username: string | undefined,
    role?: Role
};

class AuthenticationService {
    private token: string | undefined;
    private state: UserData = {
        isAuthenticated: false,
        username: undefined,
        role: undefined,
    };

    private isRefreshing: boolean = false;
    private refreshPromise: Promise<boolean> | null = null;

    private listeners = new Set<() => void>();

    subscribe(callback: () => void): () => void {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }

    getSnapshot(): UserData {
        return this.state;
    }

    private notifyAll(): void {
        this.listeners.forEach((callback) => callback());
    }

    isAuthenticated(): boolean {
        return this.token !== undefined;
    }

    getUsername(): string | undefined {
        return this.state.username;
    }

    getRole(): Role | undefined {
        return this.state.role;
    }

    getToken() : string | undefined {
        return this.token;
    }

    async initialize(): Promise<void> {
        if (this.state.isAuthenticated) return;

        const { data, error } = await apiClient.POST('/api/v1/auth/refresh');

        if (error) {
            return;
        }

        this.token = data.access_token;

        this.updateState({
            username: "ehhh",
            role: "admin",
            isAuthenticated: true
        });
    }

    async handleAuthError(): Promise<boolean> {
        if (this.isRefreshing && this.refreshPromise) {
            return this.refreshPromise;
        }

        this.isRefreshing = true;
        this.refreshPromise = this.attemptTokenRefresh();

        try {
            const success = await this.refreshPromise;
            return success;
        } finally {
            this.isRefreshing = false;
            this.refreshPromise = null;
        }
    }

    async login(credentials: LoginRequest) {
        const { data, error } = await apiClient.POST('/api/v1/auth/login', { body: credentials });
        if (error) throw error;

        this.token = data.access_token;

        this.state = {
           username: credentials.username,
           role: data.role,
           isAuthenticated: true
        };

        this.notifyAll();
    }

    private async attemptTokenRefresh(): Promise<boolean> {
        try {
            const { data, error } = await apiClient.POST('/api/v1/auth/refresh');
            
            if (error) {
                this.clearData();
                return false;
            }
            
            this.token = data.access_token;
            this.updateState({
                ...this.state,
                isAuthenticated: true,
            });

            return true;
        } catch (e: unknown) {
            this.clearData();
            console.error(e);
            return false;
        }
    }

    async logout() {
        await apiClient.POST('/api/v1/auth/logout').catch(() => {});
        this.clearData();
    }

    private clearData() {
        this.updateState({
            isAuthenticated: false,
            username: undefined,
            role: undefined
        });
        this.token = undefined;
    }

    private updateState(newState: UserData) {
        this.state = newState;
        this.notifyAll();
    }
}

export default new AuthenticationService();