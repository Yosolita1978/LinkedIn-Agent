import { apiFetch } from "./client";

export interface InboxConversation {
  contact_id: string;
  contact_name: string;
  contact_company: string | null;
  contact_headline: string | null;
  contact_linkedin_url: string | null;
  warmth_score: number | null;
  last_message_date: string | null;
  last_message_preview: string | null;
  last_message_direction: string | null;
  total_messages: number;
  needs_reply: boolean;
}

export interface InboxListResponse {
  conversations: InboxConversation[];
  total: number;
}

export interface InboxMessage {
  id: string;
  direction: string;
  date: string;
  content: string | null;
  content_length: number | null;
  is_substantive: boolean | null;
  conversation_id: string | null;
  synced_at: string | null;
}

export interface InboxConversationDetail {
  contact_id: string;
  messages: InboxMessage[];
}

export interface InboxSyncResponse {
  conversations_fetched: number;
  conversations_synced: number;
  new_messages: number;
  skipped_no_contact: number;
}

export interface InboxStats {
  total_conversations: number;
  needs_reply: number;
  waiting_for_them: number;
}

export function fetchInbox(filter?: string, limit?: number, offset?: number): Promise<InboxListResponse> {
  const params = new URLSearchParams();
  if (filter) params.set("filter", filter);
  if (limit) params.set("limit", String(limit));
  if (offset) params.set("offset", String(offset));
  const qs = params.toString();
  return apiFetch<InboxListResponse>(`/api/inbox${qs ? `?${qs}` : ""}`);
}

export function fetchConversation(contactId: string, limit?: number): Promise<InboxConversationDetail> {
  const qs = limit ? `?limit=${limit}` : "";
  return apiFetch<InboxConversationDetail>(`/api/inbox/${contactId}${qs}`);
}

export function syncInbox(limit?: number): Promise<InboxSyncResponse> {
  const qs = limit ? `?limit=${limit}` : "";
  return apiFetch<InboxSyncResponse>(`/api/inbox/sync${qs}`, { method: "POST" });
}

export function fetchInboxStats(): Promise<InboxStats> {
  return apiFetch<InboxStats>("/api/inbox/stats");
}
