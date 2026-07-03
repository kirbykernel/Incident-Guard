import { useCallback, useEffect, useState } from "react";
import { listIncidents, updateIncidentStatus } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { IncidentForm } from "../components/IncidentForm";
import { SeverityBadge, StatusBadge } from "../components/SeverityBadge";
import type { Incident, Severity, Status } from "../services/types";

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low"];
const STATUSES: Status[] = ["open", "in_progress", "resolved", "closed"];
const PAGE_SIZE = 20;

export function Dashboard() {
  const { user, logout } = useAuth();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [severity, setSeverity] = useState<Severity | "">("");
  const [status, setStatus] = useState<Status | "">("");
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await listIncidents({
        page,
        pageSize: PAGE_SIZE,
        severity: severity || undefined,
        status: status || undefined,
      });
      setIncidents(result.items);
      setTotal(result.total);
    } finally {
      setLoading(false);
    }
  }, [page, severity, status]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleStatusChange(id: string, next: Status) {
    await updateIncidentStatus(id, next);
    load();
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>IncidentGuard</h1>
        <div className="dashboard-header-user">
          <span className="muted">
            {user?.full_name} · {user?.role}
          </span>
          <button className="secondary" onClick={logout}>
            Sair
          </button>
        </div>
      </header>

      <div className="toolbar">
        <select
          value={severity}
          onChange={(e) => {
            setPage(1);
            setSeverity(e.target.value as Severity | "");
          }}
        >
          <option value="">Todas as severidades</option>
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <select
          value={status}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value as Status | "");
          }}
        >
          <option value="">Todos os status</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace("_", " ")}
            </option>
          ))}
        </select>

        <button onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancelar" : "Novo incidente"}
        </button>
      </div>

      {showForm && (
        <IncidentForm
          onCreated={() => {
            setShowForm(false);
            setPage(1);
            load();
          }}
        />
      )}

      <div className="card">
        {loading ? (
          <p className="muted">Carregando…</p>
        ) : incidents.length === 0 ? (
          <p className="muted">Nenhum incidente encontrado.</p>
        ) : (
          <table className="incident-table">
            <thead>
              <tr>
                <th>Título</th>
                <th>Severidade</th>
                <th>Status</th>
                <th>Origem</th>
                <th>Criado em</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((incident) => (
                <tr key={incident.id}>
                  <td>{incident.title}</td>
                  <td>
                    <SeverityBadge severity={incident.severity} />
                  </td>
                  <td>
                    <StatusBadge status={incident.status} />
                  </td>
                  <td className="muted">{incident.source}</td>
                  <td className="muted">
                    {new Date(incident.created_at).toLocaleString()}
                  </td>
                  <td>
                    <select
                      value={incident.status}
                      onChange={(e) =>
                        handleStatusChange(incident.id, e.target.value as Status)
                      }
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s.replace("_", " ")}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="pagination">
        <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          Anterior
        </button>
        <span className="muted">
          Página {page} de {totalPages} · {total} incidentes
        </span>
        <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
          Próxima
        </button>
      </div>
    </div>
  );
}
