import { apiFetch } from "./client";
import type { AppSettings } from "../types";

export function fetchSettings(): Promise<AppSettings> {
  return apiFetch<AppSettings>("/api/settings");
}

// Partial update — send only the fields you want to change. The backend PATCH
// applies just those (weekly cap and/or any persona field).
export function updateSettings(settings: Partial<AppSettings>): Promise<AppSettings> {
  return apiFetch<AppSettings>("/api/settings", {
    method: "PATCH",
    body: JSON.stringify(settings),
  });
}
