const BASE_URL = "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${BASE_URL}${path}`;

  const headers: Record<string, string> = {};
  if (options?.method && ["POST", "PATCH", "PUT"].includes(options.method)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    ...options,
    headers: { ...headers, ...options?.headers },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Unknown error" }));
    const message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<T>;
}
