/**
 * This file provied a client singleton to communicate with CnSS REST API.
 */

import createClient from "openapi-fetch";
import type { paths } from "./schema";
import { mapHttpError } from "./errors";

// BaseURL is set to '' as MUI is proxying API queries.
const apiClient = createClient<paths>({ baseUrl: '' });

apiClient.use({
    async onRequest({ request }) {
        // TODO: authentication workflow
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
            
            throw mapHttpError(response.status, errorBody);
        }
        
        // TODO: authentication workflow
        return response;
    }
});

export default apiClient;