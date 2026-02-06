// ============================================================================
// Contact Types
// ============================================================================

export interface WarmthBreakdown {
  recency: number;
  frequency: number;
  depth: number;
  responsiveness: number;
  initiation: number;
}

export interface Contact {
  id: string;
  linkedin_url: string;
  name: string;
  headline: string | null;
  location: string | null;
  company: string | null;
  position: string | null;
  warmth_score: number | null;
  segment_tags: string[] | null;
  manual_tags: string[] | null;
  last_message_date: string | null;
  last_message_direction: string | null;
  total_messages: number;
  created_at: string;
}

export interface ContactListResponse {
  contacts: Contact[];
  total: number;
  page: number;
  page_size: number;
}

export interface MessageMetadata {
  total_messages: number;
  first_message_date: string | null;
  last_message_date: string | null;
  last_message_direction: string | null;
  messages_sent: number;
  messages_received: number;
}

export interface ResurrectionOpportunitySummary {
  id: string;
  hook_type: string;
  hook_detail: string | null;
  detected_at: string;
  is_active: boolean;
}

export interface ContactDetail extends Contact {
  about: string | null;
  email: string | null;
  experience: Record<string, unknown>[] | null;
  education: Record<string, unknown>[] | null;
  connection_date: string | null;
  scraped_at: string | null;
  warmth_breakdown: WarmthBreakdown | null;
  warmth_calculated_at: string | null;
  message_metadata: MessageMetadata | null;
  resurrection_opportunities: ResurrectionOpportunitySummary[];
  updated_at: string;
}

export interface ContactStats {
  total_contacts: number;
  contacts_with_messages: number;
  contacts_without_messages: number;
  warmth_distribution: {
    hot: number;
    warm: number;
    cool: number;
    cold: number;
    none: number;
  };
  average_warmth: number;
}

export interface TopWarmthContact {
  id: string;
  name: string;
  company: string | null;
  headline: string | null;
  warmth_score: number;
  warmth_breakdown: WarmthBreakdown | null;
  total_messages: number;
  last_message_date: string | null;
}

// ============================================================================
// Resurrection Types
// ============================================================================

export interface ResurrectionOpportunity {
  id: string;
  contact_id: string;
  contact_name: string;
  contact_company: string | null;
  contact_headline: string | null;
  warmth_score: number | null;
  hook_type: string;
  hook_detail: string | null;
  detected_at: string;
}

export interface OpportunitiesResponse {
  count: number;
  opportunities: ResurrectionOpportunity[];
}

// ============================================================================
// Queue Types
// ============================================================================

export interface QueueItem {
  id: string;
  contact_id: string;
  use_case: string;
  outreach_type: string;
  purpose: string;
  generated_message: string | null;
  status: string;
  created_at: string;
  approved_at: string | null;
  sent_at: string | null;
  replied_at: string | null;
  contact_name: string;
  contact_headline: string | null;
  contact_company: string | null;
}

export interface QueueListResponse {
  items: QueueItem[];
  total: number;
}

export interface QueueStats {
  total: number;
  by_status: Record<string, number>;
  by_use_case: Record<string, number>;
}

export interface QueueItemCreate {
  contact_id: string;
  use_case: string;
  outreach_type: string;
  purpose: string;
  generated_message: string | null;
}

// ============================================================================
// Generate Types
// ============================================================================

export interface Purpose {
  id: string;
  description: string;
}

export interface GenerateRequest {
  contact_id: string;
  purpose: string;
  segment?: string | null;
  custom_context?: string | null;
  num_variations?: number;
}

export interface GenerateResponse {
  contact: {
    id: string;
    name: string;
    company: string | null;
    headline: string | null;
    warmth_score: number | null;
  };
  purpose: string;
  segment: string | null;
  variations: string[];
  tokens_used: number;
}
