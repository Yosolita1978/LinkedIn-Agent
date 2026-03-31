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
