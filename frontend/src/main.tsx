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

type RunbookEntry = {
  id: string;
  title: string;
  purpose: string;
  status: "matched" | "available";
  owner: string;
  lastVerified: string;
  steps: string[];
};

type ApiIncident = { id: string; pipeline_name: string; run_id: string; status: string; severity: string; summary: string; detected_at: string; mode: string };
type ApiEvidence = { id: string; source: string; summary: string; evidence_type: string; mode: string; collected_at: string; citations: { title: string; section: string }[] };
type ApiRecommendation = { schema_version: string; cause: string; confidence_band: string; evidence_ids: string[]; runbook_ids: string[]; recommended_action: string; impact: string; alternatives: { action: string; reason: string }[]; uncertainty: string };
type ApiPolicyDecision = { id: string; action: string; decision: string; risk: string; policy_version: string; required_approver_role: string | null; reasons: string[] };
type ApiApproval = { id: string; created_at: string; decision: string; reason: string; actor_role: string; execution_id: string; policy_version: string };
type ApiExecution = { id: string; action: string; status: string; policy_decision_id: string; approval_id: string | null; external_reference: string | null; created_at: string; updated_at: string };
type ApiDetail = { incident: ApiIncident; evidence: ApiEvidence[]; recommendation: ApiRecommendation | null; policy_decision: ApiPolicyDecision | null; executions: ApiExecution[]; approvals: ApiApproval[]; audit: { created_at: string; action: string; outcome: string; actor_role: string }[] };
type ApiAuditEvent = { id: string; incident_id: string | null; execution_id: string | null; actor_role: string; action: string; outcome: string; created_at: string };
type ApiAgentDetail = { incident: ApiIncident; evidence: ApiEvidence[]; recommendation: ApiRecommendation | null; policy_decision: ApiPolicyDecision | null; adapter_status: Record<string, DemoAdapterStatus>; audit: ApiAuditEvent[] };
type ApiExecutionDetail = { incident: ApiIncident; execution: ApiExecution; approval: ApiApproval | null; policy_decision: ApiPolicyDecision | null; validation: { status: string; checks: string[]; failure_reason?: string | null } | null; audit: ApiAuditEvent[] };
type ApiReport = { recommendation: ApiRecommendation | null; policy_decision: { decision: string; policy_version: string; risk: string } | null; execution: { status: string; external_reference: string | null } | null; validation: { status: string; checks: string[] } | null; feedback_count: number };
type ApiPolicyRule = { id: string; action: string; environment: string; minimum_role: string; risk: string; decision: string; required_approver_role: string | null; minimum_severity: string | null; max_retry_count: number | null; reasons: string[] };
type ApiPolicy = { schema_version: "policy.v1"; id: string; version: string; mode: string; immutable: boolean; rules: ApiPolicyRule[]; default_decision: string };
type ApiPolicyResponse = { policy: ApiPolicy };

const API_INCIDENT_ID = "inc-retail-orders-20260723";
const API_HEADERS = { "X-Actor-Id": "operator-demo", "X-Actor-Role": "operator", "Content-Type": "application/json" };
const API_ADMIN_HEADERS = { "X-Actor-Id": "admin-demo", "X-Actor-Role": "admin", "Content-Type": "application/json" };
type DemoAdapterStatus = { mode: string; status: string; source: string; reason?: string | null };
type DemoStatus = { mode: string; fixture: string; database_ready: boolean; adapters: Record<string, string>; adapter_status: Record<string, DemoAdapterStatus> };

async function fetchIncident(): Promise<ApiDetail> {
  const response = await fetch(`/v1/incidents/${API_INCIDENT_ID}`);
  if (!response.ok) throw new Error("Incident API is unavailable.");
  return response.json() as Promise<ApiDetail>;
}

async function fetchIncidents(): Promise<{ items: ApiIncident[]; total: number }> {
  const response = await fetch("/v1/incidents?limit=100");
  if (!response.ok) throw new Error("Incident queue is unavailable.");
  return response.json() as Promise<{ items: ApiIncident[]; total: number }>;
}

async function fetchAgentDetail(): Promise<ApiAgentDetail> {
  const response = await fetch(`/v1/incidents/${API_INCIDENT_ID}/agent`);
  if (!response.ok) throw new Error("Agent detail is unavailable.");
  return response.json() as Promise<ApiAgentDetail>;
}

async function fetchExecutionDetail(executionId: string): Promise<ApiExecutionDetail> {
  const response = await fetch(`/v1/incidents/${API_INCIDENT_ID}/executions/${executionId}`);
  if (!response.ok) throw new Error("Execution detail is unavailable.");
  return response.json() as Promise<ApiExecutionDetail>;
}

function mapIncident(value: ApiIncident) {
  return { pipeline: value.pipeline_name, runId: value.run_id, status: value.status.replace(/\b\w/g, (letter) => letter.toUpperCase()), severity: value.severity.replace(/\b\w/g, (letter) => letter.toUpperCase()), detected: new Date(value.detected_at).toLocaleString(), mode: value.mode };
}

function isCompletedStatus(status: string) {
  return ["Recovered", "Validated", "Reported"].includes(status);
}

function statusLabel(status: string) {
  return status === "Awaiting approval" ? "Awaiting approval" : status;
}

function mapEvidence(value: ApiEvidence): EvidenceViewModel {
  const sourceLabel = value.source.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  return { id: value.id, source: value.source, sourceLabel, status: value.mode === "live" || value.source !== "snowflake_metadata" ? "available" : "degraded", summary: value.summary, detail: value.summary, timestamp: new Date(value.collected_at).toLocaleTimeString(), metadata: `${value.evidence_type} · ${value.mode}`, citation: value.citations[0] ? `${value.citations[0].title} · ${value.citations[0].section}` : undefined };
}

function mapAuditEvent(value: ApiAuditEvent): AuditEntry {
  const warning = value.outcome.includes("failed") || value.outcome.includes("blocked") || value.outcome.includes("denied");
  return {
    time: new Date(value.created_at).toLocaleTimeString(),
    action: value.action,
    detail: `${value.outcome}${value.incident_id ? ` · ${value.incident_id}` : ""}${value.execution_id ? ` · ${value.execution_id}` : ""}`,
    actor: value.actor_role,
    tone: warning ? "warning" : value.outcome.includes("validated") || value.outcome.includes("completed") ? "success" : "neutral",
  };
}

function formatDetailStatus(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function AgentExecutionDetail({ detail, demoStatus }: { detail: ApiDetail | null; demoStatus: DemoStatus | null }) {
  const adapterStatus = demoStatus?.adapter_status ?? {};
  const latestExecution = detail?.executions.at(-1) ?? null;
  const latestApproval = detail?.approvals.at(-1) ?? null;
  const agents = [
    { label: "Context agents", detail: "Monitoring · Airflow · dbt · Snowflake", status: Object.values(adapterStatus).some((item) => item.mode === "live") ? "Live or mixed" : "Fixture evidence" },
    { label: "Decision agent", detail: "Typed recommendation + citations", status: adapterStatus.decision?.status === "available" ? "Validated" : adapterStatus.decision ? formatDetailStatus(adapterStatus.decision.status) : "Awaiting investigation" },
    { label: "Policy engine", detail: detail?.policy_decision?.policy_version ?? "No decision persisted", status: detail?.policy_decision ? formatDetailStatus(detail.policy_decision.decision) : "Pending" },
  ];

  return (
    <section className="panel agent-detail-panel animate-in delay-2" aria-label="Agent and execution detail">
      <div className="section-heading"><div><span className="eyebrow">Agent trace</span><h2>Decision and execution detail</h2></div><span className="count-badge">Typed API state</span></div>
      <div className="agent-detail-grid">
        {agents.map((agent) => <article className="agent-detail-card" key={agent.label}><span className="eyebrow">{agent.label}</span><strong>{agent.status}</strong><small>{agent.detail}</small></article>)}
      </div>
      <div className="execution-detail-grid">
        <article className="execution-detail-card">
          <div className="eyebrow-row"><span className="eyebrow">Approval record</span><span className={`status-label is-${latestApproval?.decision === "approved" ? "available" : "degraded"}`}>{latestApproval ? formatDetailStatus(latestApproval.decision) : "Not recorded"}</span></div>
          {latestApproval ? <><strong>{latestApproval.actor_role} · {latestApproval.reason}</strong><small>{latestApproval.id} · policy {latestApproval.policy_version}</small></> : <p>No approval exists. Execution must remain blocked until an Operator approves the proposal.</p>}
        </article>
        <article className="execution-detail-card">
          <div className="eyebrow-row"><span className="eyebrow">Recovery execution</span><span className={`status-label is-${latestExecution?.status === "succeeded" ? "available" : "degraded"}`}>{latestExecution ? formatDetailStatus(latestExecution.status) : "Not created"}</span></div>
          {latestExecution ? <><strong>{latestExecution.action}</strong><small>{latestExecution.id} · {latestExecution.external_reference ?? "No external reference"}</small></> : <p>Recovery writes are fixture-only and none has been created for this incident.</p>}
        </article>
      </div>
      <div className="detail-boundary-note"><Icon name="shield" size={14} /><span>Agent output is advisory. The persisted policy decision, approval identity, and execution reference are the accountable recovery boundary.</span></div>
    </section>
  );
}

function AgentDetailView({ resource, loading, error, onRetry }: { resource: ApiAgentDetail | null; loading: boolean; error: string | null; onRetry: () => void }) {
  return <div className="detail-view animate-in">
    <section className="page-heading"><div><span className="eyebrow">First-class resource</span><h1>Agent detail</h1><p className="subhead">The evidence and recommendation boundary exposed as a typed, read-only resource.</p></div><span className="page-readiness"><span className="status-dot is-emerald" />Viewer-readable</span></section>
    {loading && <div className="panel detail-state" role="status">Loading agent resource…</div>}
    {error && <div className="panel detail-state is-error" role="alert">{error}<button className="text-action" onClick={onRetry} type="button">Retry</button></div>}
    {resource && <>
      <section className="metric-grid" aria-label="Agent resource summary">
        <div className="panel metric-card"><span className="eyebrow">Incident</span><strong>{resource.incident.pipeline_name}</strong><small>{formatDetailStatus(resource.incident.status)}</small></div>
        <div className="panel metric-card"><span className="eyebrow">Evidence</span><strong>{resource.evidence.length}</strong><small>typed sources persisted</small></div>
        <div className="panel metric-card"><span className="eyebrow">Decision</span><strong>{resource.recommendation ? "Validated" : "Pending"}</strong><small>{resource.recommendation?.confidence_band ?? "No recommendation"}</small></div>
        <div className="panel metric-card"><span className="eyebrow">Policy</span><strong>{resource.policy_decision ? formatDetailStatus(resource.policy_decision.decision) : "Pending"}</strong><small>{resource.policy_decision?.policy_version ?? "No policy result"}</small></div>
      </section>
      <section className="panel detail-resource-panel"><div className="section-heading"><div><span className="eyebrow">Context adapters</span><h2>Evidence provenance</h2></div><span className="count-badge">{Object.keys(resource.adapter_status).length} adapters</span></div><div className="resource-list">{Object.entries(resource.adapter_status).map(([name, status]) => <div className="resource-row" key={name}><strong>{formatDetailStatus(name)}</strong><span>{formatDetailStatus(status.status)}</span><small>{status.mode} · {status.source}{status.reason ? ` · ${status.reason}` : ""}</small></div>)}</div></section>
      <section className="panel detail-resource-panel"><div className="section-heading"><div><span className="eyebrow">Recommendation contract</span><h2>{resource.recommendation?.cause ?? "No recommendation yet"}</h2></div><span className="count-badge">{resource.recommendation?.schema_version ?? "pending"}</span></div>{resource.recommendation ? <div className="report-content"><p className="policy-reason">Impact: {resource.recommendation.impact}</p><p className="policy-reason">Alternative: {resource.recommendation.alternatives[0]?.action} — {resource.recommendation.alternatives[0]?.reason}</p><p className="policy-reason">Citations: {resource.recommendation.evidence_ids.join(" · ")} · {resource.recommendation.runbook_ids.join(" · ")}</p></div> : <p className="empty-state">Investigate the incident to create a typed recommendation.</p>}</section>
    </>}
  </div>;
}

function ExecutionDetailView({ resource, loading, error, onRetry }: { resource: ApiExecutionDetail | null; loading: boolean; error: string | null; onRetry: () => void }) {
  return <div className="detail-view animate-in">
    <section className="page-heading"><div><span className="eyebrow">First-class resource</span><h1>Execution detail</h1><p className="subhead">The policy, approval, fixture reference, and validation evidence for one recovery attempt.</p></div><span className="page-readiness"><span className="status-dot is-emerald" />Governed boundary</span></section>
    {loading && <div className="panel detail-state" role="status">Loading execution resource…</div>}
    {error && <div className="panel detail-state is-error" role="alert">{error}<button className="text-action" onClick={onRetry} type="button">Retry</button></div>}
    {resource && <>
      <section className="metric-grid" aria-label="Execution resource summary">
        <div className="panel metric-card"><span className="eyebrow">Status</span><strong>{formatDetailStatus(resource.execution.status)}</strong><small>{resource.execution.id}</small></div>
        <div className="panel metric-card"><span className="eyebrow">Policy</span><strong>{formatDetailStatus(resource.policy_decision?.decision ?? "unknown")}</strong><small>{resource.policy_decision?.policy_version ?? "not available"}</small></div>
        <div className="panel metric-card"><span className="eyebrow">Approval</span><strong>{resource.approval ? formatDetailStatus(resource.approval.decision) : "Missing"}</strong><small>{resource.approval?.actor_role ?? "No accountable actor"}</small></div>
        <div className="panel metric-card"><span className="eyebrow">Validation</span><strong>{resource.validation ? formatDetailStatus(resource.validation.status) : "Pending"}</strong><small>{resource.validation?.checks.length ?? 0} checks</small></div>
      </section>
      <section className="panel detail-resource-panel"><div className="section-heading"><div><span className="eyebrow">Execution record</span><h2>{resource.execution.action}</h2></div><span className="count-badge">fixture-only</span></div><div className="resource-list"><div className="resource-row"><strong>External reference</strong><span>{resource.execution.external_reference ?? "None"}</span><small>Recovery writes never cross the fixture boundary.</small></div><div className="resource-row"><strong>Approval justification</strong><span>{resource.approval?.reason ?? "No approval recorded"}</span><small>{resource.approval ? `${resource.approval.actor_role} · ${resource.approval.created_at}` : "Execution must remain blocked."}</small></div><div className="resource-row"><strong>Validation checks</strong><span>{resource.validation?.checks.join(" · ") ?? "Not run"}</span><small>{resource.validation?.failure_reason ?? "Audit-backed execution state."}</small></div></div></section>
      <section className="panel detail-resource-panel"><div className="section-heading"><div><span className="eyebrow">Execution audit</span><h2>Append-only events</h2></div><span className="count-badge">{resource.audit.length}</span></div><div className="audit-list">{resource.audit.map((event) => <div className="audit-entry" key={event.id}><span className="audit-marker is-success" /><time>{new Date(event.created_at).toLocaleTimeString()}</time><div><strong>{event.action}</strong><span>{event.outcome}</span></div><small>{event.actor_role}</small></div>)}</div></section>
    </>}
  </div>;
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

type IncidentViewModel = { pipeline: string; runId: string; status: string; severity: string; detected: string; mode: string };

const incident: IncidentViewModel = {
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

const governanceChain = [
  { label: "CoCo gathers", detail: "sanitized evidence" },
  { label: "Decision proposes", detail: "cited action" },
  { label: "Policy decides", detail: "risk + permission" },
  { label: "Operator approves", detail: "accountability" },
  { label: "Recovery executes", detail: "fixture boundary" },
  { label: "Validation closes", detail: "audited result" },
];

const businessImpact = {
  summary: "Downstream order reporting is stale until the staging contract is corrected and the run is replayed.",
  affected: "stg_orders · fct_orders · daily_store_revenue",
  alternative: "Wait for the upstream contract update",
  alternativeReason: "Rejected for this incident because it leaves the current reporting window stale without a controlled replay.",
};

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

const runbooks: RunbookEntry[] = [
  {
    id: "runbook-schema-drift",
    title: "Schema Drift Response",
    purpose: "Confirm a source schema change, compare the staging projection, and replay only the affected downstream models.",
    status: "matched",
    owner: "Data Platform",
    lastVerified: "23 Jul 2026",
    steps: ["Collect monitoring, sanitized logs, dbt context, and read-only metadata", "Compare source metadata with staging projections", "Validate downstream model contracts and freshness", "Update the staging projection, rerun the affected chain, and validate"],
  },
  {
    id: "runbook-dbt-freshness",
    title: "dbt Freshness Failure",
    purpose: "Identify the stale source and affected downstream models before selecting the minimum recovery scope.",
    status: "available",
    owner: "Data Platform",
    lastVerified: "18 Jul 2026",
    steps: ["Identify the stale source and last successful load", "List affected downstream models", "Validate model dependencies and warehouse availability", "Run the minimum affected model selection after policy review"],
  },
  {
    id: "runbook-airflow-retry",
    title: "Airflow Retry and Run Failure",
    purpose: "Determine whether a failed task is transient, idempotent, and eligible for a governed retry.",
    status: "available",
    owner: "Data Platform",
    lastVerified: "18 Jul 2026",
    steps: ["Confirm DAG, task, run ID, retry count, and current state", "Match a sanitized failure signature", "Check transient and idempotent retry criteria", "Bind any retry or clear-task action to policy and idempotency"],
  },
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

function CommandCenter({
  incident,
  incidents,
  evidenceCount,
  report,
  integrationLabel,
  onOpenWorkbench,
  onNotice,
}: {
  incident: IncidentViewModel;
  incidents: ApiIncident[];
  evidenceCount: number;
  report: ApiReport | null;
  integrationLabel: string;
  onOpenWorkbench: () => void;
  onNotice: (message: string) => void;
}) {
  const [queueFilter, setQueueFilter] = useState<"all" | "open" | "resolved">("all");
  const validated = incident.status === "Validated";
  const recovered = isCompletedStatus(incident.status);
  const exceptionState = validated ? "Closed" : incident.status === "Created" ? "Needs investigation" : "Open";
  const queueItems = incidents.filter((item) => {
    if (queueFilter === "open") return !["validated", "reported", "failed", "denied"].includes(item.status);
    if (queueFilter === "resolved") return ["validated", "reported", "failed", "denied"].includes(item.status);
    return true;
  });
  const employees = [
    { name: "Signal Sentinel", role: "Monitoring employee", status: "Healthy", detail: "Watching retail_orders_daily", icon: "activity" as IconName, tone: "emerald" },
    { name: "Evidence Analyst", role: "Investigation employee", status: incident.status === "Created" ? "Ready" : "Evidence assembled", detail: `${evidenceCount} cited sources`, icon: "spark" as IconName, tone: "blue" },
    { name: "Policy Guardian", role: "Governance employee", status: validated ? "Closed" : "Approval required", detail: "High-risk recovery is gated", icon: "shield" as IconName, tone: "amber" },
    { name: "Recovery Operator", role: "Execution employee", status: recovered ? (validated ? "Validated" : "Recovered") : "Standby", detail: "Fixture boundary · no production writes", icon: "terminal" as IconName, tone: recovered ? "emerald" : "neutral" },
  ];

  return (
    <div className="command-center animate-in">
      <section className="command-heading">
        <div>
          <span className="eyebrow">Operations workspace</span>
          <h1>Command Center</h1>
          <p className="subhead">Governed AI employees keep the recovery decision observable, accountable, and reversible.</p>
        </div>
        <div className="command-mode"><span className="status-dot is-emerald" /><span><strong>{integrationLabel}</strong><small>Evidence context · recovery fixture-only</small></span></div>
      </section>

      <section className="metric-grid" aria-label="Operational metrics">
        <div className="panel metric-card"><span className="eyebrow">Active exceptions</span><strong>{validated ? 0 : 1}</strong><small>{validated ? "No unresolved exception" : "1 high-priority exception"}</small></div>
        <div className="panel metric-card"><span className="eyebrow">Freshness posture</span><strong className={validated ? "is-good" : "is-warning"}>{validated ? "Healthy" : "Stale"}</strong><small>daily_store_revenue</small></div>
        <div className="panel metric-card"><span className="eyebrow">Evidence coverage</span><strong>{evidenceCount}/4</strong><small>{integrationLabel} context sources</small></div>
        <div className="panel metric-card"><span className="eyebrow">Recovery outcome</span><strong className={validated ? "is-good" : "is-neutral"}>{validated ? "Validated" : report?.execution ? "Executed" : "Pending"}</strong><small>{validated ? "Audit closed" : "Operator decision required"}</small></div>
      </section>

      <section className="employee-panel panel">
        <div className="section-heading"><div><span className="eyebrow">AI employees</span><h2>Execution health</h2></div><span className="count-badge">4 workers · deterministic demo</span></div>
        <div className="employee-grid">
          {employees.map((employee) => <article className="employee-card" key={employee.name}>
            <div className={`employee-icon is-${employee.tone}`}><Icon name={employee.icon} size={16} /></div>
            <div className="employee-copy"><strong>{employee.name}</strong><small>{employee.role}</small><p>{employee.detail}</p></div>
            <span className={`employee-status is-${employee.tone}`}>{employee.status}</span>
          </article>)}
        </div>
      </section>

      <section className="exception-panel panel" aria-label="Exception queue">
        <div className="section-heading"><div><span className="eyebrow">Exception queue</span><h2>Attention required</h2></div><span className={`queue-state ${validated ? "is-closed" : "is-open"}`}>{exceptionState}</span></div>
        <div className="queue-toolbar" role="group" aria-label="Exception queue filters">
          {(["all", "open", "resolved"] as const).map((option) => <button className={`filter-button ${queueFilter === option ? "is-active" : ""}`} aria-pressed={queueFilter === option} key={option} onClick={() => setQueueFilter(option)} type="button">{option === "all" ? "All" : option === "open" ? "Open" : "Resolved"}</button>)}
          <span className="filter-note">{queueItems.length} of {incidents.length} records</span>
        </div>
        <div className="exception-list">
          {queueItems.map((item) => {
            const isPrimary = item.id === API_INCIDENT_ID;
            const itemResolved = ["validated", "reported", "failed", "denied"].includes(item.status);
            return <div className={`exception-row ${itemResolved ? "is-resolved" : ""}`} key={item.id}>
              <div className="exception-priority"><span className={`signal-dot ${itemResolved ? "is-emerald" : ""}`} /><span>{formatDetailStatus(item.severity)}</span></div>
              <div className="exception-main"><strong>{item.pipeline_name}</strong><span>{item.summary}</span><small>{item.run_id} · {formatDetailStatus(item.status)}{isPrimary ? ` · ${businessImpact.affected}` : ""}</small></div>
              {isPrimary ? <button className="secondary-button" onClick={onOpenWorkbench} type="button">{validated ? "Review resolution" : "Open workbench"}<Icon name="arrow" size={14} /></button> : <button className="secondary-button" onClick={() => onNotice("This seeded queue record is read-only; the governed walkthrough uses the schema-drift incident.")} type="button">View record<Icon name="arrow" size={14} /></button>}
            </div>;
          })}
          {queueItems.length === 0 && <p className="empty-state">No queue records match this filter.</p>}
        </div>
      </section>

      <div className="decision-boundary-note"><Icon name="shield" size={15} /><span><strong>Governed recovery boundary:</strong> the AI employees can gather evidence and propose a plan; only the Policy Guardian plus an accountable Operator can authorize execution.</span></div>
    </div>
  );
}

function RunbooksView({ onOpenWorkbench, onNotice }: { onOpenWorkbench: () => void; onNotice: (message: string) => void }) {
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(runbooks[0].id);
  const filtered = runbooks.filter((runbook) => `${runbook.title} ${runbook.purpose} ${runbook.id}`.toLowerCase().includes(query.trim().toLowerCase()));
  const selected = filtered.find((runbook) => runbook.id === selectedId) ?? filtered[0] ?? null;

  return (
    <div className="runbooks-view animate-in">
      <section className="page-heading">
        <div>
          <span className="eyebrow">Operational knowledge</span>
          <h1>Runbook library</h1>
          <p className="subhead">The cited procedures that keep a recovery decision constrained and reviewable.</p>
        </div>
        <span className="page-readiness"><span className="status-dot is-emerald" />Fixture catalog</span>
      </section>

      <section className="runbook-layout">
        <div className="panel runbook-list-panel">
          <div className="section-heading"><div><span className="eyebrow">Matched procedures</span><h2>{filtered.length} runbooks</h2></div><span className="count-badge">1 cited</span></div>
          <label className="search-field"><Icon name="search" size={15} /><span className="sr-only">Search runbooks</span><input aria-label="Search runbooks" onChange={(event) => setQuery(event.target.value)} placeholder="Search runbooks" value={query} /></label>
          <div className="runbook-list" role="list">
            {filtered.map((runbook) => <button className={`runbook-list-item ${selected?.id === runbook.id ? "is-selected" : ""}`} key={runbook.id} onClick={() => setSelectedId(runbook.id)} type="button">
              <span className="runbook-list-icon"><Icon name="file" size={16} /></span>
              <span><strong>{runbook.title}</strong><small>{runbook.id}</small></span>
              <span className={`runbook-status is-${runbook.status}`}>{runbook.status === "matched" ? "Matched" : "Available"}</span>
            </button>)}
            {filtered.length === 0 && <p className="empty-state">No runbooks match this search.</p>}
          </div>
        </div>

        {selected && <article className="panel runbook-detail-panel">
          <div className="eyebrow-row"><span className="eyebrow">{selected.id}</span><span className={`runbook-status is-${selected.status}`}>{selected.status === "matched" ? "Matched to incident" : "Available"}</span></div>
          <h2>{selected.title}</h2>
          <p className="runbook-purpose">{selected.purpose}</p>
          <div className="runbook-meta"><span><b>Owner</b>{selected.owner}</span><span><b>Last verified</b>{selected.lastVerified}</span><span><b>Scope</b>Fixture incident</span></div>
          <div className="runbook-steps"><span className="eyebrow">Procedure outline</span><ol>{selected.steps.map((step, index) => <li key={step}><span>{index + 1}</span><p>{step}</p></li>)}</ol></div>
          {selected.status === "matched" && <button className="secondary-button" onClick={onOpenWorkbench} type="button">Open governed workbench <Icon name="arrow" size={14} /></button>}
          {selected.status === "available" && <button className="secondary-button" onClick={() => onNotice("Runbook preview is available; execution still requires a cited recommendation, policy decision, and Operator approval.")} type="button">Preview boundary note <Icon name="shield" size={14} /></button>}
        </article>}
      </section>

      <div className="readiness-note"><Icon name="shield" size={15} /><span><strong>Submission boundary:</strong> this is a sanitized, read-only runbook catalog for the demo. Versioned production ownership, authoring, permissions, and change publishing are not ready and are intentionally outside this slice.</span></div>
    </div>
  );
}

function AuditLogView({ entries, onOpenWorkbench, onNotice }: { entries: AuditEntry[]; onOpenWorkbench: () => void; onNotice: (message: string) => void }) {
  const [query, setQuery] = useState("");
  const [adminEntries, setAdminEntries] = useState<AuditEntry[] | null>(null);
  const [adminLoading, setAdminLoading] = useState(false);
  const visibleEntries = adminEntries ?? entries;
  const filtered = visibleEntries.filter((entry) => `${entry.action} ${entry.detail} ${entry.actor}`.toLowerCase().includes(query.trim().toLowerCase()));

  const loadAdminAudit = async () => {
    setAdminLoading(true);
    try {
      const response = await fetch("/v1/audit-logs", { headers: API_ADMIN_HEADERS });
      if (!response.ok) throw new Error(response.status === 403 ? "Admin authorization is required for the cross-incident audit index." : "The audit index is unavailable.");
      const payload = await response.json() as { items: ApiAuditEvent[] };
      setAdminEntries(payload.items.map(mapAuditEvent));
      onNotice("Admin audit index loaded. Cross-incident filtering remains read-only.");
    } catch (error) {
      onNotice(error instanceof Error ? error.message : "The audit index is unavailable.");
    } finally {
      setAdminLoading(false);
    }
  };

  return (
    <div className="audit-view animate-in">
      <section className="page-heading">
        <div>
          <span className="eyebrow">Traceability workspace</span>
          <h1>Audit log</h1>
          <p className="subhead">An incident-scoped view of investigation, governance, and recovery events.</p>
        </div>
        <span className="page-readiness"><span className="status-dot is-emerald" />Append-only events</span>
      </section>

      <section className="audit-summary-grid" aria-label="Audit summary">
        <div className="panel metric-card"><span className="eyebrow">Events shown</span><strong>{filtered.length}</strong><small>{visibleEntries.length} events loaded</small></div>
        <div className="panel metric-card"><span className="eyebrow">Actors</span><strong>{new Set(visibleEntries.map((entry) => entry.actor)).size}</strong><small>System and demo integrations</small></div>
        <div className="panel metric-card"><span className="eyebrow">Scope</span><strong>{adminEntries ? "All" : "1"}</strong><small>{adminEntries ? "Admin audit index" : "Seeded incident"}</small></div>
        <div className="panel metric-card"><span className="eyebrow">Recovery writes</span><strong>0</strong><small>Fixture boundary only</small></div>
      </section>

      <section className="panel audit-full-panel">
        <div className="section-heading"><div><span className="eyebrow">{adminEntries ? "Admin event index" : "Event stream"}</span><h2>{adminEntries ? "All governed events" : "retail_orders_daily"}</h2></div><button className="text-action" onClick={onOpenWorkbench} type="button">Back to workbench <Icon name="arrow" size={14} /></button></div>
        <label className="search-field audit-search"><Icon name="search" size={15} /><span className="sr-only">Filter audit events</span><input aria-label="Filter audit events" onChange={(event) => setQuery(event.target.value)} placeholder="Filter by action or actor" value={query} /></label>
        <div className="audit-toolbar"><span className="muted-label">{adminEntries ? "Admin demo identity · cross-incident scope" : "Current incident scope"}</span><button className="secondary-button" disabled={adminLoading} onClick={() => void loadAdminAudit()} type="button">{adminLoading ? "Loading audit index..." : "Load admin audit index"}</button></div>
        <div className="audit-list audit-list-full">{filtered.map((entry) => <div className="audit-entry" key={`${entry.time}-${entry.action}`}><span className={`audit-marker is-${entry.tone}`} /><time>{entry.time}</time><div><strong>{entry.action}</strong><span>{entry.detail}</span></div><small>{entry.actor}</small></div>)}</div>
        {filtered.length === 0 && <p className="empty-state">No audit events match this filter.</p>}
      </section>

      <div className="readiness-note"><Icon name="shield" size={15} /><span><strong>Submission boundary:</strong> incident events are available to the demo identity; the optional cross-incident index requires Admin authorization. Retention, export, and production identity federation remain deferred.</span></div>
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
  const [liveDetail, setLiveDetail] = useState<ApiDetail | null>(null);
  const [queueIncidents, setQueueIncidents] = useState<ApiIncident[]>([]);
  const [agentResource, setAgentResource] = useState<ApiAgentDetail | null>(null);
  const [agentResourceError, setAgentResourceError] = useState<string | null>(null);
  const [executionResource, setExecutionResource] = useState<ApiExecutionDetail | null>(null);
  const [executionResourceError, setExecutionResourceError] = useState<string | null>(null);
  const [resourceLoading, setResourceLoading] = useState(false);
  const [report, setReport] = useState<ApiReport | null>(null);
  const [feedbackText, setFeedbackText] = useState("");
  const [livePolicyDocument, setLivePolicyDocument] = useState<ApiPolicy | null>(null);
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [draftAction, setDraftAction] = useState(policy.action);
  const recoveryProposalKey = "ui-schema-drift-recovery";
  const [editingAction, setEditingAction] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const integration = useMemo(() => {
    const details = demoStatus?.adapter_status;
    if (!details) return { label: "Fixture mode", detail: "Sanitized evidence only", notice: "Fixture mode uses sanitized evidence and does not execute recovery actions.", actionLabel: "Investigate fixture incident" };
    const context = Object.entries(details).filter(([name]) => name !== "decision");
    const liveContext = context.some(([, value]) => value.mode === "live");
    const degradedContext = context.filter(([, value]) => value.status !== "available");
    const contextReason = degradedContext.length > 0 ? ` ${degradedContext.map(([name, value]) => `${name}: ${value.reason ?? value.status}`).join("; ")}` : "";
    const decision = details.decision;
    if (liveContext && decision?.mode === "live") return { label: "CoCo live path", detail: "Live context + live decision", notice: `CoCo supplied live read-only context and decision support.${contextReason} Policy remains server-side; recovery remains fixture-only.`, actionLabel: "Investigate with CoCo" };
    if (liveContext) return { label: "CoCo live context", detail: "Fixture decision + recovery", notice: `CoCo supplied live read-only context.${contextReason} ${decision?.reason ?? "Decision support is using the deterministic fixture fallback."} Recovery remains fixture-only.`, actionLabel: "Investigate with CoCo" };
    if (decision?.status === "degraded") return { label: "CoCo fallback", detail: "Fixture context + decision", notice: `${decision.reason ?? "CoCo was unavailable."} The deterministic fixture path remains governed by server policy.`, actionLabel: "Investigate fixture incident" };
    if (decision?.source === "coco") return { label: "CoCo configured", detail: "Awaiting verified call", notice: "CoCo is configured but the latest investigation has not verified a live result.", actionLabel: "Investigate with CoCo" };
    return { label: "Fixture mode", detail: "Sanitized evidence only", notice: "Fixture mode uses sanitized evidence and does not execute recovery actions.", actionLabel: "Investigate fixture incident" };
  }, [demoStatus]);

  const refresh = async () => {
    setLoading(true);
    try {
      const [detail, statusResponse, reportResponse, policyResponse, queueResponse, agentResponse] = await Promise.all([fetchIncident(), fetch("/v1/demo/status"), fetch(`/v1/incidents/${API_INCIDENT_ID}/report`), fetch("/v1/policies/current"), fetchIncidents(), fetchAgentDetail()]);
      if (!statusResponse.ok) throw new Error("Demo readiness status is unavailable.");
      setDemoStatus(await statusResponse.json() as DemoStatus);
      const reportData = reportResponse.ok ? await reportResponse.json() as ApiReport : null;
      setReport(reportData);
      setLiveDetail(detail);
      setQueueIncidents(queueResponse.items);
      setAgentResource(agentResponse);
      setAgentResourceError(null);
      const latestExecution = detail.executions.at(-1);
      if (latestExecution) {
        try {
          setExecutionResource(await fetchExecutionDetail(latestExecution.id));
          setExecutionResourceError(null);
        } catch (error) {
          setExecutionResourceError(error instanceof Error ? error.message : "Execution detail is unavailable.");
        }
      } else {
        setExecutionResource(null);
        setExecutionResourceError(null);
      }
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
      const approvals = detail.approvals ?? [];
      const timeline = [
        ...detail.audit.map((entry) => ({ createdAt: entry.created_at, action: entry.action, detail: entry.outcome, actor: entry.actor_role, tone: entry.outcome.includes("failed") ? "warning" as const : "neutral" as const })),
        ...approvals.map((entry) => ({ createdAt: entry.created_at, action: `Operator ${entry.decision}`, detail: entry.reason, actor: entry.actor_role, tone: entry.decision === "approved" ? "success" as const : "warning" as const })),
      ].sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());
      setLiveAudit(timeline.map(({ createdAt, ...entry }) => ({ ...entry, time: new Date(createdAt).toLocaleTimeString() })));
      if (detail.recommendation) {
        setLivePolicy({ decision: "Approval required", risk: "High", reason: detail.recommendation.uncertainty, action: detail.recommendation.recommended_action });
        setDraftAction((current) => editingAction ? current : detail.recommendation?.recommended_action ?? current);
      }
      if (reportData?.policy_decision) setLivePolicy({ decision: reportData.policy_decision.decision.replace("_", " "), risk: reportData.policy_decision.risk, reason: detail.recommendation?.uncertainty ?? "Policy decision loaded from the server.", action: detail.recommendation?.recommended_action ?? "" });
      setApiError(null);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Unable to load incident data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void refresh(); }, []);

  const reloadAgentResource = async () => {
    setResourceLoading(true);
    try {
      setAgentResource(await fetchAgentDetail());
      setAgentResourceError(null);
    } catch (error) {
      setAgentResourceError(error instanceof Error ? error.message : "Agent detail is unavailable.");
    } finally {
      setResourceLoading(false);
    }
  };

  const reloadExecutionResource = async () => {
    const executionId = liveDetail?.executions.at(-1)?.id;
    if (!executionId) {
      setExecutionResourceError("No execution exists for this incident yet.");
      return;
    }
    setResourceLoading(true);
    try {
      setExecutionResource(await fetchExecutionDetail(executionId));
      setExecutionResourceError(null);
    } catch (error) {
      setExecutionResourceError(error instanceof Error ? error.message : "Execution detail is unavailable.");
    } finally {
      setResourceLoading(false);
    }
  };

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
    if (actionLoading) return;
    setActionLoading(true);
    try {
      const response = await fetch(`/v1/incidents/${API_INCIDENT_ID}/${path}`, { method: "POST", headers: { ...API_HEADERS, "Idempotency-Key": key }, body: body ? JSON.stringify(body) : undefined });
      if (!response.ok) {
        const payload = await response.json().catch(() => null) as { error?: { code?: string; message?: string } } | null;
        const code = payload?.error?.code;
        const message = payload?.error?.message ?? "The server rejected this governed action.";
        throw new Error(code ? `${code}: ${message}` : message);
      }
      await refresh();
      setNotice(path === "investigate" ? "Investigation completed. Adapter status reflects the actual CoCo or fixture result; recovery remains fixture-only." : "Governed fixture action completed and the incident view was refreshed.");
    } catch (error) {
      await refresh().catch(() => undefined);
      setNotice(error instanceof Error ? error.message : "Action failed.");
    } finally {
      setActionLoading(false);
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

  const searchMatches = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return [];
    const items = [
      { label: liveIncident.pipeline, detail: `${liveIncident.runId} Â· ${liveIncident.status}`, action: "incident" },
      ...liveEvidence.map((item) => ({ label: item.sourceLabel, detail: item.summary, action: "evidence" })),
      ...runbooks.map((runbook) => ({ label: runbook.title, detail: runbook.id, action: "runbook" })),
      ...liveAudit.map((entry) => ({ label: entry.action, detail: `${entry.actor} Â· ${entry.detail}`, action: "audit" })),
    ];
    return items.filter((item) => `${item.label} ${item.detail}`.toLowerCase().includes(query)).slice(0, 6);
  }, [liveAudit, liveEvidence, liveIncident, searchQuery]);

  const focusWorkflow = (step: WorkflowStep) => {
    document.getElementById(step.target)?.scrollIntoView({ behavior: "smooth", block: "start" });
    setNotice(`${step.label}: ${step.description}`);
  };

  const openWorkbench = () => {
    setActiveNav("Workbench");
    setSearchOpen(false);
  };

  const openAuditLog = () => {
    setActiveNav("Audit log");
    setSearchOpen(false);
  };

  const approveRecovery = () => {
    const reason = draftAction.trim() === livePolicy.action.trim()
      ? "Approve fixture recovery."
      : `Approve edited recovery plan: ${draftAction.trim()}`;
    void runAction("approvals", { action: "schema_drift_recovery", approved: true, reason }, recoveryProposalKey);
    setEditingAction(false);
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
          {[{ label: "Overview", icon: "grid" as IconName }, { label: "Workbench", icon: "activity" as IconName }, { label: "Agent detail", icon: "spark" as IconName }, { label: "Execution detail", icon: "terminal" as IconName }, { label: "Runbooks", icon: "file" as IconName }, { label: "Policy", icon: "shield" as IconName }, { label: "Audit log", icon: "clipboard" as IconName }].map((item) => (
            <button aria-label={item.label} className={`nav-item ${activeNav === item.label ? "is-active" : ""}`} key={item.label} onClick={() => { if (item.label === "Workbench") openWorkbench(); else { setActiveNav(item.label); setSearchOpen(false); window.scrollTo({ top: 0, behavior: "smooth" }); if (item.label === "Agent detail") void reloadAgentResource(); if (item.label === "Execution detail") void reloadExecutionResource(); } }} type="button">
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.label === "Workbench" && <span className="nav-count">1</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="rail-label">Environment</div>
          <button className="environment-card" onClick={() => setNotice(integration.notice)} type="button">
            <span className="signal-dot is-emerald" />
            <span><strong>{integration.label}</strong><small>{integration.detail}</small></span>
            <Icon name="chevron" size={15} />
          </button>
          <div className="user-chip"><span className="avatar">OP</span><span><strong>Operator</strong><small>Demo identity</small></span><span className="status-dot" /></div>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><Icon name="chevron" size={13} /><strong>{activeNav}</strong></div>
          <div className="topbar-actions">
            <button className={`topbar-button ${searchOpen ? "is-active" : ""}`} onClick={() => setSearchOpen((current) => !current)} title="Search workspace" type="button"><Icon name="search" size={16} /><span>Search</span></button>
            <button className="topbar-button" disabled={loading || actionLoading} onClick={() => void resetDemo()} title="Admin-only fixture reset using the explicit Admin demo identity" type="button">Reset fixture · Admin demo</button>
            <button className="icon-button" onClick={() => setNotice("All fixture adapters are responding. Snowflake metadata is marked degraded by design.")} title="System health" type="button"><span className="status-dot is-emerald" /><Icon name="activity" size={16} /></button>
          </div>
          {searchOpen && <div className="workspace-search" role="search">
            <label className="search-field"><Icon name="search" size={15} /><span className="sr-only">Search workspace</span><input aria-label="Search workspace" autoFocus onChange={(event) => setSearchQuery(event.target.value)} placeholder="Search incident, evidence, runbook, or audit" value={searchQuery} /></label>
            {searchQuery.trim() && <div className="search-results">{searchMatches.length > 0 ? searchMatches.map((item) => <button key={`${item.action}-${item.label}`} onClick={item.action === "audit" ? openAuditLog : openWorkbench} type="button"><strong>{item.label}</strong><small>{item.detail}</small></button>) : <p className="empty-state">No workspace matches.</p>}</div>}
            {!searchQuery.trim() && <p className="search-hint">Local demo search covers the seeded incident, evidence, runbook citations, and audit events.</p>}
          </div>}
        </header>

        <div className="content-wrap">
          {loading && <div className="api-banner is-loading" role="status"><span className="status-dot is-emerald" />Loading persisted incident state…</div>}
          {apiError && <div className="api-banner is-error" role="alert"><span className="signal-dot" />{apiError} <button className="text-action" onClick={() => void refresh()} type="button">Retry</button></div>}
          {demoStatus && <div className="api-banner is-ready" role="status"><span className="status-dot is-emerald" />{demoStatus.fixture} · {demoStatus.mode} · database ready · {integration.label} · {integration.detail} · recovery fixture-only</div>}
          {activeNav === "Policy" ? <PolicyView policy={livePolicyDocument} loading={loading} error={policyError} onRetry={() => void refresh()} /> : activeNav === "Agent detail" ? <AgentDetailView resource={agentResource} loading={loading || resourceLoading} error={agentResourceError} onRetry={() => void reloadAgentResource()} /> : activeNav === "Execution detail" ? <ExecutionDetailView resource={executionResource} loading={loading || resourceLoading} error={executionResourceError} onRetry={() => void reloadExecutionResource()} /> : activeNav === "Overview" ? <CommandCenter incident={liveIncident} incidents={queueIncidents} evidenceCount={liveEvidence.length} report={report} integrationLabel={integration.label} onOpenWorkbench={openWorkbench} onNotice={setNotice} /> : activeNav === "Runbooks" ? <RunbooksView onOpenWorkbench={openWorkbench} onNotice={setNotice} /> : activeNav === "Audit log" ? <AuditLogView entries={liveAudit} onOpenWorkbench={openWorkbench} onNotice={setNotice} /> : <>
          <section className="incident-header animate-in" id="incident-overview">
            <div>
              <div className="eyebrow-row"><span className="eyebrow">Exception Workbench</span><span className="badge badge-warning"><span className="signal-dot" />{liveIncident.severity} priority</span></div>
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

           <section className="governance-chain panel animate-in delay-1" aria-label="Governed decision boundary">
             <div className="section-heading"><div><span className="eyebrow">Decision boundary</span><h2>AI proposes. Policy controls.</h2></div><span className="count-badge">No direct production writes</span></div>
             <div className="governance-chain-list">
               {governanceChain.map((item, index) => <React.Fragment key={item.label}>
                 <div className={`governance-node ${index === 2 ? "is-policy" : index === 3 ? "is-approval" : ""}`}>
                   <strong>{item.label}</strong>
                   <small>{item.detail}</small>
                 </div>
                 {index < governanceChain.length - 1 && <span className="governance-arrow" aria-hidden="true">→</span>}
               </React.Fragment>)}
             </div>
           </section>

           <AgentExecutionDetail detail={liveDetail} demoStatus={demoStatus} />

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
                <div className="policy-action"><div className="section-heading"><span className="eyebrow">Proposed action</span><button className="text-action action-edit" onClick={() => setEditingAction((current) => !current)} type="button">{editingAction ? "Close editor" : "Edit proposal"}</button></div>{editingAction ? <><textarea aria-label="Edit proposed action" className="action-editor" onChange={(event) => setDraftAction(event.target.value)} value={draftAction} /><small className="editor-note">Edit the operator-facing recovery plan. The canonical policy action remains <code>schema_drift_recovery</code>.</small><button className="text-action" onClick={() => { setEditingAction(false); setNotice("Edited recovery plan will be captured in the approval justification."); }} type="button">Save proposed action <Icon name="arrow" size={14} /></button></> : <p>{draftAction}</p>}</div>
                <p className="policy-reason">{livePolicy.reason}</p>
                <button className="secondary-button" onClick={() => setNotice(livePolicy.reason)} type="button"><Icon name="shield" size={15} />Explain policy gate</button>
                <div className="fixture-actions" aria-busy={actionLoading}>
                  {actionLoading && <span className="muted-label" role="status">Working through the governed action…</span>}
                  {loading && <span className="muted-label">Loading live incident state…</span>}
                  {apiError && <button className="secondary-button" disabled={actionLoading} onClick={() => void refresh()} type="button">Retry API connection</button>}
                  {!loading && liveIncident.status === "Created" && <button className="secondary-button" disabled={actionLoading} onClick={() => void runAction("investigate")} type="button">{integration.actionLabel}</button>}
                   {!loading && ["Investigated", "Awaiting Approval"].includes(liveIncident.status) && <><button className="secondary-button" disabled={actionLoading} onClick={() => void runAction("executions", { action: "schema_drift_recovery" }, recoveryProposalKey)} type="button"><Icon name="lock" size={15} />Try execution — show approval gate</button><button className="secondary-button" disabled={actionLoading} onClick={approveRecovery} type="button">Approve fixture recovery</button><button className="secondary-button" disabled={actionLoading} onClick={() => void runAction("approvals", { action: "schema_drift_recovery", approved: false, reason: "Reject fixture recovery." }, `ui-schema-drift-rejection-${Date.now()}`)} type="button">Reject recovery</button></>}
                  {!loading && liveIncident.status === "Approved" && <button className="secondary-button" disabled={actionLoading} onClick={() => void runAction("executions", { action: "schema_drift_recovery" })} type="button">Execute fixture recovery</button>}
                  {!loading && liveIncident.status === "Recovered" && <button className="secondary-button" disabled={actionLoading} onClick={() => void runAction("validate")} type="button">Validate recovery</button>}
                </div>
                <div className="preview-note"><span className="signal-dot is-amber" /><span>{integration.notice}</span></div>
              </section>
              <section className="panel recommendation-panel animate-in delay-4">
                 <div className="section-heading"><div><span className="eyebrow">Decision support</span><h2>Root cause signal</h2></div><span className="confidence">{report?.recommendation?.confidence_band ?? "High"}</span></div>
                 <p className="root-cause">{report?.recommendation?.cause ?? "Upstream raw orders added order_channel, but the staging projection was not updated before the daily run."}</p>
                 <div className="signal-row"><span><Icon name="spark" size={14} />{report?.recommendation?.evidence_ids.length ?? 4} supporting sources</span><span><Icon name="file" size={14} />{report?.recommendation?.runbook_ids.length ?? 1} cited runbook</span></div>
                 <div className="impact-grid">
                   <div className="impact-card impact-card-business"><span className="eyebrow">Business impact</span><p>{report?.recommendation?.impact ?? businessImpact.summary}</p><small>{businessImpact.affected}</small></div>
                   <div className="impact-card impact-card-alternative"><span className="eyebrow">Alternative considered</span><p>{report?.recommendation?.alternatives[0]?.action ?? businessImpact.alternative}</p><small>{report?.recommendation?.alternatives[0]?.reason ?? businessImpact.alternativeReason}</small></div>
                 </div>
              </section>
            </aside>
          </div>

          <section className="panel audit-panel animate-in delay-4" id="audit-timeline">
            <div className="section-heading"><div><span className="eyebrow">Traceability</span><h2>Audit timeline</h2></div><button className="text-action" onClick={openAuditLog} type="button">View full log <Icon name="arrow" size={14} /></button></div>
            <div className="audit-list">{liveAudit.map((entry) => <div className="audit-entry" key={`${entry.time}-${entry.action}`}><span className={`audit-marker is-${entry.tone}`} /><time>{entry.time}</time><div><strong>{entry.action}</strong><span>{entry.detail}</span></div><small>{entry.actor}</small></div>)}</div>
          </section>

          <section className="panel report-panel animate-in delay-4" id="incident-report">
            <div className="section-heading"><div><span className="eyebrow">Evidence-linked RCA</span><h2>Incident report</h2></div><span className="count-badge">{report?.feedback_count ?? 0} feedback</span></div>
            {report?.recommendation ? <div className="report-content"><p className="root-cause">{report.recommendation.cause}</p><div className="signal-row"><span>{report.recommendation.confidence_band} confidence</span><span>{report.recommendation.evidence_ids.length} evidence IDs</span><span>{report.recommendation.runbook_ids.length} runbook citation</span></div><p className="policy-reason">Impact: {report.recommendation.impact}</p><p className="policy-reason">Alternative: {report.recommendation.alternatives[0]?.action} - {report.recommendation.alternatives[0]?.reason}</p><p className="policy-reason">Uncertainty: {report.recommendation.uncertainty}</p>{report.validation && <p className="policy-reason">Validation: {report.validation.status} · {report.validation.checks.join(" · ")}</p>}{report.execution?.external_reference && <p className="policy-reason">External reference: {report.execution.external_reference}</p>}</div> : <p className="muted-label">Report becomes available after investigation.</p>}
            <div className="feedback-form"><input aria-label="Operator feedback" onChange={(event) => setFeedbackText(event.target.value)} placeholder="Add an operator correction" value={feedbackText} /><button className="secondary-button" disabled={!feedbackText.trim()} onClick={() => void submitFeedback()} type="button">Record feedback</button></div>
          </section>

          <footer className="workspace-footer"><span><span className="signal-dot is-emerald" />{integration.label} · {integration.detail}</span><span>PipelinePilot v0.3 · governed by policy · recovery fixture-only</span></footer>
          </>}
        </div>
        {notice && <button className="notice-toast" onClick={() => setNotice(null)} type="button"><Icon name="spark" size={15} /><span>{notice}</span><span className="toast-dismiss">Dismiss</span></button>}
      </main>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
