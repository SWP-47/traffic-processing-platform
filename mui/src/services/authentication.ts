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

    requestTokenRenewal(): void {
        this.logout();
        // To be implemented in the future
        // this.notifyAll();
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

        // implement auto renewal
        this.notifyAll();
    }

    logout() {
        this.state = {
            isAuthenticated: false,
            username: undefined,
            role: undefined
        }

        this.token = undefined;

        this.notifyAll();
    }
}

export default new AuthenticationService();