import { useEffect, useId, useRef, type ReactNode } from "react";
import { ArrowUpRight, Eye, Minus, Radio, X } from "lucide-react";
import type { Source } from "./types";

export function Brand({ name }: { name: "tavily" | "jev" }) {
  return name === "tavily" ? (
    <img className="brand tavily" src="/brand/tavily.svg" alt="Tavily" />
  ) : (
    <span className="brand jev">jev</span>
  );
}
export const badgeClass = (value: string) => value.toLowerCase();
export function Badge({ value }: { value: string }) {
  const Icon = value === "Alert" ? Radio : value === "Watch" ? Eye : Minus;
  return (
    <span className={`badge ${badgeClass(value)}`}>
      <Icon size={12} />
      {value}
    </span>
  );
}
export function Avatar({ name }: { name: string }) {
  return (
    <span className={`avatar avatar-${name.charCodeAt(0) % 4}`}>
      {name.slice(0, 1)}
    </span>
  );
}
export function Modal({
  title,
  children,
  close,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  close: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    ref.current?.showModal();
    const element = ref.current;
    return () => element?.close();
  }, []);
  return (
    <dialog
      aria-labelledby={titleId}
      ref={ref}
      className={`modal ${wide ? "wide" : ""}`}
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
      onClick={(e) => {
        if (e.target === ref.current) close();
      }}
    >
      <div className="modal-head">
        <h2 id={titleId}>{title}</h2>
        <button
          className="icon-button"
          aria-label="Close dialog"
          onClick={close}
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function SourceDetail({
  source,
  close,
}: {
  source: Source;
  close: () => void;
}) {
  const d = source.decision;
  return (
    <Modal title="Follow the signal" close={close} wide>
      <div className="detail-top">
        <Avatar name={source.competitor || source.domain} />
        <div>
          <strong>{source.competitor || source.domain}</strong>
          <span className="meta">
            {source.source_type || source.domain} ·{" "}
            {source.published_date || "Retrieved this session"}
          </span>
        </div>
        {d && <Badge value={d.verdict} />}
      </div>
      <h3 className="detail-title">{source.title}</h3>
      {source.evaluation_error && (
        <p className="error-banner" role="alert">
          jev could not evaluate this source: {source.evaluation_error}
        </p>
      )}
      {d && (
        <section className="decision-box">
          <div className="eyebrow">
            <Brand name="jev" /> THE DECISION
          </div>
          <h3>{d.verdict}</h3>
          <div className="decision-meta">
            <span>
              {d.provider === "Jev"
                ? `${Math.round((d.confidence || 0) * 100)}% model confidence`
                : "Decision unavailable"}
            </span>
            {d.latency_ms != null && (
              <span>{d.latency_ms.toLocaleString()} ms round trip</span>
            )}
          </div>
          {d.provider === "Jev" && (
            <div className="distribution">
              {Object.entries(d.probabilities).map(([label, p]) => (
                <div key={label}>
                  <span>{label}</span>
                  <div className="bar">
                    <i style={{ width: `${p * 100}%` }} />
                  </div>
                  <span>{Math.round(p * 100)}%</span>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
      <section className="source-box">
        <div className="eyebrow">
          <Brand name="tavily" /> THE EVIDENCE
        </div>
        <p className="source-label">Retrieved source passage</p>
        <blockquote>{source.content}</blockquote>
        {source.url && /^https?:\/\//.test(source.url) && (
          <a
            className="text-link"
            href={source.url}
            target="_blank"
            rel="noreferrer"
          >
            Read original source <ArrowUpRight size={14} />
          </a>
        )}
      </section>
      <p className="fine-print">
        Source relevance is not a measure of truth. Review the original source
        before acting.
      </p>
    </Modal>
  );
}
