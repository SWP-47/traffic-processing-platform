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
    
    async onResponse({ response }) {
        if (!response.ok) {
            let errorBody;
            try {
                errorBody = await response.json();
            } catch {
                errorBody = null;
            }

            if (response.status === 401) auth.requestTokenRenewal();
            
            throw mapHttpError(response.status, errorBody);
        }
        
        return response;
    }
});

export default apiClient;