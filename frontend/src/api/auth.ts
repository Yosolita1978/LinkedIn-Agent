import { apiFetch } from "./client";

export interface AuthStatus {
  cookies_valid: boolean;
  cookies_found: boolean;
  message: string;
}

export function fetchAuthStatus(): Promise<AuthStatus> {
  return apiFetch<AuthStatus>("/api/auth/status");
}
