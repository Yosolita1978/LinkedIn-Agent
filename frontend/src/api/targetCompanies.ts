import { apiFetch } from "./client";

export interface TargetCompany {
  id: string;
  name: string;
  notes: string | null;
}

export interface TargetCompanyCreate {
  name: string;
  notes?: string | null;
}

export function fetchTargetCompanies(): Promise<TargetCompany[]> {
  return apiFetch<TargetCompany[]>("/api/target-companies");
}

export function addTargetCompany(company: TargetCompanyCreate): Promise<TargetCompany> {
  return apiFetch<TargetCompany>("/api/target-companies", {
    method: "POST",
    body: JSON.stringify(company),
  });
}

export function addTargetCompaniesBulk(
  companies: TargetCompanyCreate[]
): Promise<{ status: string; created: number; skipped: number }> {
  return apiFetch("/api/target-companies/bulk", {
    method: "POST",
    body: JSON.stringify(companies),
  });
}

export function deleteTargetCompany(id: string): Promise<void> {
  return apiFetch<void>(`/api/target-companies/${id}`, { method: "DELETE" });
}
