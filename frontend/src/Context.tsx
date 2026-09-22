import { useState, type FormEvent } from "react";
import { ArrowLeft, Save } from "lucide-react";
import { api } from "./api";
import type { Company } from "./types";

function priorityText(company: Company) {
  if (company.priorities.length === 1 && company.priorities[0].id === "focus")
    return company.priorities[0].detail;
  return company.priorities
    .map(
      (p) =>
        `${p.importance === "high" ? "Prioritize" : p.importance === "watch" ? "Watch" : "Ignore"}: ${p.label}. ${p.detail}`,
    )
    .join("\n");
}

function competitorNames(value: string) {
  const seen = new Set<string>();
  return value
    .split(/[,\n]+/)
    .map((v) => v.trim())
    .filter((name) => {
      if (!name || seen.has(name.toLowerCase())) return false;
      seen.add(name.toLowerCase());
      return true;
    });
}

export default function Context({
  company,
  saved,
  back,
}: {
  company: Company;
  saved: (c: Company) => void;
  back: () => void;
}) {
  const initialFocus = priorityText(company);
  const [description, setDescription] = useState(
    [
      company.description,
      company.audience ? `Audience: ${company.audience}` : "",
    ]
      .filter(Boolean)
      .join("\n"),
  );
  const [focus, setFocus] = useState(initialFocus);
  const [competitors, setCompetitors] = useState(
    company.competitors.map((c) => c.name).join(", "),
  );
  const [name, setName] = useState(company.name);
  const [websites, setWebsites] = useState<Record<string, string>>(
    Object.fromEntries(
      company.competitors.map((c) => [c.name.toLowerCase(), c.domain || ""]),
    ),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const names = competitorNames(competitors);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!description.trim() || !focus.trim()) {
      setError("Describe your company and what matters to it.");
      return;
    }
    if (!names.length || names.length > 5 || names.some((n) => n.length > 70)) {
      setError("Add 1–5 competitor names, up to 70 characters each.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const next: Company = {
        name: name.trim() || "Your company",
        description: description.trim(),
        audience: "",
        priorities:
          focus === initialFocus
            ? company.priorities
            : [
                {
                  id: "focus",
                  label: "What matters most",
                  detail: focus.trim(),
                  importance: "high",
                },
              ],
        competitors: names.map((n) => ({
          name: n,
          domain: websites[n.toLowerCase()]?.trim() || "",
        })),
      };
      const result = await api<Company>("company", "PUT", next);
      saved(result);
      back();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="context-setup">
      <button className="text-link back-link" onClick={back} disabled={busy}>
        <ArrowLeft size={14} /> Back to briefing
      </button>
      <div className="page-heading">
        <div>
          <h1>Give your feed some context.</h1>
          <p>A few sentences are enough to tell jev what matters.</p>
        </div>
      </div>
      <form className="editor-section simple-context-form" onSubmit={save}>
        {error && (
          <div className="error-banner" role="alert">
            {error}
          </div>
        )}
        <label>
          Your company
          <span className="field-hint">What you build and who you serve.</span>
          <textarea
            required
            aria-label="Your company"
            rows={4}
            maxLength={2200}
            value={description}
            disabled={busy}
            placeholder="We build a project management tool for small software teams."
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <label>
          What matters
          <span className="field-hint">
            What deserves an alert, what to watch, and what to ignore.
          </span>
          <textarea
            required
            aria-label="What matters"
            rows={4}
            maxLength={1800}
            value={focus}
            disabled={busy}
            placeholder="Prioritize AI planning features and pricing changes. Watch GitHub and Slack integrations. Ignore hiring and general productivity tips."
            onChange={(e) => setFocus(e.target.value)}
          />
        </label>
        <label>
          Competitors
          <span className="field-hint">
            Up to 5 names, separated by commas. No websites needed.
          </span>
          <textarea
            required
            aria-label="Competitors"
            rows={2}
            maxLength={500}
            value={competitors}
            disabled={busy}
            placeholder="Linear, Asana, ClickUp"
            onChange={(e) => setCompetitors(e.target.value)}
          />
        </label>
        <details className="context-options">
          <summary>Optional details</summary>
          <label>
            Company name
            <input
              maxLength={80}
              value={name}
              disabled={busy}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          {names.slice(0, 5).map((n) => (
            <label key={n.toLowerCase()}>
              {n} website <span className="optional-label">(optional)</span>
              <input
                placeholder="example.com"
                value={websites[n.toLowerCase()] || ""}
                disabled={busy}
                onChange={(e) =>
                  setWebsites({
                    ...websites,
                    [n.toLowerCase()]: e.target.value,
                  })
                }
              />
            </label>
          ))}
        </details>
        <div className="context-actions">
          <button className="primary" disabled={busy} type="submit">
            <Save size={15} /> {busy ? "Saving…" : "Save context"}
          </button>
        </div>
      </form>
    </div>
  );
}
