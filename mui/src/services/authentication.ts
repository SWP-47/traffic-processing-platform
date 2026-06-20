import apiClient from '@/api/client';

import type { components } from '@/api/schema';
export type LoginRequest = components["schemas"]["LoginRequest"]; 
export type Role = components["schemas"]["LoginResponse"]["role"];

export interface UserData {
    isAuthenticated: boolean,
    username: string | undefined,
    role: Role
};

class AuthenticationService {
    private username: string | undefined;
    private role: Role;
    private token: string | undefined;

    private listeners = new Set<() => void>();

    subscribe(callback: () => void): () => void {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }

    getSnapshot(): UserData {
        return {
            isAuthenticated: this.isAuthenticated(),
            username: this.username,
            role: this.role,
        };
    }

    private notifyAll(): void {
        this.listeners.forEach((callback) => callback());
    }

    isAuthenticated(): boolean {
        return this.token !== undefined;
    }

    getUsername(): string | undefined {
        return this.username;
    }

    getRole(): Role {
        return this.role;
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

        this.username = credentials.username;
        this.token = data.access_token;
        this.role = data.role;

        // implement auto renewal
        this.notifyAll();
    }

    logout() {
        this.username = undefined;
        this.role = undefined;
        this.token = undefined;

        this.notifyAll();
    }
}

export default new AuthenticationService();