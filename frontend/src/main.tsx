import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Session } from "@supabase/supabase-js";
import { Download, FileUp, LogOut, Monitor, Moon, Plus, RefreshCw, ShieldCheck, Sun } from "lucide-react";
import { ApiAuthError, request } from "./lib/api";
import { frontendConfig } from "./lib/config";
import { supabase } from "./lib/supabase";
import "./styles.css";

const client = new QueryClient();

type Project = { id: string; name: string; description: string; requirements_count: number; changed_requirements: number; unresolved_findings: number };
type ImportBatch = { id: string; filename: string; version_label: string; row_count: number; status: string };
type Comparison = { id: string; baseline_import_id: string; comparison_import_id: string; summary_json: Record<string, number>; status: string };
type Change = { id: string; external_id: string; change_type: string; changed_fields: Record<string, unknown>; text_diff: string };
type Finding = { id: string; requirement_change_id: string; impacted_requirement_external_id: string; severity: string; confidence: number; detection_method: string; reason: string; review_status: string; reviewer_note?: string };
type ThemePreference = "system" | "light" | "dark";

function downloadBase64(name: string, mediaType: string, content: string) {
  const link = document.createElement("a");
  link.href = `data:${mediaType};base64,${content}`;
  link.download = name;
  link.click();
}

export function App() {
  return <QueryClientProvider client={client}><AuthGate /></QueryClientProvider>;
}

function AuthGate() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(frontendConfig.authEnabled);
  const [authError, setAuthError] = useState<string | null>(null);

  React.useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return undefined;
    }
    let active = true;
    supabase.auth.getSession().then(({ data, error }) => {
      if (!active) return;
      if (error) setAuthError(error.message);
      setSession(data.session);
      setLoading(false);
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setAuthError(null);
      if (!nextSession) client.clear();
    });
    return () => {
      active = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  if (frontendConfig.authConfigError) {
    return <ConfigError message={frontendConfig.authConfigError} />;
  }
  if (loading) {
    return <LoadingScreen />;
  }
  if (supabase && !session) {
    return <AuthScreen initialError={authError} />;
  }
  return <RadarApp session={session} />;
}

function LoadingScreen() {
  return (
    <main className="auth-shell">
      <div className="auth-panel status-panel">
        <ReqRadarWordmark />
        <p>Checking your session...</p>
      </div>
    </main>
  );
}

function ConfigError({ message }: { message: string }) {
  return (
    <main className="auth-shell">
      <div className="auth-panel status-panel">
        <ReqRadarWordmark />
        <p role="alert" className="form-error">{message}</p>
      </div>
    </main>
  );
}

function AuthScreen({ initialError }: { initialError: string | null }) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(initialError);
  const [pending, setPending] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!supabase) return;
    setPending(true);
    setError(null);
    setMessage(null);
    const result = mode === "login"
      ? await supabase.auth.signInWithPassword({ email, password })
      : await supabase.auth.signUp({ email, password });
    setPending(false);
    if (result.error) {
      setError(result.error.message);
      return;
    }
    if (mode === "signup" && !result.data.session) {
      setMessage("Check your email to confirm your account before signing in.");
    }
  };

  return (
    <main className="auth-shell">
      <section className="auth-panel">
        <ReqRadarWordmark />
        <div className="auth-tabs" role="tablist" aria-label="Authentication mode">
          <button type="button" className={mode === "login" ? "active" : ""} onClick={() => { setMode("login"); setError(null); setMessage(null); }}>Log in</button>
          <button type="button" className={mode === "signup" ? "active" : ""} onClick={() => { setMode("signup"); setError(null); setMessage(null); }}>Create account</button>
        </div>
        <form className="auth-form" onSubmit={submit}>
          <label>Email<input aria-label="Email" className="field" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
          <label>Password<input aria-label="Password" className="field" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(event) => setPassword(event.target.value)} required minLength={6} /></label>
          {error ? <p className="form-error" role="alert">{error}</p> : null}
          {message ? <p className="form-success" role="status">{message}</p> : null}
          <button className="btn" type="submit" disabled={pending}>{pending ? "Working..." : mode === "login" ? "Log in" : "Create account"}</button>
        </form>
      </section>
    </main>
  );
}

function useThemePreference() {
  const [theme, setTheme] = useState<ThemePreference>(() => (globalThis.localStorage?.getItem("reqradar-theme") as ThemePreference) || "system");
  React.useEffect(() => {
    const media = globalThis.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const dark = theme === "dark" || (theme === "system" && media.matches);
      globalThis.document.documentElement.dataset.theme = dark ? "dark" : "light";
    };
    globalThis.localStorage?.setItem("reqradar-theme", theme);
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [theme]);
  return { theme, setTheme };
}

function ReqRadarLogo() {
  return (
    <svg className="logo-mark" viewBox="0 0 40 40" role="img" aria-label="ReqRadar logo">
      <rect width="40" height="40" rx="10" />
      <circle className="radar-ring outer" cx="20" cy="20" r="12.5" />
      <circle className="radar-ring inner" cx="20" cy="20" r="7" />
      <path className="radar-sweep" d="M20 20 12 12" />
      <circle className="radar-center" cx="20" cy="20" r="2.6" />
      <circle className="radar-blip" cx="29" cy="14" r="2.3" />
      <circle className="radar-blip" cx="17" cy="31" r="2.1" />
    </svg>
  );
}

function ReqRadarWordmark() {
  return (
    <div className="wordmark">
      <ReqRadarLogo />
      <div>
        <h1>ReqRadar</h1>
        <p>Know what a requirement change affects before it becomes a defect.</p>
      </div>
    </div>
  );
}

function ThemeToggle({ theme, setTheme }: { theme: ThemePreference; setTheme: (theme: ThemePreference) => void }) {
  const icon = theme === "dark" ? <Moon size={16} /> : theme === "light" ? <Sun size={16} /> : <Monitor size={16} />;
  return (
    <label className="theme-control">
      {icon}
      <span className="sr-only">Theme</span>
      <select aria-label="Theme" value={theme} onChange={(event) => setTheme(event.target.value as ThemePreference)}>
        <option value="system">System</option>
        <option value="light">Light</option>
        <option value="dark">Dark</option>
      </select>
    </label>
  );
}

function RadarApp({ session }: { session: Session | null }) {
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const { theme, setTheme } = useThemePreference();
  const projects = useQuery({ queryKey: ["projects"], queryFn: () => request<Project[]>("/projects") });
  const active = projects.data?.find((p) => p.id === activeProjectId) || projects.data?.[0];
  const signOut = async () => {
    client.clear();
    await supabase?.auth.signOut();
  };
  return (
    <main className="app-shell">
      <header className="app-header">
        <ReqRadarWordmark />
        <div className="header-actions">
          {!supabase && frontendConfig.isDevelopment ? <span className="dev-pill"><ShieldCheck size={16} /> Dev</span> : null}
          {session ? <span className="user-pill" title={session.user.email || session.user.id}>{session.user.email || "Signed in"}</span> : null}
          <ThemeToggle theme={theme} setTheme={setTheme} />
          {supabase ? <button className="small-btn" type="button" onClick={signOut}><LogOut size={15} /> Sign out</button> : null}
        </div>
      </header>
      <section className="app-layout">
        <aside className="sidebar">
          <ProjectCreator onCreated={setActiveProjectId} />
          <div className="sidebar-label">Projects</div>
          <div className="project-list">
            {projects.data?.map((project) => (
              <button key={project.id} className={`project-tab ${active?.id === project.id ? "active" : ""}`} onClick={() => setActiveProjectId(project.id)}>
                <span aria-hidden="true" />
                <div>
                  <div className="font-medium">{project.name}</div>
                  <div>{project.changed_requirements} changed · {project.unresolved_findings} review</div>
                </div>
              </button>
            ))}
          </div>
        </aside>
        <section className="workspace">{active ? <ProjectWorkspace project={active} /> : <EmptyState />}</section>
      </section>
    </main>
  );
}

function ProjectCreator({ onCreated }: { onCreated: (id: string) => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const mutation = useMutation({ mutationFn: () => request<Project>("/projects", { method: "POST", body: JSON.stringify({ name, description: "" }) }), onSuccess: (project) => { setName(""); onCreated(project.id); queryClient.invalidateQueries({ queryKey: ["projects"] }); } });
  return (
    <form className="project-create" onSubmit={(e) => { e.preventDefault(); if (name.trim()) mutation.mutate(); }}>
      <div className="project-create-fields">
        <input data-testid="project-name" className="field" placeholder="New project" value={name} onChange={(e) => setName(e.target.value)} />
        {mutation.error ? <p className="form-error" role="alert">{mutation.error.message}</p> : null}
      </div>
      <button data-testid="create-project" className="icon-btn" title="New Project"><Plus size={16} /></button>
    </form>
  );
}

function EmptyState() {
  return <div className="empty-state">Create a project to upload your first requirements register.</div>;
}

function ProjectWorkspace({ project }: { project: Project }) {
  const queryClient = useQueryClient();
  const [csvText, setCsvText] = useState("");
  const [filename, setFilename] = useState("");
  const [versionLabel, setVersionLabel] = useState("V1");
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [validationMessages, setValidationMessages] = useState<string[]>([]);
  const [uploadKey, setUploadKey] = useState(0);
  const [comparisonId, setComparisonId] = useState<string | null>(null);
  const detail = useQuery({ queryKey: ["project", project.id], queryFn: () => request<{ imports: ImportBatch[]; comparisons: Comparison[] }>(`/projects/${project.id}`) });
  const comparison = useQuery({ queryKey: ["comparison", comparisonId], queryFn: () => request<{ comparison: Comparison; changes: Change[]; findings: Finding[] }>(`/projects/${project.id}/comparisons/${comparisonId}`), enabled: Boolean(comparisonId) });
  const importMutation = useMutation({ mutationFn: () => request<ImportBatch>(`/projects/${project.id}/imports`, { method: "POST", body: JSON.stringify({ filename, version_label: versionLabel, csv_text: csvText, mapping }) }), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["project", project.id] }); setCsvText(""); setFilename(""); setUploadKey((value) => value + 1); setValidationMessages(["Import complete"]); } });
  const handleSelectedFile = async (file: File | undefined) => {
    if (!file) return;
    setFilename(file.name);
    setCsvText(await file.text());
    setMapping({ "Requirement ID": "Requirement ID", Type: "Type", Title: "Title", Description: "Description", Status: "Status", "Parent ID": "Parent ID", "Related To": "Related To", Tags: "Tags", Owner: "Owner" });
    setValidationMessages([`${file.name} ready for mapping`, "Requirement ID and Title mapped"]);
  };
  const compareMutation = useMutation({ mutationFn: () => { const imports = detail.data?.imports || []; return request<Comparison>(`/projects/${project.id}/comparisons`, { method: "POST", body: JSON.stringify({ baseline_import_id: imports[imports.length - 2]?.id, comparison_import_id: imports[imports.length - 1]?.id }) }); }, onSuccess: (data) => { setComparisonId(data.id); queryClient.invalidateQueries({ queryKey: ["project", project.id] }); } });
  const imports = detail.data?.imports || [];
  const baseline = imports[imports.length - 2];
  const latest = imports[imports.length - 1];
  return (
    <div className="workspace-stack">
      <div className="workspace-header">
        <div>
          <h2>{project.name}</h2>
          <p>{project.requirements_count} requirements · {baseline?.version_label || "V1"} → {latest?.version_label || "V2"}</p>
        </div>
        <button data-testid="compare-versions" className="btn" disabled={(detail.data?.imports.length || 0) < 2} onClick={() => compareMutation.mutate()}><RefreshCw size={16} /> Compare versions</button>
      </div>
      <div className="version-strip">
        <span><strong>{baseline?.version_label || "V1"}</strong> {baseline?.filename || "No baseline yet"}</span>
        <span aria-hidden="true">→</span>
        <span><strong>{latest?.version_label || "V2"}</strong> {latest?.filename || "Upload comparison"}</span>
      </div>
      <div className="setup-grid">
        <section className="upload-section">
          <h3 className="section-title"><FileUp size={16} /> Upload New Version</h3>
          <input key={uploadKey} data-testid="csv-upload" type="file" accept=".csv" className="text-sm" onInput={(e) => handleSelectedFile(e.currentTarget.files?.[0])} onChange={(e) => handleSelectedFile(e.currentTarget.files?.[0])} />
          <input data-testid="version-label" className="field" value={versionLabel} onChange={(e) => setVersionLabel(e.target.value)} placeholder="Version label" />
          <MappingEditor mapping={mapping} setMapping={setMapping} />
          <div data-testid="validation-messages" className="space-y-1 text-xs text-slate-600">{validationMessages.map((message) => <div key={message}>{message}</div>)}</div>
          {importMutation.error ? <div className="text-xs text-red-700">{importMutation.error.message}</div> : null}
          <button data-testid="import-csv" className="btn w-full justify-center" disabled={!csvText || importMutation.isPending} onClick={() => importMutation.mutate()}>Import CSV</button>
        </section>
        <section className="imports-section">
          <h3 className="section-title">Imports</h3>
          <div className="imports-table">
            {(detail.data?.imports || []).map((item) => <div className="tr" key={item.id}><span>{item.version_label}</span><span>{item.filename}</span><span>{item.row_count} rows</span><span>{item.status}</span></div>)}
          </div>
        </section>
      </div>
      {comparison.data ? (
        <ComparisonResults project={project} imports={imports} data={comparison.data} onBackToHistory={() => setComparisonId(null)} />
      ) : (
        <ComparisonHistory comparisons={detail.data?.comparisons || []} imports={imports} setComparisonId={setComparisonId} />
      )}
    </div>
  );
}

function MappingEditor({ mapping, setMapping }: { mapping: Record<string, string>; setMapping: (m: Record<string, string>) => void }) {
  return <div className="grid grid-cols-2 gap-2 text-xs">{Object.keys(mapping).map((field) => <label key={field} className="space-y-1"><span>{field}</span><input className="field" value={mapping[field]} onChange={(e) => setMapping({ ...mapping, [field]: e.target.value })} /></label>)}</div>;
}

function comparisonVersionLabel(comparison: Comparison, imports: ImportBatch[]) {
  const labels = new Map(imports.map((item) => [item.id, item.version_label]));
  return `${labels.get(comparison.baseline_import_id) || "Unknown"} → ${labels.get(comparison.comparison_import_id) || "Unknown"}`;
}

function ComparisonHistory({ comparisons, imports, setComparisonId }: { comparisons: Comparison[]; imports: ImportBatch[]; setComparisonId: (id: string) => void }) {
  return (
    <section className="history-section">
      <h3 className="section-title">Comparison History</h3>
      {comparisons.map((comparison) => (
        <button data-testid="comparison-history-row" className="history-row" key={comparison.id} onClick={() => setComparisonId(comparison.id)}>
          <strong>{comparisonVersionLabel(comparison, imports)}</strong>
          <span>Changed {comparison.summary_json.MODIFIED || 0} · Added {comparison.summary_json.ADDED || 0} · Removed {comparison.summary_json.REMOVED || 0} · Impacts {comparison.summary_json.impact_findings || 0}</span>
        </button>
      ))}
    </section>
  );
}

function ComparisonResults({ project, imports, data, onBackToHistory }: { project: Project; imports: ImportBatch[]; data: { comparison: Comparison; changes: Change[]; findings: Finding[] }; onBackToHistory: () => void }) {
  const [selected, setSelected] = useState(data.changes.find((c) => c.change_type !== "UNCHANGED")?.id || data.changes[0]?.id);
  const [changeTypeFilter, setChangeTypeFilter] = useState("ALL");
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const change = data.changes.find((c) => c.id === selected);
  const findings = data.findings.filter((f) => f.requirement_change_id === selected && (severityFilter === "ALL" || f.severity === severityFilter));
  const rows = data.changes.filter((c) => c.change_type !== "UNCHANGED" && (changeTypeFilter === "ALL" || c.change_type === changeTypeFilter));
  const versionLabel = comparisonVersionLabel(data.comparison, imports);
  return (
    <section className="comparison-section">
      <div className="comparison-nav">
        <button data-testid="back-to-history" className="link-btn" type="button" onClick={onBackToHistory}>← Comparison history</button>
        <div className="comparison-breadcrumb">
          <button data-testid="project-breadcrumb" type="button" onClick={onBackToHistory}>{project.name}</button>
          <span>/</span>
          <strong>Comparison {versionLabel}</strong>
        </div>
      </div>
      <div className="summary-grid">
        {["MODIFIED", "ADDED", "REMOVED", "impact_findings", "high_impact"].map((key) => <div key={key}><span>{key.replace("_", " ")}</span><strong>{data.comparison.summary_json[key] || 0}</strong></div>)}
      </div>
      <div className="comparison-workspace">
        <div className="change-rail">
          <div className="filter-row">
          <select data-testid="change-filter" className="field max-w-44" value={changeTypeFilter} onChange={(e) => setChangeTypeFilter(e.target.value)}><option>ALL</option><option>MODIFIED</option><option>ADDED</option><option>REMOVED</option></select>
          <select data-testid="severity-filter" className="field max-w-44" value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}><option>ALL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select>
          </div>
          <h3 className="section-title">Changes</h3>
          <div className="change-list">{rows.map((row) => <button data-testid="change-row" key={row.id} className={`change-row ${row.id === selected ? "active" : ""}`} onClick={() => setSelected(row.id)}><span>{row.external_id}</span><span className={`badge ${row.change_type.toLowerCase()}`}>{row.change_type}</span><span>{data.findings.filter((f) => f.requirement_change_id === row.id).length}</span></button>)}</div>
        </div>
        <aside className="impact-inspector">
        <div className="inspector-header"><h3>{change?.external_id}</h3><ExportButtons projectId={project.id} comparisonId={data.comparison.id} /></div>
        <div className="mb-2 text-xs font-semibold text-slate-600">OLD / NEW word diff</div>
        <pre data-testid="change-diff" className="diff">{change?.text_diff}</pre>
        <h3 className="section-title impact-title">Impacts</h3>
        <ImpactReview findings={findings} />
        </aside>
      </div>
    </section>
  );
}

function ExportButtons({ projectId, comparisonId }: { projectId: string; comparisonId: string }) {
  const exportReport = async (format: "csv" | "pdf", reportType?: "executive" | "audit") => {
    const query = reportType ? `?type=${reportType}` : "";
    const result = await request<{ filename: string; media_type: string; content_base64: string }>(`/projects/${projectId}/comparisons/${comparisonId}/export.${format}${query}`);
    downloadBase64(result.filename, result.media_type, result.content_base64);
  };
  return (
    <div className="export-actions">
      <button data-testid="export-csv" className="export-btn" title="Export CSV" onClick={() => exportReport("csv")}><Download size={15} /><span>CSV</span></button>
      <details className="export-menu">
        <summary data-testid="export-report" className="export-btn"><Download size={15} /><span>Export Report</span></summary>
        <div className="export-menu-panel">
          <button data-testid="export-executive-pdf" type="button" onClick={() => exportReport("pdf", "executive")}>
            <strong>Executive Report</strong>
            <span>Concise stakeholder report focused on key changes, high-impact findings, and review status.</span>
          </button>
          <button data-testid="export-audit-pdf" type="button" onClick={() => exportReport("pdf", "audit")}>
            <strong>Full Audit Report</strong>
            <span>Complete comparison record containing every impact finding and its supporting evidence.</span>
          </button>
        </div>
      </details>
    </div>
  );
}

function ImpactReview({ findings }: { findings: Finding[] }) {
  const queryClient = useQueryClient();
  const [notes, setNotes] = useState<Record<string, string>>({});
  const review = useMutation({ mutationFn: ({ id, payload }: { id: string; payload: Record<string, string> }) => request(`/findings/${id}`, { method: "PATCH", body: JSON.stringify(payload) }), onSuccess: () => queryClient.invalidateQueries() });
  return <div className="finding-stack">{findings.map((finding, index) => <div data-testid="impact-finding" className="finding" key={finding.id}><div className="finding-head"><strong>{finding.impacted_requirement_external_id}</strong><span className={`badge ${finding.severity.toLowerCase()}`}>{finding.severity}</span></div><p>{finding.reason}</p><div className="finding-meta"><span>Confidence {(finding.confidence * 100).toFixed(0)}%</span><span>{finding.detection_method}</span></div><div className="finding-actions"><button data-testid={index === 0 ? "confirm-finding" : undefined} className="small-btn" onClick={() => review.mutate({ id: finding.id, payload: { review_status: "CONFIRMED" } })}>Confirm</button><button data-testid={index === 1 ? "dismiss-finding" : undefined} className="small-btn" onClick={() => review.mutate({ id: finding.id, payload: { review_status: "DISMISSED" } })}>Dismiss</button><select data-testid={index === 0 ? "severity-override" : undefined} className="small-btn" value={finding.severity} onChange={(e) => review.mutate({ id: finding.id, payload: { severity: e.target.value } })}><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select><input data-testid={index === 0 ? "reviewer-note" : undefined} className="field note-field" placeholder="Reviewer note" value={notes[finding.id] ?? finding.reviewer_note ?? ""} onChange={(e) => setNotes({ ...notes, [finding.id]: e.target.value })} /><button data-testid={index === 0 ? "save-note" : undefined} className="small-btn" onClick={(e) => { const input = e.currentTarget.parentElement?.querySelector(".note-field"); const reviewerNote = input instanceof globalThis.HTMLInputElement ? input.value : ""; review.mutate({ id: finding.id, payload: { reviewer_note: reviewerNote } }); }}>Save note</button><span>{finding.review_status}</span></div></div>)}</div>;
}

const root = document.getElementById("root");
if (root) {
  ReactDOM.createRoot(root).render(<App />);
}
