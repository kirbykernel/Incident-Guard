import type { Severity, Status } from "../services/types";

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <span className={`badge badge--severity-${severity}`}>{severity}</span>;
}

export function StatusBadge({ status }: { status: Status }) {
  return <span className={`badge badge--status-${status}`}>{status.replace("_", " ")}</span>;
}
