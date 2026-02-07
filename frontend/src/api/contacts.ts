import { apiFetch } from "./client";
import type {
  ContactListResponse,
  ContactDetail,
  ContactStats,
  TopWarmthContact,
} from "../types";

interface FetchContactsParams {
  page?: number;
  page_size?: number;
  search?: string;
  warmth_min?: number;
  warmth_max?: number;
  segment?: string;
  sort_by?: string;
  sort_order?: string;
}

export function fetchContacts(params: FetchContactsParams = {}): Promise<ContactListResponse> {
  const query = new URLSearchParams();
  if (params.page) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));
  if (params.search) query.set("search", params.search);
  if (params.warmth_min !== undefined) query.set("warmth_min", String(params.warmth_min));
  if (params.warmth_max !== undefined) query.set("warmth_max", String(params.warmth_max));
  if (params.segment) query.set("segment", params.segment);
  if (params.sort_by) query.set("sort_by", params.sort_by);
  if (params.sort_order) query.set("sort_order", params.sort_order);

  const qs = query.toString();
  return apiFetch<ContactListResponse>(`/api/contacts/${qs ? `?${qs}` : ""}`);
}

export function fetchContactDetail(id: string): Promise<ContactDetail> {
  return apiFetch<ContactDetail>(`/api/contacts/${id}`);
}

export function fetchContactStats(): Promise<ContactStats> {
  return apiFetch<ContactStats>("/api/contacts/stats");
}

export function fetchTopWarmth(limit: number = 10): Promise<TopWarmthContact[]> {
  return apiFetch<TopWarmthContact[]>(`/api/contacts/top-warmth?limit=${limit}`);
}

export interface SegmentationResult {
  status: string;
  contacts_processed: number;
  segments: {
    mujertech: number;
    cascadia: number;
    job_target: number;
  };
  no_segment: number;
}

export function runSegmentation(allContacts: boolean = true): Promise<SegmentationResult> {
  return apiFetch<SegmentationResult>(`/api/contacts/segment?all_contacts=${allContacts}`, {
    method: "POST",
  });
}
