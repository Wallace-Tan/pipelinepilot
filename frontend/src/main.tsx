import { useEffect, useMemo, useState } from "react";
import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";

type EvidenceStatus = "available" | "degraded";
type EvidenceFilter = "all" | "available" | "degraded";

type EvidenceViewModel = {
  id: string;
  source: string;
  sourceLabel: string;
  status: EvidenceStatus;
  summary: string;
  detail: string;
  timestamp: string;
  metadata: string;
  citation?: string;
};

type WorkflowStep = {
  id: string;
  label: string;
  description: string;
  state: "complete" | "active" | "pending";
  target: string;
};

type PolicyPosture = {
  decision: string;
  risk: string;
  reason: string;
  action: string;
};

type AuditEntry = {
  time: string;
  action: string;
  detail: string;
  actor: string;
  tone: "neutral" | "success" | "warning";
};

type ApiIncident = { id: string; pipeline_name: string; run_id: string; status: string; severity: string; detected_at: string; mode: string };
type ApiEvidence = { id: string; source: string; summary: string; evidence_type: string; collected_at: string; citations: { title: string; section: string }[] };
type ApiDetail = { incident: ApiIncident; evidence: ApiEvidence[]; recommendation: { cause: string; confidence_band: string; recommended_action: string; uncertainty: string } | null; audit: { created_at: string; action: string; outcome: string; actor_role: string }[] };
type ApiReport = { recommendation: { cause: string; confidence_band: string; evidence_ids: string[]; runbook_ids: string[]; recommended_action: string; uncertainty: string } | null; policy_decision: { decision: string; policy_version: string; risk: string } | null; execution: { status: string; external_reference: string | null } | null; validation: { status: string; checks: string[] } | null; feedback_count: number };
type ApiPolicyRule = { id: string; action: string; environment: string; minimum_role: string; risk: string; decision: string; required_approver_role: string | null; minimum_severity: string | null; max_retry_count: number | null; reasons: string[] };
type ApiPolicy = { schema_version: "policy.v1"; id: string; version: string; mode: string; immutable: boolean; rules: ApiPolicyRule[]; default_decision: string };
type ApiPolicyResponse = { policy: ApiPolicy };

const API_INCIDENT_ID = "inc-retail-orders-20260723";
const API_HEADERS = { "X-Actor-Id": "operator-demo", "X-Actor-Role": "operator", "Content-Type": "application/json" };
const API_ADMIN_HEADERS = { "X-Actor-Id": "admin-demo", "X-Actor-Role": "admin", "Content-Type": "application/json" };
type DemoStatus = { mode: string; fixture: string; database_ready: boolean; adapters: Record<string, string> };

async function fetchIncident(): Promise<ApiDetail> {
  const response = await fetch(`/v1/incidents/${API_INCIDENT_ID}`);
  if (!response.ok) throw new Error("Incident API is unavailable.");
  return response.json() as Promise<ApiDetail>;
}

function mapIncident(value: ApiIncident) {
  return { pipeline: value.pipeline_name, runId: value.run_id, status: value.status.replace(/\b\w/g, (letter) => letter.toUpperCase()), severity: value.severity.replace(/\b\w/g, (letter) => letter.toUpperCase()), detected: new Date(value.detected_at).toLocaleString(), mode: value.mode };
}

function mapEvidence(value: ApiEvidence): EvidenceViewModel {
  const sourceLabel = value.source.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  return { id: value.id, source: value.source, sourceLabel, status: value.source === "snowflake_metadata" ? "degraded" : "available", summary: value.summary, detail: value.summary, timestamp: new Date(value.collected_at).toLocaleTimeString(), metadata: value.evidence_type, citation: value.citations[0] ? `${value.citations[0].title} · ${value.citations[0].section}` : undefined };
}

type IconName =
  | "activity"
  | "archive"
  | "arrow"
  | "chevron"
  | "clipboard"
  | "database"
  | "file"
  | "grid"
  | "layers"
  | "lock"
  | "search"
  | "shield"
  | "spark"
  | "terminal";

const incident = {
  pipeline: "retail_orders_daily",
  runId: "airflow-run-20260723T040000Z",
  status: "Awaiting approval",
  severity: "High",
  detected: "23 Jul 2026, 09:18 MYT",
  mode: "Fixture",
};

const evidence: EvidenceViewModel[] = [
  {
    id: "monitoring",
    source: "monitoring",
    sourceLabel: "Monitoring",
    status: "available",
    summary: "Pipeline failed in transform_orders with no retry running.",
    detail: "Airflow fixture reports a failed retail_orders_daily run. The task stopped on its first attempt and has no active recovery operation.",
    timestamp: "09:19:15",
    metadata: "run status · try 1",
  },
  {
    id: "airflow-log",
    source: "airflow_log",
    sourceLabel: "Airflow log",
    status: "available",
    summary: "ColumnNotFound: order_channel during staging compilation.",
    detail: "Compilation failed for stg_orders because the downstream contract expects order_channel, but the selected source columns do not include it.",
    timestamp: "09:20:30",
    metadata: "parser signature · cited",
    citation: "runbook-schema-drift · Validate downstream model contracts",
  },
  {
    id: "dbt",
    source: "dbt",
    sourceLabel: "dbt health",
    status: "available",
    summary: "stg_orders failed and downstream freshness is stale.",
    detail: "The accepted-values check for order_channel failed. fct_orders and daily_store_revenue are marked stale while the source contract remains unresolved.",
    timestamp: "09:21:45",
    metadata: "model failure · freshness stale",
    citation: "runbook-schema-drift · Validate downstream model contracts",
  },
  {
    id: "snowflake",
    source: "snowflake_metadata",
    sourceLabel: "Snowflake metadata",
    status: "degraded",
    summary: "Source metadata confirms order_channel is new; live ownership is unavailable.",
    detail: "The fixture compares raw ORDERS columns with the staging projection. It confirms the new field but cannot verify live deployment ownership in fixture mode.",
    timestamp: "09:22:10",
    metadata: "read-only context · fixture",
    citation: "runbook-schema-drift · Compare source metadata with staging projections",
  },
];

const workflow: WorkflowStep[] = [
  { id: "detect", label: "Detect", description: "Failure received", state: "complete", target: "incident-overview" },
  { id: "investigate", label: "Investigate", description: "Evidence assembled", state: "complete", target: "evidence-workspace" },
  { id: "decide", label: "Decide", description: "Operator review", state: "active", target: "decision-panel" },
  { id: "recover", label: "Recover", description: "Approval required", state: "pending", target: "decision-panel" },
  { id: "validate", label: "Validate", description: "Not started", state: "pending", target: "audit-timeline" },
];

const policy: PolicyPosture = {
  decision: "Approval required",
  risk: "High",
  reason: "Schema changes can affect downstream financial reporting. A controlled rerun needs an Operator or Admin approval bound to this action.",
  action: "Update staging projection and rerun downstream order models",
};

const audit: AuditEntry[] = [
  { time: "09:22:14", action: "Investigation completed", detail: "4 evidence sources collected · 1 degraded", actor: "system", tone: "success" },
  { time: "09:21:45", action: "dbt context attached", detail: "stg_orders failed · freshness stale", actor: "dbt health", tone: "neutral" },
  { time: "09:20:30", action: "Parser signature matched", detail: "ColumnNotFound: order_channel", actor: "Airflow log", tone: "neutral" },
  { time: "09:18:00", action: "Incident created", detail: "retail_orders_daily run failed", actor: "monitoring", tone: "warning" },
];

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  const paths: Record<IconName, React.ReactNode> = {
    activity: <><path d="M3 12h4l2-7 4 14 2-7h6" /><path d="M3 5h.01M21 19h.01" /></>,
    archive: <><path d="M4 7h16v13H4z" /><path d="M3 4h18v3H3zM9 12h6" /></>,
    arrow: <><path d="M5 12h13" /><path d="m13 6 6 6-6 6" /></>,
    chevron: <path d="m6 9 6 6 6-6" />,
    clipboard: <><rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 4.5V3h6v1.5M8 10h8M8 14h6" /></>,
    database: <><ellipse cx="12" cy="5" rx="7" ry="3" /><path d="M5 5v7c0 1.7 3.1 3 7 3s7-1.3 7-3V5M5 12v7c0 1.7 3.1 3 7 3s7-1.3 7-3v-7" /></>,
    file: <><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v5h5M9 13h6M9 17h4" /></>,
    grid: <><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><rect x="14" y="14" width="6" height="6" rx="1" /></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 12 9 5 9-5M3 16l9 5 9-5" /></>,
    lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3" /></>,
    search: <><circle cx="11" cy="11" r="6" /><path d="m16 16 4 4" /></>,
    shield: <><path d="M12 3 19 6v5c0 4.4-2.9 8-7 10-4.1-2-7-5.6-7-10V6l7-3Z" /><path d="m9 12 2 2 4-4" /></>,
    spark: <><path d="m12 3 1.5 6.5L20 11l-6.5 1.5L12 19l-1.5-6.5L4 11l6.5-1.5L12 3Z" /><path d="m19 3 .4 1.6L21 5l-1.6.4L19 7l-.4-1.6L17 5l1.6-.4L19 3Z" /></>,
    terminal: <><path d="m5 7 5 5-5 5M13 17h6" /></>,
  };

  return <svg aria-hidden="true" className="icon" fill="none" height={size} viewBox="0 0 24 24" width={size} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7">{paths[name]}</svg>;
}

function BrandMark() {
  return (
    <svg aria-hidden="true" className="brand-mark-svg" fill="none" viewBox="0 0 40 32">
      <path className="brand-circuit" d="M5 7h7a5 5 0 0 1 5 5v3m-12 10h8a5 5 0 0 0 5-5v-3h8" />
      <circle className="brand-node" cx="5" cy="7" r="2.5" />
      <circle className="brand-node" cx="5" cy="25" r="2.5" />
      <circle className="brand-node" cx="17" cy="5" r="2.5" />
      <circle className="brand-node" cx="31" cy="24" r="2.5" />
      <path className="brand-plane" d="m9 16 24-10-10 20-4-8-10-2Z" />
      <path className="brand-plane-fold" d="m9 16 14 2-4 8" />
    </svg>
  );
}

function formatPolicyValue(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function PolicyView({ policy, loading, error, onRetry }: { policy: ApiPolicy | null; loading: boolean; error: string | null; onRetry: () => void }) {
  return (
    <div className="policy-view animate-in">
      <section className="policy-heading">
        <div>
          <span className="eyebrow">Governance configuration</span>
          <h1>Active policy</h1>
          <p className="subhead">The server-side rules that determine whether incident actions are allowed, gated, or denied.</p>
        </div>
        <div className="policy-readonly-badge"><Icon name="lock" size={15} /><span>Read-only</span></div>
      </section>

      {loading && <section className="panel policy-state" role="status"><span className="status-dot is-emerald" />Loading the active policy…</section>}
      {error && <section className="panel policy-state is-error" role="alert"><span className="signal-dot" /><span>{error}</span><button className="text-action" onClick={onRetry} type="button">Retry</button></section>}
      {!loading && !error && policy && <>
        <section className="policy-summary-grid" aria-label="Policy summary">
          <div className="panel policy-summary-card"><span className="eyebrow">Policy version</span><strong>{policy.version}</strong><small>{policy.id}</small></div>
          <div className="panel policy-summary-card"><span className="eyebrow">Environment</span><strong>{formatPolicyValue(policy.mode)}</strong><small>Runtime mode</small></div>
          <div className="panel policy-summary-card"><span className="eyebrow">Protection</span><strong>{policy.immutable ? "Immutable" : "Mutable"}</strong><small>Policy changes require a new version</small></div>
          <div className="panel policy-summary-card"><span className="eyebrow">Default decision</span><strong>{formatPolicyValue(policy.default_decision)}</strong><small>Unknown actions fail closed</small></div>
        </section>

        <section className="panel policy-rules-panel">
          <div className="section-heading"><div><span className="eyebrow">Decision rules</span><h2>{policy.rules.length} active rules</h2></div><span className="count-badge">{policy.schema_version}</span></div>
          <div className="policy-rules" role="list">
            {policy.rules.map((rule) => <article className="policy-rule" key={rule.id} role="listitem">
              <div className="policy-rule-header"><div><span className="eyebrow">{rule.id}</span><h3>{formatPolicyValue(rule.action)}</h3></div><span className={`policy-decision-badge is-${rule.decision}`}>{formatPolicyValue(rule.decision)}</span></div>
              <div className="policy-rule-meta"><span><b>Environment</b>{formatPolicyValue(rule.environment)}</span><span><b>Minimum role</b>{formatPolicyValue(rule.minimum_role)}</span><span><b>Risk</b>{formatPolicyValue(rule.risk)}</span><span><b>Approver</b>{rule.required_approver_role ? formatPolicyValue(rule.required_approver_role) : "Not required"}</span></div>
              <div className="policy-rule-constraints"><span>Minimum severity: {rule.minimum_severity ? formatPolicyValue(rule.minimum_severity) : "None"}</span><span>Maximum retries: {rule.max_retry_count ?? "Unbounded"}</span></div>
              <ul className="policy-reasons">{rule.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
            </article>)}
          </div>
        </section>

        <div className="policy-footnote"><Icon name="shield" size={14} /><span>Policy is evaluated by the backend before approval or recovery. This view cannot change rules or authorize an action.</span></div>
      </>}
    </div>
  );
}

function App() {
  const [activeNav, setActiveNav] = useState("Overview");
  const [filter, setFilter] = useState<EvidenceFilter>("all");
  const [expandedEvidence, setExpandedEvidence] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [liveIncident, setLiveIncident] = useState(incident);
  const [liveEvidence, setLiveEvidence] = useState<EvidenceViewModel[]>(evidence);
  const [liveAudit, setLiveAudit] = useState<AuditEntry[]>(audit);
  const [livePolicy, setLivePolicy] = useState(policy);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);
  const [demoStatus, setDemoStatus] = useState<DemoStatus | null>(null);
  const [report, setReport] = useState<ApiReport | null>(null);
  const [feedbackText, setFeedbackText] = useState("");
  const [livePolicyDocument, setLivePolicyDocument] = useState<ApiPolicy | null>(null);
  const [policyError, setPolicyError] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    try {
      const [detail, statusResponse, reportResponse, policyResponse] = await Promise.all([fetchIncident(), fetch("/v1/demo/status"), fetch(`/v1/incidents/${API_INCIDENT_ID}/report`), fetch("/v1/policies/current")]);
      if (!statusResponse.ok) throw new Error("Demo readiness status is unavailable.");
      setDemoStatus(await statusResponse.json() as DemoStatus);
      const reportData = reportResponse.ok ? await reportResponse.json() as ApiReport : null;
      setReport(reportData);
      if (policyResponse.ok) {
        const policyData = await policyResponse.json() as ApiPolicyResponse;
        setLivePolicyDocument(policyData.policy);
        setPolicyError(null);
      } else {
        setLivePolicyDocument(null);
        setPolicyError(policyResponse.status === 503 ? "The active policy is unavailable." : "The policy API request was rejected.");
      }
      setLiveIncident(mapIncident(detail.incident));
      setLiveEvidence(detail.evidence.map(mapEvidence));
      setLiveAudit(detail.audit.map((entry) => ({ time: new Date(entry.created_at).toLocaleTimeString(), action: entry.action, detail: entry.outcome, actor: entry.actor_role, tone: entry.outcome.includes("failed") ? "warning" : "neutral" })));
      if (detail.recommendation) setLivePolicy({ decision: "Approval required", risk: "High", reason: detail.recommendation.uncertainty, action: detail.recommendation.recommended_action });
      if (reportData?.policy_decision) setLivePolicy({ decision: reportData.policy_decision.decision.replace("_", " "), risk: reportData.policy_decision.risk, reason: detail.recommendation?.uncertainty ?? "Policy decision loaded from the server.", action: detail.recommendation?.recommended_action ?? "" });
      setApiError(null);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Unable to load incident data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void refresh(); }, []);

  const resetDemo = async () => {
    setLoading(true);
    try {
      const response = await fetch("/v1/demo/reset", { method: "POST", headers: API_ADMIN_HEADERS });
      if (!response.ok) throw new Error("Admin fixture reset was rejected.");
      await refresh();
      setNotice("Fixture reset completed. The seeded incident is ready for a new walkthrough.");
    } catch (error) {
      setLoading(false);
      setNotice(error instanceof Error ? error.message : "Fixture reset failed.");
    }
  };

  const runAction = async (path: string, body?: object, key = "ui-schema-drift-recovery") => {
    try {
      const response = await fetch(`/v1/incidents/${API_INCIDENT_ID}/${path}`, { method: "POST", headers: { ...API_HEADERS, "Idempotency-Key": key }, body: body ? JSON.stringify(body) : undefined });
      if (!response.ok) throw new Error("The server rejected this governed action.");
      await refresh();
      setNotice("Fixture-mode action completed and the incident view was refreshed.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Action failed.");
    }
  };

  const submitFeedback = async () => {
    if (!feedbackText.trim()) return;
    await runAction("feedback", { correction: feedbackText.trim(), outcome: "operator-noted" }, `ui-feedback-${Date.now()}`);
    setFeedbackText("");
  };

  const filteredEvidence = useMemo(
    () => liveEvidence.filter((item) => filter === "all" || item.status === filter),
    [filter, liveEvidence],
  );

  const focusWorkflow = (step: WorkflowStep) => {
    document.getElementById(step.target)?.scrollIntoView({ behavior: "smooth", block: "start" });
    setNotice(`${step.label}: ${step.description}`);
  };

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand-lockup">
          <div className="brand-mark"><BrandMark /></div>
          <div>
            <strong>PipelinePilot</strong>
            <span>Incident command</span>
          </div>
        </div>
        <div className="rail-label">Workspace</div>
        <nav className="main-nav">
          {[{ label: "Overview", icon: "grid" as IconName }, { label: "Incidents", icon: "activity" as IconName }, { label: "Runbooks", icon: "file" as IconName }, { label: "Policy", icon: "shield" as IconName }, { label: "Audit log", icon: "clipboard" as IconName }].map((item) => (
            <button className={`nav-item ${activeNav === item.label ? "is-active" : ""}`} key={item.label} onClick={() => { setActiveNav(item.label); if (item.label !== "Policy") setNotice(`${item.label} view is ready for the next API milestone.`); }} type="button">
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.label === "Incidents" && <span className="nav-count">1</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="rail-label">Environment</div>
          <button className="environment-card" onClick={() => setNotice(demoStatus?.adapters.decision === "coco" ? "CoCo is enabled for read-only context and decision support. Recovery remains governed by the backend policy and approval workflow." : "Fixture mode uses sanitized evidence and does not execute recovery actions.")} type="button">
            <span className="signal-dot is-emerald" />
            <span><strong>{demoStatus?.adapters.decision === "coco" ? "CoCo bridge" : "Fixture mode"}</strong><small>{demoStatus?.adapters.decision === "coco" ? "Read-only external context" : "Safe demo environment"}</small></span>
            <Icon name="chevron" size={15} />
          </button>
          <div className="user-chip"><span className="avatar">OP</span><span><strong>Operator</strong><small>Demo identity</small></span><span className="status-dot" /></div>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><Icon name="chevron" size={13} /><strong>{activeNav}</strong></div>
          <div className="topbar-actions">
            <button className="topbar-button" onClick={() => setNotice("Global search will connect to incident and evidence APIs in Milestone 6.")} title="Search workspace" type="button"><Icon name="search" size={16} /><span>Search</span></button>
            <button className="topbar-button" onClick={() => void resetDemo()} title="Admin-only fixture reset using the explicit Admin demo identity" type="button">Reset fixture · Admin demo</button>
            <button className="icon-button" onClick={() => setNotice("All fixture adapters are responding. Snowflake metadata is marked degraded by design.")} title="System health" type="button"><span className="status-dot is-emerald" /><Icon name="activity" size={16} /></button>
          </div>
        </header>

        <div className="content-wrap">
          {loading && <div className="api-banner is-loading" role="status"><span className="status-dot is-emerald" />Loading persisted incident state…</div>}
          {apiError && <div className="api-banner is-error" role="alert"><span className="signal-dot" />{apiError} <button className="text-action" onClick={() => void refresh()} type="button">Retry</button></div>}
          {demoStatus && <div className="api-banner is-ready" role="status"><span className="status-dot is-emerald" />{demoStatus.fixture} · {demoStatus.mode} · database ready · {demoStatus.adapters.decision === "coco" ? "CoCo-backed read-only context and decision" : "Fixture context and decision"} · {demoStatus.adapters.snowflake_metadata === "coco" ? "Snowflake metadata via CoCo" : "Snowflake metadata degraded by design"}</div>}
          {activeNav === "Policy" ? <PolicyView policy={livePolicyDocument} loading={loading} error={policyError} onRetry={() => void refresh()} /> : <>
          <section className="incident-header animate-in" id="incident-overview">
            <div>
              <div className="eyebrow-row"><span className="eyebrow">Active incident</span><span className="badge badge-warning"><span className="signal-dot" />{liveIncident.severity} severity</span></div>
              <h1>{liveIncident.pipeline}</h1>
              <p className="subhead">Daily retail orders load failed after an upstream schema change.</p>
              <div className="incident-meta"><span><Icon name="terminal" size={14} />{liveIncident.runId}</span><span><Icon name="database" size={14} />Detected {liveIncident.detected}</span></div>
            </div>
            <div className="incident-state">
              <span className="eyebrow">Current state</span>
              <div className="state-value"><span className="state-pulse" />{liveIncident.status}</div>
              <button className="text-action" onClick={() => setNotice("The action is intentionally gated by the deterministic policy engine.")} type="button">Why is this blocked? <Icon name="arrow" size={14} /></button>
            </div>
          </section>

          <section className="workflow-panel panel animate-in delay-1" aria-label="Incident workflow">
            <div className="section-heading"><div><span className="eyebrow">Workflow</span><h2>From signal to resolution</h2></div><span className="muted-label">5 stages · 1 active</span></div>
            <div className="workflow-steps">
              {workflow.map((step, index) => <React.Fragment key={step.id}>
                <button className={`workflow-step is-${step.state}`} onClick={() => focusWorkflow(step)} type="button">
                  <span className="step-marker">{step.state === "complete" ? "✓" : index + 1}</span>
                  <span className="step-copy"><strong>{step.label}</strong><small>{step.description}</small></span>
                </button>
                {index < workflow.length - 1 && <span className={`step-line ${step.state === "complete" ? "is-complete" : ""}`} />}
              </React.Fragment>)}
            </div>
          </section>

          <div className="content-grid">
            <section className="panel evidence-panel animate-in delay-2" id="evidence-workspace">
              <div className="section-heading section-heading-wrap"><div><span className="eyebrow">Investigation context</span><h2>Evidence collected</h2></div><span className="count-badge">{filteredEvidence.length} / {liveEvidence.length}</span></div>
              <div className="filter-row" aria-label="Evidence filters">
                {(["all", "available", "degraded"] as EvidenceFilter[]).map((option) => <button className={`filter-button ${filter === option ? "is-active" : ""}`} key={option} onClick={() => setFilter(option)} type="button">{option === "all" ? "All sources" : option === "available" ? "Available" : "Degraded"}</button>)}
                <span className="filter-note"><Icon name="shield" size={13} />Redacted before persistence</span>
              </div>
              <div className="evidence-list" aria-live="polite">
                {filteredEvidence.map((item) => <article className={`evidence-card ${expandedEvidence === item.id ? "is-expanded" : ""}`} key={item.id}>
                  <button className="evidence-summary" aria-expanded={expandedEvidence === item.id} onClick={() => setExpandedEvidence(expandedEvidence === item.id ? null : item.id)} type="button">
                    <span className={`source-icon source-${item.source}`}><Icon name={item.source === "monitoring" ? "activity" : item.source === "snowflake_metadata" ? "database" : item.source === "dbt" ? "layers" : "terminal"} size={17} /></span>
                    <span className="evidence-main"><span className="evidence-title-row"><strong>{item.sourceLabel}</strong><span className={`status-label is-${item.status}`}>{item.status}</span></span><span className="evidence-summary-text">{item.summary}</span><span className="evidence-meta">{item.timestamp} · {item.metadata}</span></span>
                    <span className="expand-icon"><Icon name="chevron" size={16} /></span>
                  </button>
                  <div className="evidence-detail"><p>{item.detail}</p>{item.citation && <span className="citation"><Icon name="file" size={13} />{item.citation}</span>}</div>
                </article>)}
              </div>
            </section>

            <aside className="side-stack">
              <section className="panel decision-panel animate-in delay-3" id="decision-panel">
                <div className="section-heading"><div><span className="eyebrow">Governance gate</span><h2>Policy posture</h2></div><Icon name="lock" size={18} /></div>
                <div className="policy-decision"><div><span className="eyebrow">Decision</span><strong>{livePolicy.decision}</strong></div><span className="badge badge-warning">{livePolicy.risk} risk</span></div>
                <div className="policy-action"><span className="eyebrow">Proposed action</span><p>{livePolicy.action}</p></div>
                <p className="policy-reason">{livePolicy.reason}</p>
                <button className="secondary-button" onClick={() => setNotice(livePolicy.reason)} type="button"><Icon name="shield" size={15} />Explain policy gate</button>
                <div className="fixture-actions">
                  {loading && <span className="muted-label">Loading live incident state…</span>}
                  {apiError && <button className="secondary-button" onClick={() => void refresh()} type="button">Retry API connection</button>}
                  {!loading && liveIncident.status === "Created" && <button className="secondary-button" onClick={() => void runAction("investigate")} type="button">{demoStatus?.adapters.decision === "coco" ? "Investigate with CoCo" : "Investigate fixture incident"}</button>}
                  {!loading && liveIncident.status === "Investigated" && <><button className="secondary-button" onClick={() => void runAction("approvals", { action: "schema_drift_recovery", approved: true, reason: "Approve fixture recovery." })} type="button">Approve fixture recovery</button><button className="secondary-button" onClick={() => void runAction("approvals", { action: "schema_drift_recovery", approved: false, reason: "Reject fixture recovery." })} type="button">Reject recovery</button></>}
                  {!loading && liveIncident.status === "Approved" && <button className="secondary-button" onClick={() => void runAction("executions", { action: "schema_drift_recovery" })} type="button">Execute fixture recovery</button>}
                  {!loading && liveIncident.status === "Recovered" && <button className="secondary-button" onClick={() => void runAction("validate")} type="button">Validate recovery</button>}
                </div>
                <div className="preview-note"><span className="signal-dot is-amber" /><span>{demoStatus?.adapters.decision === "coco" ? "CoCo context is read-only; recovery remains fixture-only and is governed by the server policy." : "Fixture actions are governed by the server policy and remain visibly non-production."}</span></div>
              </section>
              <section className="panel recommendation-panel animate-in delay-4">
                <div className="section-heading"><div><span className="eyebrow">Decision support</span><h2>Root cause signal</h2></div><span className="confidence">High</span></div>
                <p className="root-cause">Upstream raw orders added <code>order_channel</code>, but the staging projection was not updated before the daily run.</p>
                <div className="signal-row"><span><Icon name="spark" size={14} />4 supporting sources</span><span><Icon name="file" size={14} />1 cited runbook</span></div>
              </section>
            </aside>
          </div>

          <section className="panel audit-panel animate-in delay-4" id="audit-timeline">
            <div className="section-heading"><div><span className="eyebrow">Traceability</span><h2>Audit timeline</h2></div><button className="text-action" onClick={() => setNotice("Full audit filtering will be available with the Milestone 6 API.")} type="button">View full log <Icon name="arrow" size={14} /></button></div>
            <div className="audit-list">{liveAudit.map((entry) => <div className="audit-entry" key={`${entry.time}-${entry.action}`}><span className={`audit-marker is-${entry.tone}`} /><time>{entry.time}</time><div><strong>{entry.action}</strong><span>{entry.detail}</span></div><small>{entry.actor}</small></div>)}</div>
          </section>

          <section className="panel report-panel animate-in delay-4" id="incident-report">
            <div className="section-heading"><div><span className="eyebrow">Evidence-linked RCA</span><h2>Incident report</h2></div><span className="count-badge">{report?.feedback_count ?? 0} feedback</span></div>
            {report?.recommendation ? <div className="report-content"><p className="root-cause">{report.recommendation.cause}</p><div className="signal-row"><span>{report.recommendation.confidence_band} confidence</span><span>{report.recommendation.evidence_ids.length} evidence IDs</span><span>{report.recommendation.runbook_ids.length} runbook citation</span></div><p className="policy-reason">Uncertainty: {report.recommendation.uncertainty}</p>{report.validation && <p className="policy-reason">Validation: {report.validation.status} · {report.validation.checks.join(" · ")}</p>}{report.execution?.external_reference && <p className="policy-reason">External reference: {report.execution.external_reference}</p>}</div> : <p className="muted-label">Report becomes available after investigation.</p>}
            <div className="feedback-form"><input aria-label="Operator feedback" onChange={(event) => setFeedbackText(event.target.value)} placeholder="Add an operator correction" value={feedbackText} /><button className="secondary-button" disabled={!feedbackText.trim()} onClick={() => void submitFeedback()} type="button">Record feedback</button></div>
          </section>

          <footer className="workspace-footer"><span><span className="signal-dot is-emerald" />{demoStatus?.adapters.decision === "coco" ? "CoCo bridge · read-only external context" : "Fixture mode · sanitized evidence only"}</span><span>PipelinePilot v0.3 · governed by policy</span></footer>
          </>}
        </div>
        {notice && <button className="notice-toast" onClick={() => setNotice(null)} type="button"><Icon name="spark" size={15} /><span>{notice}</span><span className="toast-dismiss">Dismiss</span></button>}
      </main>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
