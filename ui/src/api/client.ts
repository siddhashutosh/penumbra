// Typed fetch wrapper: unwraps the backend error envelope, one retry on 5xx.

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, retry = true): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(path, { headers: { "Content-Type": "application/json" } });
  } catch {
    throw new ApiError("NETWORK_ERROR", "Backend unreachable — is uvicorn running on :8001?", 0);
  }
  if (!resp.ok) {
    if (retry && resp.status >= 500) {
      await new Promise((r) => setTimeout(r, 800));
      return request<T>(path, false);
    }
    let code = "HTTP_ERROR";
    let message = `Request failed (${resp.status})`;
    try {
      const body = await resp.json();
      if (body?.error) {
        code = body.error.code ?? code;
        message = body.error.message ?? message;
      }
    } catch {
      /* non-JSON */
    }
    throw new ApiError(code, message, resp.status);
  }
  return (await resp.json()) as T;
}

export const api = { get: <T>(path: string) => request<T>(path) };
