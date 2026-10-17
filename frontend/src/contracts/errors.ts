export type ApiErrorCode =
  | "VALIDATION"
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "CONFLICT"
  | "RATE_LIMIT"
  | "NETWORK"
  | "UNAVAILABLE"
  | "INTERNAL";

export type ApiErrorBody = {
  error: {
    code: ApiErrorCode;
    message: string;
    fields?: Record<string, string>;
  };
};

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status: number;
  readonly fields?: Record<string, string>;

  constructor(
    code: ApiErrorCode,
    message: string,
    status: number,
    fields?: Record<string, string>,
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.fields = fields;
  }

  toJSON(): ApiErrorBody {
    return { error: { code: this.code, message: this.message, fields: this.fields } };
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}
