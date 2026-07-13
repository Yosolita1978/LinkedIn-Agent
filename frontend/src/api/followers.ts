import { apiFetch } from "./client";
import type {
  ScanResponse,
  FollowerCandidate,
  GenerateNotesResponse,
  CandidateWithNote,
  ConnectResponse,
  TrackResponse,
  ConnectionRequestListResponse,
  CheckAcceptancesResponse,
  ConnectionRequestStatsResponse,
  BacklogListResponse,
  BacklogCandidate,
  BacklogUpdate,
} from "../types";

export async function scanFollowers(
  maxFollowers: number = 50,
  maxProfiles: number = 15
): Promise<ScanResponse> {
  return apiFetch<ScanResponse>("/api/followers/scan", {
    method: "POST",
    body: JSON.stringify({
      max_followers: maxFollowers,
      max_profiles: maxProfiles,
    }),
  });
}

export async function generateNotes(
  candidates: FollowerCandidate[]
): Promise<GenerateNotesResponse> {
  return apiFetch<GenerateNotesResponse>("/api/followers/generate-notes", {
    method: "POST",
    body: JSON.stringify({ candidates }),
  });
}

export async function connectWithCandidates(
  candidates: CandidateWithNote[],
  maxConnections: number = 10
): Promise<ConnectResponse> {
  return apiFetch<ConnectResponse>("/api/followers/connect", {
    method: "POST",
    body: JSON.stringify({
      candidates,
      max_connections: maxConnections,
    }),
  });
}

export async function trackConnectionRequests(
  candidates: CandidateWithNote[]
): Promise<TrackResponse> {
  return apiFetch<TrackResponse>("/api/followers/track", {
    method: "POST",
    body: JSON.stringify({ candidates }),
  });
}

export async function listConnectionRequests(
  status?: string
): Promise<ConnectionRequestListResponse> {
  const params = status ? `?status=${status}` : "";
  return apiFetch<ConnectionRequestListResponse>(
    `/api/followers/requests${params}`
  );
}

export async function checkAcceptances(): Promise<CheckAcceptancesResponse> {
  return apiFetch<CheckAcceptancesResponse>("/api/followers/check-acceptances", {
    method: "POST",
  });
}

export async function getConnectionRequestStats(): Promise<ConnectionRequestStatsResponse> {
  return apiFetch<ConnectionRequestStatsResponse>(
    "/api/followers/requests/stats"
  );
}

export async function fetchCandidates(
  status?: string,
  limit: number = 20,
  offset: number = 0
): Promise<BacklogListResponse> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return apiFetch<BacklogListResponse>(
    `/api/followers/candidates?${params.toString()}`
  );
}

export async function updateCandidate(
  id: string,
  update: BacklogUpdate
): Promise<BacklogCandidate> {
  return apiFetch<BacklogCandidate>(`/api/followers/candidates/${id}`, {
    method: "PATCH",
    body: JSON.stringify(update),
  });
}
