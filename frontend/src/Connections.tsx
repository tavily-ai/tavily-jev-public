import { useState } from "react";
import { Check, KeyRound } from "lucide-react";
import { api } from "./api";
import { Brand, Modal } from "./shared";

export default function Connections({
  connected,
  close,
  save,
}: {
  connected: { tavily: boolean; jev: boolean };
  close: () => void;
  save: (c: { tavily: boolean; jev: boolean }) => void;
}) {
  const [tavily, setTavily] = useState("");
  const [jev, setJev] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit() {
    setBusy(true);
    setError("");
    try {
      const c = await api<{ tavily: boolean; jev: boolean }>(
        "connections",
        "POST",
        { tavily, jev },
      );
      setTavily("");
      setJev("");
      save(c);
      close();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Connect your tools" close={close}>
      <p className="modal-intro">
        Bring live search and real jev decisions into your briefing.
      </p>
      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <div className="connection-field">
          <div>
            <Brand name="tavily" />
            <span className={connected.tavily ? "connected" : "not-connected"}>
              {connected.tavily ? <Check size={12} /> : <KeyRound size={12} />}{" "}
              {connected.tavily ? "Key configured" : "Key needed"}
            </span>
          </div>
          <label>
            Tavily API key
            <input
              type="password"
              autoComplete="off"
              value={tavily}
              onChange={(e) => setTavily(e.target.value)}
              placeholder={
                connected.tavily ? "Leave blank to keep current key" : "tvly-…"
              }
            />
          </label>
          <a href="https://app.tavily.com" target="_blank" rel="noreferrer">
            Get a Tavily key ↗
          </a>
        </div>
        <div className="connection-field">
          <div>
            <Brand name="jev" />
            <span className={connected.jev ? "connected" : "not-connected"}>
              {connected.jev ? <Check size={12} /> : <KeyRound size={12} />}{" "}
              {connected.jev ? "Key configured" : "Key needed"}
            </span>
          </div>
          <label>
            jev API key
            <input
              type="password"
              autoComplete="off"
              value={jev}
              onChange={(e) => setJev(e.target.value)}
              placeholder={
                connected.jev
                  ? "Leave blank to keep current key"
                  : "Your jev key"
              }
            />
          </label>
          <a
            href="https://docs.typesafe.ai/api"
            target="_blank"
            rel="noreferrer"
          >
            jev API documentation ↗
          </a>
        </div>
        <p className="fine-print">
          Keys stay in this local server’s memory until it restarts. To keep
          them between sessions, add them to the project’s .env file. Key
          validity is checked when you run a live scan.
        </p>
        <button
          className="primary full-width"
          disabled={busy || (!tavily.trim() && !jev.trim())}
        >
          {busy ? "Saving…" : "Save connections"}
        </button>
      </form>
    </Modal>
  );
}
