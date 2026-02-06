import { apiFetch } from "./client";
import type { OpportunitiesResponse } from "../types";

export function fetchOpportunities(hookType?: string): Promise<OpportunitiesResponse> {
  const query = hookType ? `?hook_type=${hookType}` : "";
  return apiFetch<OpportunitiesResponse>(`/api/resurrection/opportunities${query}`);
}

export function dismissOpportunity(id: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/resurrection/opportunities/${id}/dismiss`, {
    method: "POST",
  });
}
