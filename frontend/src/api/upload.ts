import { apiFetch } from "./client";

export interface UploadResult {
  records_processed: number;
  contacts_created: number;
  contacts_updated: number;
  messages_created: number;
  resurrection_found: number;
  errors: string[];
}

export interface UploadStatus {
  last_messages_upload: string | null;
  last_connections_upload: string | null;
  total_contacts: number;
  total_messages: number;
}

function uploadFile(path: string, file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<UploadResult>(path, { method: "POST", body: form });
}

export function uploadConnections(file: File): Promise<UploadResult> {
  return uploadFile("/api/upload/connections", file);
}

export function uploadMessages(file: File): Promise<UploadResult> {
  return uploadFile("/api/upload/messages", file);
}

export function fetchUploadStatus(): Promise<UploadStatus> {
  return apiFetch<UploadStatus>("/api/upload/status");
}
