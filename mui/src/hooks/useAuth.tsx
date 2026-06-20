import { useSyncExternalStore } from 'react';
import authService from '@/services/authentication';

export function useAuth() {
    return useSyncExternalStore(
        (callback) => authService.subscribe(callback),
        () => authService.getSnapshot(),
        () => authService.getSnapshot(),
    );
}
