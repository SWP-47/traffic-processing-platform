import { useSyncExternalStore } from 'react';
import authService from '@/services/authentication';

export function useAuth() {
    return useSyncExternalStore(
        authService.subscribe.bind(authService),
        authService.getSnapshot,
        authService.getSnapshot,
    );
}
