/**
 * This file provied a client singleton to communicate with CnSS REST API.
 */

import createClient from "openapi-fetch";
import type { paths } from "./schema";
import { mapHttpError } from "./errors";
import auth from "@/services/authentication";

// BaseURL is set to '' as MUI is proxying API queries.
const apiClient = createClient<paths>({ baseUrl: '' });

apiClient.use({
    async onRequest({ request }) {
        const token = auth.getToken();
        
        if (token) {
            request.headers.set('Authorization', `Bearer ${token}`);
        }

        return request;
    },

    async onResponse({ request, response }) {
        // In case of authentication error
        if (response.status === 401) {
            const url = new URL(request.url);
            
            if (url.pathname !== '/api/v1/auth/refresh' && url.pathname !== '/api/v1/auth/login') {
                // Try to refresh token
                const isRefreshed = await auth.handleAuthError();
                
                if (isRefreshed) {
                    // Clone original query, set new token and execute
                    const newToken = auth.getToken();
                    const clonedRequest = new Request(request.url, {
                        method: request.method,
                        headers: request.headers,
                        body: request.body,
                    });
                    clonedRequest.headers.set('Authorization', `Bearer ${newToken}`);
                    
                    return fetch(clonedRequest);
                }
            }
        }

        if (!response.ok) {
            let errorBody;
            try {
                errorBody = await response.json();
            } catch {
                errorBody = null;
            }
            
            throw mapHttpError(response.status, errorBody);
        }
        
        return response;
    }
});

export default apiClient;