import { useState, type FormEvent } from "react";
import { createIncident } from "../services/api";
import type { IncidentCreateInput, Severity } from "../services/types";

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low"];

export function IncidentForm({ onCreated }: { onCreated: () => void }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState<Severity>("medium");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const input: IncidentCreateInput = { title, severity };
      if (description.trim()) input.description = description.trim();
      await createIncident(input);
      setTitle("");
      setDescription("");
      setSeverity("medium");
      onCreated();
    } catch {
      setError("Não foi possível criar o incidente.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="card incident-form" onSubmit={handleSubmit}>
      <h2>Novo incidente</h2>

      <label htmlFor="title">Título</label>
      <input
        id="title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        required
      />

      <label htmlFor="description">Descrição</label>
      <textarea
        id="description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        rows={3}
      />

      <label htmlFor="severity">Severidade</label>
      <select
        id="severity"
        value={severity}
        onChange={(e) => setSeverity(e.target.value as Severity)}
      >
        {SEVERITIES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      {error && <p className="error">{error}</p>}

      <button type="submit" disabled={submitting}>
        {submitting ? "Criando…" : "Criar incidente"}
      </button>
    </form>
  );
}
