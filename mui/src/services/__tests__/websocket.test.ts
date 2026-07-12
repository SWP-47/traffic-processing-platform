import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import defaultService, {
    ConnectionStatus, 
    ActivityStatus 
} from '../websocket';

// Infer the type of the singleton service to avoid using 'any'
type WebSocketServiceType = typeof defaultService;

// Mock the authentication module.
// Now auth.getToken() will return 'mock-token' instead of calling the real implementation,
// and auth.requestTokenRenewal() will just record that it was called.
vi.mock('@/services/authentication', () => ({
    default: {
        getToken: vi.fn(() => 'mock-token'),
        requestTokenRenewal: vi.fn(),
    },
}));

// Import the mocked auth module to verify if it was called
import auth from '@/services/authentication';

describe('WebSocketConnectionService', () => {
    let service: WebSocketServiceType;
    let wsInstance: MockWebSocket | null = null;

    // Create a mock class for WebSocket.
    // We have full control over its behavior from the tests.
    class MockWebSocket {
        static CONNECTING = 0;
        static OPEN = 1;
        static CLOSING = 2;
        static CLOSED = 3;

        readyState = MockWebSocket.CONNECTING;
        url: string;
        onopen: (() => void) | null = null;
        onclose: ((event: Partial<CloseEvent>) => void) | null = null;
        onmessage: ((event: Partial<MessageEvent>) => void) | null = null;
        onerror: ((error: Event) => void) | null = null;
        
        send = vi.fn();
        close = vi.fn();

        constructor(url: string) {
            this.url = url;
            // Save a reference to the last created socket 
            // so tests can simulate its events
            // eslint-disable-next-line @typescript-eslint/no-this-alias
            wsInstance = this; 
        }
        
        // Helpers to simulate WebSocket events
        simulateOpen() {
            this.readyState = MockWebSocket.OPEN;
            this.onopen?.();
        }
        simulateClose(code = 1000, reason = '', wasClean = true) {
            this.readyState = MockWebSocket.CLOSED;
            this.onclose?.({ code, reason, wasClean } as CloseEvent);
        }
        simulateMessage(data: string) {
            this.onmessage?.({ data } as MessageEvent);
        }
    }

    beforeEach(async () => {
        // Reset module registry so each test gets a FRESH instance of the singleton
        vi.resetModules();
        
        // Replace the global browser WebSocket with our MockWebSocket
        vi.stubGlobal('WebSocket', MockWebSocket);
        
        // "Freeze" time. setTimeout and setInterval won't tick on their own.
        vi.useFakeTimers();

        // Make Math.random() deterministic (always 0) 
        // so the reconnection delay is predictable (no jitter)
        vi.spyOn(Math, 'random').mockReturnValue(0);

        // Silence console to keep test output clean
        vi.spyOn(console, 'debug').mockImplementation(() => {});
        vi.spyOn(console, 'error').mockImplementation(() => {});

        // Dynamically import the service AFTER resetting modules and stubbing WebSocket
        const module = await import('../websocket');
        service = module.default;
        
        vi.clearAllMocks();
        wsInstance = null;
    });

    afterEach(() => {
        // Restore time and global objects to their normal state after each test
        vi.useRealTimers();
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    // --- TESTS START HERE ---

    it('should have Disconnected status initially', () => {
        expect(service.getState().connectionStatus).toBe(ConnectionStatus.Disconnected);
    });

    describe('connect', () => {
        it('should create WebSocket and update state to Connecting', () => {
            service.connect({ channel_id: '123' });
            
            expect(wsInstance).not.toBeNull();
            expect(wsInstance!.url).toContain('channel_id=123');
            expect(wsInstance!.url).toContain('token=mock-token');
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Connecting);
        });

        it('should update state to Connected and Active on open', () => {
            service.connect({ channel_id: '123' });
            wsInstance!.simulateOpen();
            
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Connected);
            expect(service.getState().activityStatus).toBe(ActivityStatus.Active);
        });

        it('should schedule new connection if already connected', () => {
            service.connect({ channel_id: '1' });
            wsInstance!.simulateOpen();
            const firstWs = wsInstance;

            // Try to connect again without closing the first connection
            service.connect({ channel_id: '2' });
            
            // The service should call close on the first connection
            expect(firstWs!.close).toHaveBeenCalled();
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Disconnecting);

            // Simulate the first connection closing
            firstWs!.simulateClose();
            
            // A new connection should be created with the new channel_id
            expect(wsInstance).not.toBe(firstWs);
            expect(wsInstance!.url).toContain('channel_id=2');
        });
    });

    describe('disconnect', () => {
        it('should close WebSocket and update state', () => {
            service.connect({ channel_id: '123' });
            wsInstance!.simulateOpen();
            
            service.disconnect();
            
            expect(wsInstance!.close).toHaveBeenCalled();
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Disconnecting);

            wsInstance!.simulateClose();
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Disconnected);
        });
    });

    describe('inactivity timeout', () => {
        it('should become Inactive after 6 seconds of idle', () => {
            service.connect({ channel_id: '123' });
            wsInstance!.simulateOpen();
            expect(service.getState().activityStatus).toBe(ActivityStatus.Active);

            // "Fast-forward" time by 6 seconds
            vi.advanceTimersByTime(6000);
            expect(service.getState().activityStatus).toBe(ActivityStatus.Inactive);
        });

        it('should reset inactivity timer on message', () => {
            service.connect({ channel_id: '123' });
            wsInstance!.simulateOpen();
            
            vi.advanceTimersByTime(3000); // 3 seconds passed
            wsInstance!.simulateMessage('some data'); // Message received, timer reset
            
            vi.advanceTimersByTime(3000); // Another 3 seconds passed (6 total since last message)
            expect(service.getState().activityStatus).toBe(ActivityStatus.Active); // Not Inactive yet
            
            vi.advanceTimersByTime(3000); // Another 3 seconds passed (6 total since message)
            expect(service.getState().activityStatus).toBe(ActivityStatus.Inactive); // Now Inactive
        });
    });

    describe('ping/pong', () => {
        it('should respond with pong to ping', () => {
            service.connect({ channel_id: '123' });
            wsInstance!.simulateOpen();
            
            wsInstance!.simulateMessage('ping');
            expect(wsInstance!.send).toHaveBeenCalledWith('pong');
        });
    });

    describe('reconnection', () => {
        it('should reconnect on abnormal closure', () => {
            service.connect({ channel_id: '123' });
            wsInstance!.simulateOpen();
            const firstWs = wsInstance;
            
            // 1006 - Abnormal Closure (falls into ReconnectionCodes)
            wsInstance!.simulateClose(1006, 'Abnormal', false);
            
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Reconnecting);
            
            // Wait for the reconnection timer. 
            // With reconnectionAttempt=1 and Math.random()=0, delay is 500 * 2^1 = 1000ms
            vi.advanceTimersByTime(1000);
            
            // A new socket should be created
            expect(wsInstance).not.toBe(firstWs);
            expect(wsInstance!.url).toContain('channel_id=123');
        });

        // RECONNECTING persists until connection is established
        it('should keep RECONNECTING status while creating new connection during automatic reconnection', () => {
            service.connect({ channel_id: '123' });
            wsInstance!.simulateOpen();
            
            // Trigger reconnection
            wsInstance!.simulateClose(1006, 'Abnormal', false);
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Reconnecting);
            
            // Wait for reconnection timer
            vi.advanceTimersByTime(1000);
            
            // Status should STILL be RECONNECTING (not CONNECTING)
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Reconnecting);
            
            // Only after successful connection should it become CONNECTED
            wsInstance!.simulateOpen();
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Connected);
        });

        // Manual connect() call should reset RECONNECTING to CONNECTING
        it('should change RECONNECTING to CONNECTING when connect() is called manually', () => {
            service.connect({ channel_id: '123' });
            wsInstance!.simulateOpen();
            
            // Trigger reconnection
            wsInstance!.simulateClose(1006, 'Abnormal', false);
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Reconnecting);
            
            // User manually calls connect() with new channel_id
            service.connect({ channel_id: '456' });
            
            // Status should become CONNECTING (not RECONNECTING)
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Connecting);
            expect(wsInstance!.url).toContain('channel_id=456');
        });

        // Manual disconnect() call should reset RECONNECTING to DISCONNECTING
        it('should change RECONNECTING to DISCONNECTING when disconnect() is called', () => {
            service.connect({ channel_id: '123' });
            wsInstance!.simulateOpen();
            
            // Trigger reconnection
            wsInstance!.simulateClose(1006, 'Abnormal', false);
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Reconnecting);
            
            // User manually calls disconnect()
            service.disconnect();
            
            // Status should become DISCONNECTING
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Disconnecting);
        });

        // Non-reconnection error code should reset RECONNECTING to DISCONNECTED
        it('should change RECONNECTING to DISCONNECTED when error code is not in ReconnectionCodes', () => {
            service.connect({ channel_id: '123' });
            wsInstance!.simulateOpen();
            
            // Trigger reconnection
            wsInstance!.simulateClose(1006, 'Abnormal', false);
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Reconnecting);
            
            // Wait for reconnection timer and create new connection
            vi.advanceTimersByTime(1000);
            
            // Close with normal code (1000) - should NOT trigger reconnection
            wsInstance!.simulateClose(1000, 'Normal closure', true);
            
            // Status should become DISCONNECTED
            expect(service.getState().connectionStatus).toBe(ConnectionStatus.Disconnected);
        });

        it('should request token renewal on auth error (4001)', () => {
            service.connect({ channel_id: '123' });
            wsInstance!.simulateOpen();
            
            wsInstance!.simulateClose(4001, 'Auth error', true);
            
            expect(auth.requestTokenRenewal).toHaveBeenCalled();
        });
    });

    describe('listeners', () => {
        it('should notify state listeners', () => {
            const callback = vi.fn();
            service.subscribeState(callback);
            
            service.connect({ channel_id: '123' }); // This triggers updateState
            expect(callback).toHaveBeenCalled();
        });

        it('should notify message listeners', () => {
            const callback = vi.fn();
            service.subscribeMessages(callback);
            
            service.connect({ channel_id: '123' });
            wsInstance!.simulateOpen();
            
            wsInstance!.simulateMessage('hello');
            expect(callback).toHaveBeenCalledWith('hello');
        });

        it('should unsubscribe correctly', () => {
            const callback = vi.fn();
            const unsubscribe = service.subscribeMessages(callback);
            
            service.connect({ channel_id: '123' });
            wsInstance!.simulateOpen();
            
            unsubscribe(); // Unsubscribe
            
            wsInstance!.simulateMessage('hello');
            expect(callback).not.toHaveBeenCalled(); // Callback shouldn't be called
        });
    });
});