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
  // For file uploads (FormData) the browser must set the multipart Content-Type
  // with its boundary, so only force JSON for non-FormData bodies.
  const isFormData =
    typeof FormData !== "undefined" && options?.body instanceof FormData;
  if (options?.method && ["POST", "PATCH", "PUT"].includes(options.method) && !isFormData) {
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
