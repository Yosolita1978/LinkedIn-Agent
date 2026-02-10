import { apiFetch } from "./client";
import type { NetworkOverview } from "../types";

export function fetchNetworkOverview(): Promise<NetworkOverview> {
  return apiFetch<NetworkOverview>("/api/analytics/overview");
}
