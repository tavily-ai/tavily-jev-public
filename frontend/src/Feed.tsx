import { useEffect, useState } from "react";
import {
  ArrowRight,
  ChevronRight,
  LoaderCircle,
  Search,
  Square,
} from "lucide-react";
import { Badge, Brand } from "./shared";
import type { Company, Source, Verdict } from "./types";

type Props = {
  company: Company;
  connected: boolean;
  items: Source[];
  running: boolean;
  stage: string;
  window: string;
  setWindow: (v: string) => void;
  run: () => void;
  stop: () => void;
  reset: () => void;
  select: (s: Source) => void;
  edit: () => void;
  completed: string;
};

export default function Feed(p: Props) {
  const [filter, setFilter] = useState<"All" | Verdict>("All");
  const { company, items, running } = p;
  useEffect(() => {
    if (running) setFilter("All");
  }, [running]);
  const decided = items.filter((i) => i.decision).length;
  const count = (value: string) =>
    value === "All"
      ? items.length
      : items.filter((i) => i.decision?.verdict === value).length;
  const visible = items.filter(
    (i) => filter === "All" || i.decision?.verdict === filter,
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Signal, not noise.</h1>
          <p>Competitor updates, filtered for what matters to your company.</p>
        </div>
        <div className="heading-actions">
          <select
            aria-label="Search window"
            value={p.window}
            onChange={(e) => p.setWindow(e.target.value)}
            disabled={running}
          >
            <option value="day">Last 24 hours</option>
            <option value="week">Last 7 days</option>
            <option value="month">Last 30 days</option>
          </select>
          <button className="primary" onClick={running ? p.stop : p.run}>
            {running ? <Square size={15} /> : <Search size={15} />}
            {running
              ? "Stop scan"
              : p.connected
                ? "Run daily scan"
                : "Connect API keys"}
          </button>
        </div>
      </div>
      <section className="context-summary" aria-label="Company context">
        <span className="company-initial">{company.name.charAt(0)}</span>
        <div>
          <strong>{company.name}</strong>
          <span className="context-topics">
            {company.priorities
              .filter((p) => p.importance !== "off")
              .map((p) => p.label)
              .join(" · ") || "No active priorities"}
          </span>
        </div>
        <button className="text-link" disabled={running} onClick={p.edit}>
          Edit context <ChevronRight size={14} />
        </button>
      </section>
      <div
        className="pipeline-simple"
        aria-label="Discovery and evaluation progress"
      >
        <span>
          <Brand name="tavily" />
          <span>{items.length} sources found</span>
        </span>
        <ArrowRight size={16} />
        <span>
          <Brand name="jev" />
          <span>{decided} evaluated</span>
        </span>
        <span className="scan-status" role="status">
          {running ? (
            <>
              <LoaderCircle size={13} className="spin" />
              {p.stage}
            </>
          ) : p.completed ? (
            p.completed
          ) : (
            "Ready to scan"
          )}
        </span>
      </div>
      <section className="results-panel" aria-label="jev decisions">
        <div className="results-toolbar">
          <h2>What matters</h2>
          <div className="result-filters" aria-label="Filter decisions">
            {(["All", "Alert", "Watch", "Ignore"] as const).map((value) => (
              <button
                key={value}
                aria-pressed={filter === value}
                onClick={() => setFilter(value)}
                className={filter === value ? "selected" : ""}
              >
                {value}
                <span>{count(value)}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="result-columns" aria-hidden="true">
          <span>UPDATE</span>
          <span>SOURCE EXCERPT</span>
          <span>jev decision</span>
          <span />
        </div>
        <div className="results-list">
          {visible.map((item) => (
            <button
              className="result-row"
              key={item.id}
              onClick={() => p.select(item)}
            >
              <div className="result-update">
                <span className="result-meta">
                  {item.competitor || item.domain}
                  <span>·</span>
                  {item.kind}
                </span>
                <h3>{item.title}</h3>
              </div>
              <div className="result-reason">
                <span>{item.domain}</span>
                <p>{item.content}</p>
              </div>
              <div className="result-verdict">
                {item.decision ? (
                  <Badge value={item.decision.verdict} />
                ) : (
                  <span className="pending-status">
                    {running && !item.evaluation_error && (
                      <LoaderCircle size={13} className="spin" />
                    )}
                    {item.evaluation_error
                      ? "Unavailable"
                      : running
                        ? "Queued"
                        : "Not evaluated"}
                  </span>
                )}
              </div>
              <ChevronRight size={15} />
            </button>
          ))}
          {!visible.length && (
            <div className="empty">
              <Search size={25} />
              <h3>
                {running
                  ? "Finding your next signal…"
                  : items.length
                    ? `No ${filter.toLowerCase()} updates`
                    : p.connected
                      ? "Your next briefing starts here"
                      : "Connect Tavily and jev"}
              </h3>
              <p>
                {items.length
                  ? "Try another filter to see the rest of your briefing."
                  : p.connected
                    ? "Run a scan to find competitor news, launches, and pricing updates."
                    : "Add your API keys to start searching real competitor updates."}
              </p>
            </div>
          )}
        </div>
      </section>
      <div className="feed-footer">
        <span>Live Tavily sources · jev decisions</span>
        <button className="text-link" disabled={running} onClick={p.reset}>
          Reset briefing
        </button>
      </div>
    </>
  );
}
