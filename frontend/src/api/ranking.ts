import { apiFetch } from "./client";
import type { RecommendationsResponse } from "../types";

export function fetchRecommendations(
  limit = 15,
  segment?: string,
): Promise<RecommendationsResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (segment) params.set("segment", segment);
  return apiFetch<RecommendationsResponse>(`/api/ranking/recommendations?${params}`);
}
