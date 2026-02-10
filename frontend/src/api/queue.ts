import { apiFetch } from "./client";
import type { QueueListResponse, QueueStats, QueueItem, QueueItemCreate } from "../types";

export function fetchQueueItems(
  status?: string,
  useCase?: string,
  limit: number = 50,
  offset: number = 0,
): Promise<QueueListResponse> {
  const query = new URLSearchParams();
  if (status) query.set("status", status);
  if (useCase) query.set("use_case", useCase);
  query.set("limit", String(limit));
  query.set("offset", String(offset));
  return apiFetch<QueueListResponse>(`/api/queue/?${query.toString()}`);
}

export function fetchQueueStats(): Promise<QueueStats> {
  return apiFetch<QueueStats>("/api/queue/stats");
}

export function addToQueue(item: QueueItemCreate): Promise<QueueItem> {
  return apiFetch<QueueItem>("/api/queue/", {
    method: "POST",
    body: JSON.stringify(item),
  });
}

export function updateQueueStatus(id: string, status: string): Promise<QueueItem> {
  return apiFetch<QueueItem>(`/api/queue/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function updateQueueMessage(id: string, message: string): Promise<QueueItem> {
  return apiFetch<QueueItem>(`/api/queue/${id}/message`, {
    method: "PATCH",
    body: JSON.stringify({ generated_message: message }),
  });
}

export function regenerateQueueMessage(
  id: string,
  customInstruction?: string,
): Promise<{ message: string; all_variations: string[] }> {
  return apiFetch<{ message: string; all_variations: string[] }>(
    `/api/queue/${id}/regenerate`,
    {
      method: "POST",
      body: JSON.stringify({ custom_instruction: customInstruction || null }),
    },
  );
}

export function deleteQueueItem(id: string): Promise<void> {
  return apiFetch<void>(`/api/queue/${id}`, { method: "DELETE" });
}
