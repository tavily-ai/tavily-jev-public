import { useEffect, useRef, useState } from "react";
import { CircleHelp, Settings2, Radar, X } from "lucide-react";
import { api, stream } from "./api";
import { Brand, Modal, SourceDetail } from "./shared";
import Feed from "./Feed";
import Context from "./Context";
import Connections from "./Connections";
import type { Config, Source } from "./types";

export default function App() {
  const [config, setConfig] = useState<Config | null>(null);
  const [page, setPage] = useState("feed");
  const [items, setItems] = useState<Source[]>([]);
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState("");
  const [error, setError] = useState("");
  const [window, setWindow] = useState("day");
  const [selected, setSelected] = useState<Source | null>(null);
  const [connections, setConnections] = useState(false);
  const [guide, setGuide] = useState(false);
  const [completed, setCompleted] = useState("");
  const controller = useRef<AbortController | null>(null);
  const busy = running;
  useEffect(() => {
    api<Config>("config")
      .then(setConfig)
      .catch((e) => setError(e.message));
    return () => controller.current?.abort();
  }, []);
  useEffect(() => {
    globalThis.scrollTo(0, 0);
  }, [page]);
  function reset() {
    setCompleted("");
    setError("");
    setStage("");
    setItems([]);
  }
  async function run() {
    if (!config) return;
    if (!config.connected.tavily || !config.connected.jev) {
      setConnections(true);
      return;
    }
    controller.current = new AbortController();
    setItems([]);
    setCompleted("");
    setError("");
    setRunning(true);
    setStage("Starting your scan…");
    try {
      await stream(
        "scan",
        { window, company: config.company },
        (e) => {
          if (e.type === "source") setItems((v) => [...v, e.item]);
          if (e.type === "decision")
            setItems((v) =>
              v.map((i) =>
                i.id === e.id ? { ...i, decision: e.decision } : i,
              ),
            );
          if (e.type === "source_error")
            setItems((v) =>
              v.map((i) =>
                i.id === e.id ? { ...i, evaluation_error: e.message } : i,
              ),
            );
          if (e.type === "stage") setStage(e.message);
          if (e.type === "warning") setError(e.message);
          if (e.type === "complete")
            setCompleted(
              e.failed
                ? `Scan finished · ${e.failed} source(s) could not be evaluated`
                : `Scan complete · ${e.count} sources processed`,
            );
        },
        controller.current.signal,
      );
    } catch (e) {
      setError(
        (e as Error).name === "AbortError"
          ? "Scan stopped. Completed decisions remain visible."
          : (e as Error).message,
      );
    } finally {
      setRunning(false);
    }
  }
  if (!config)
    return (
      <div className="boot">
        <Radar size={34} />
        <h1>Signal Desk</h1>
        <p>{error || "Getting your workspace ready…"}</p>
        {error && (
          <button className="primary" onClick={() => location.reload()}>
            Retry
          </button>
        )}
      </div>
    );
  return (
    <div className="app">
      <header className="app-header">
        <div className="product-lockup">
          <Brand name="tavily" />
          <span className="product-name">Signal Desk</span>
        </div>

        <div className="header-tools">
          <button
            className="icon-button"
            aria-label="Connections"
            title="Connections"
            onClick={() => setConnections(true)}
            disabled={busy}
          >
            <Settings2 size={18} />
          </button>
          <button
            className="icon-button"
            aria-label="Quick start"
            title="Quick start"
            onClick={() => setGuide(true)}
          >
            <CircleHelp size={18} />
          </button>
        </div>
      </header>
      <main>
        {error && (
          <div className="error-banner" role="alert">
            <span>{error}</span>
            <button
              className="icon-button"
              aria-label="Dismiss message"
              onClick={() => setError("")}
            >
              <X size={14} />
            </button>
          </div>
        )}
        {page === "feed" && (
          <Feed
            company={config.company}
            connected={config.connected.tavily && config.connected.jev}
            items={items}
            running={running}
            stage={stage}
            window={window}
            setWindow={setWindow}
            run={run}
            stop={() => controller.current?.abort()}
            reset={reset}
            select={setSelected}
            edit={() => {
              if (!busy) setPage("context");
            }}
            completed={completed}
          />
        )}
        {page === "context" && (
          <Context
            company={config.company}
            saved={(company) => {
              setConfig({ ...config, company });
              setItems([]);
              setCompleted("");
            }}
            back={() => setPage("feed")}
          />
        )}
      </main>
      {selected && (
        <SourceDetail
          source={items.find((i) => i.id === selected.id) || selected}
          close={() => setSelected(null)}
        />
      )}
      {connections && (
        <Connections
          connected={config.connected}
          close={() => setConnections(false)}
          save={(connected) => setConfig({ ...config, connected })}
        />
      )}
      {guide && (
        <Modal title="Get started in two steps" close={() => setGuide(false)}>
          <ol className="guide-steps">
            <li>
              <strong>Set your context.</strong>
              <p>
                Edit Forma’s company context and choose which topics deserve
                attention.
              </p>
            </li>
            <li>
              <strong>Run a daily scan.</strong>
              <p>
                Tavily finds sources. jev sorts them into Alert, Watch, and
                Ignore. Click any update to see the evidence. Change a priority
                and scan again to see the difference.
              </p>
            </li>
          </ol>
          <p className="fine-print">
            Every scan uses Tavily search and jev evaluation. Connect both API
            keys using the Connections button before running your first scan.
          </p>
        </Modal>
      )}
    </div>
  );
}
