export type Role = "admin" | "analyst" | "viewer";
export type Severity = "critical" | "high" | "medium" | "low";
export type Status = "open" | "in_progress" | "resolved" | "closed";
export type Source = "alertmanager" | "security_scanner" | "falco" | "synthetic" | "manual";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Incident {
  id: string;
  title: string;
  description: string | null;
  severity: Severity;
  status: Status;
  source: Source;
  created_by: string | null;
  assigned_to: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface IncidentListResponse {
  items: Incident[];
  total: number;
  page: number;
  page_size: number;
}

export interface IncidentCreateInput {
  title: string;
  description?: string;
  severity: Severity;
  assigned_to?: string;
}
