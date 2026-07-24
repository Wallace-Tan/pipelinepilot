import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";

type IncidentSnapshot = {
  pipeline: string;
  status: string;
  policy: string;
  mode: "fixture";
};

const incident: IncidentSnapshot = {
  pipeline: "retail_orders_daily",
  status: "Created",
  policy: "Approval required before retry or recovery",
  mode: "fixture",
};

function App() {
  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Primary">
        <div className="brand">PipelinePilot</div>
        <span className="mode-pill">Fixture demo</span>
      </aside>

      <section className="workspace">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">Incident command</p>
            <h1>{incident.pipeline}</h1>
          </div>
          <div className="status-block">
            <span>Status</span>
            <strong>{incident.status}</strong>
          </div>
        </header>

        <section className="summary-grid" aria-label="Demo status">
          <article>
            <span>Runtime mode</span>
            <strong>{incident.mode}</strong>
          </article>
          <article>
            <span>Policy posture</span>
            <strong>{incident.policy}</strong>
          </article>
          <article>
            <span>Workflow scope</span>
            <strong>Schema drift foundation</strong>
          </article>
        </section>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
