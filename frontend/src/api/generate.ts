import { apiFetch } from "./client";
import type { GenerateRequest, GenerateResponse, Purpose } from "../types";

export function generateMessage(request: GenerateRequest): Promise<GenerateResponse> {
  return apiFetch<GenerateResponse>("/api/generate/message", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function fetchPurposes(): Promise<{ purposes: Purpose[] }> {
  return apiFetch<{ purposes: Purpose[] }>("/api/generate/purposes");
}
