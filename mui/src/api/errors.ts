export type ApiErrorCode = 
    | 'bad_request'
    | 'unauthorized'
    | 'invalid_credentials'
    | 'forbidden'
    | 'not_found'
    | 'internal_error'
    | 'network_error'
    | 'unknown';

export type ApiErrorType = 'expected' | 'unexpected';

export class ApiError extends Error {
    public code: ApiErrorCode;
    public status: number | null;
    public type: ApiErrorType;

    constructor(
        code: ApiErrorCode,
        message: string,
        status: number | null,
        type: ApiErrorType
    ) {
        super(message);
        this.code = code;
        this.status = status;
        this.type = type;
        this.name = 'ApiError';
    }
}

const ERROR_MESSAGES: Record<number, string> = {
    400: 'Malformed request or missing required fields',
    401: 'Authorization is required',
    403: 'Access is denied',
    404: 'Requested resource does not exist',
    500: 'Server internal error'
};

export function mapHttpError(status: number, errorBody?: unknown): ApiError {
    let code = 'unknown';
    let message = 'Unknown message';

    if (errorBody && typeof errorBody == 'object') {
        const e = errorBody as Record<string, unknown>;

        if (e.error && typeof e.error == 'string') code = e.error;

        if (e.message && typeof e.message == 'string') message = e.message;
        else if (ERROR_MESSAGES[status]) message = ERROR_MESSAGES[status];
    }

    const type = status >= 500 ? 'unexpected' : 'expected';

    return new ApiError(code as ApiErrorCode, message, status, type);
}