import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileUp, Plus, RefreshCw, ShieldCheck } from "lucide-react";
import "./styles.css";

const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
const client = new QueryClient();

type Project = { id: string; name: string; description: string; requirements_count: number; changed_requirements: number; unresolved_findings: number };
type ImportBatch = { id: string; filename: string; version_label: string; row_count: number; status: string };
type Comparison = { id: string; summary_json: Record<string, number>; status: string };
type Change = { id: string; external_id: string; change_type: string; changed_fields: Record<string, unknown>; text_diff: string };
type Finding = { id: string; requirement_change_id: string; impacted_requirement_external_id: string; severity: string; confidence: number; detection_method: string; reason: string; review_status: string; reviewer_note?: string };

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { ...options, headers: { "content-type": "application/json", ...(options.headers || {}) } });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: { message: response.statusText } }));
    throw new Error(error.error?.message || "Radar could not complete the request.");
  }
  return response.json();
}

function downloadBase64(name: string, mediaType: string, content: string) {
  const link = document.createElement("a");
  link.href = `data:${mediaType};base64,${content}`;
  link.download = name;
  link.click();
}

function App() {
  return <QueryClientProvider client={client}><RadarApp /></QueryClientProvider>;
}

function RadarApp() {
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const projects = useQuery({ queryKey: ["projects"], queryFn: () => request<Project[]>("/projects") });
  const active = projects.data?.find((p) => p.id === activeProjectId) || projects.data?.[0];
  return (
    <main className="min-h-screen bg-white text-radar-ink">
      <header className="border-b border-radar-line px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold">Requirements Impact Radar</h1>
            <p className="text-sm text-slate-600">Know what a requirement change affects before it becomes a defect.</p>
          </div>
          <span className="inline-flex items-center gap-2 rounded border border-radar-line px-3 py-2 text-sm"><ShieldCheck size={16} /> Dev auth active</span>
        </div>
      </header>
      <section className="grid grid-cols-[280px_1fr] min-h-[calc(100vh-73px)]">
        <aside className="border-r border-radar-line bg-radar-panel p-4">
          <ProjectCreator />
          <div className="mt-4 space-y-2">
            {projects.data?.map((project) => (
              <button key={project.id} className={`w-full rounded border px-3 py-2 text-left text-sm ${active?.id === project.id ? "border-blue-500 bg-white" : "border-radar-line bg-transparent"}`} onClick={() => setActiveProjectId(project.id)}>
                <div className="font-medium">{project.name}</div>
                <div className="text-xs text-slate-600">{project.changed_requirements} changed · {project.unresolved_findings} unreviewed</div>
              </button>
            ))}
          </div>
        </aside>
        <section className="p-5">{active ? <ProjectWorkspace project={active} /> : <EmptyState />}</section>
      </section>
    </main>
  );
}

function ProjectCreator() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const mutation = useMutation({ mutationFn: () => request<Project>("/projects", { method: "POST", body: JSON.stringify({ name, description: "" }) }), onSuccess: () => { setName(""); queryClient.invalidateQueries({ queryKey: ["projects"] }); } });
  return <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (name.trim()) mutation.mutate(); }}><input data-testid="project-name" className="min-w-0 flex-1 rounded border border-radar-line px-2 py-2 text-sm" placeholder="New project" value={name} onChange={(e) => setName(e.target.value)} /><button data-testid="create-project" className="icon-btn" title="New Project"><Plus size={16} /></button></form>;
}

function EmptyState() {
  return <div className="flex h-full items-center justify-center text-sm text-slate-600">Create a project to upload your first requirements register.</div>;
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
  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div><h2 className="text-lg font-semibold">{project.name}</h2><p className="text-sm text-slate-600">Upload two CSV versions, compare them, then review likely impacts.</p></div>
        <button data-testid="compare-versions" className="btn" disabled={(detail.data?.imports.length || 0) < 2} onClick={() => compareMutation.mutate()}><RefreshCw size={16} /> Compare versions</button>
      </div>
      <div className="grid grid-cols-[420px_1fr] gap-5">
        <section className="panel">
          <h3 className="section-title"><FileUp size={16} /> Upload New Version</h3>
          <input key={uploadKey} data-testid="csv-upload" type="file" accept=".csv" className="text-sm" onInput={(e) => handleSelectedFile(e.currentTarget.files?.[0])} onChange={(e) => handleSelectedFile(e.currentTarget.files?.[0])} />
          <input data-testid="version-label" className="field" value={versionLabel} onChange={(e) => setVersionLabel(e.target.value)} placeholder="Version label" />
          <MappingEditor mapping={mapping} setMapping={setMapping} />
          <div data-testid="validation-messages" className="space-y-1 text-xs text-slate-600">{validationMessages.map((message) => <div key={message}>{message}</div>)}</div>
          {importMutation.error ? <div className="text-xs text-red-700">{importMutation.error.message}</div> : null}
          <button data-testid="import-csv" className="btn w-full justify-center" disabled={!csvText || importMutation.isPending} onClick={() => importMutation.mutate()}>Import CSV</button>
        </section>
        <section className="panel">
          <h3 className="section-title">Imports</h3>
          <div className="table">
            {(detail.data?.imports || []).map((item) => <div className="tr" key={item.id}><span>{item.version_label}</span><span>{item.filename}</span><span>{item.row_count} rows</span><span>{item.status}</span></div>)}
          </div>
        </section>
      </div>
      {comparison.data ? <ComparisonResults projectId={project.id} data={comparison.data} /> : <ComparisonHistory projectId={project.id} comparisons={detail.data?.comparisons || []} setComparisonId={setComparisonId} />}
    </div>
  );
}

function MappingEditor({ mapping, setMapping }: { mapping: Record<string, string>; setMapping: (m: Record<string, string>) => void }) {
  return <div className="grid grid-cols-2 gap-2 text-xs">{Object.keys(mapping).map((field) => <label key={field} className="space-y-1"><span>{field}</span><input className="field" value={mapping[field]} onChange={(e) => setMapping({ ...mapping, [field]: e.target.value })} /></label>)}</div>;
}

function ComparisonHistory({ projectId, comparisons, setComparisonId }: { projectId: string; comparisons: Comparison[]; setComparisonId: (id: string) => void }) {
  return <section className="panel"><h3 className="section-title">Comparison History</h3>{comparisons.map((comparison) => <button className="history-row" key={comparison.id} onClick={() => setComparisonId(comparison.id)}>Changed {comparison.summary_json.MODIFIED || 0} · Added {comparison.summary_json.ADDED || 0} · Removed {comparison.summary_json.REMOVED || 0} · Impacts {comparison.summary_json.impact_findings || 0}</button>)}</section>;
}

function ComparisonResults({ projectId, data }: { projectId: string; data: { comparison: Comparison; changes: Change[]; findings: Finding[] } }) {
  const [selected, setSelected] = useState(data.changes.find((c) => c.change_type !== "UNCHANGED")?.id || data.changes[0]?.id);
  const [changeTypeFilter, setChangeTypeFilter] = useState("ALL");
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const change = data.changes.find((c) => c.id === selected);
  const findings = data.findings.filter((f) => f.requirement_change_id === selected && (severityFilter === "ALL" || f.severity === severityFilter));
  const rows = data.changes.filter((c) => c.change_type !== "UNCHANGED" && (changeTypeFilter === "ALL" || c.change_type === changeTypeFilter));
  return (
    <section className="grid grid-cols-[1fr_440px] gap-5">
      <div className="panel">
        <div className="summary-grid">
          {["MODIFIED", "ADDED", "REMOVED", "impact_findings", "high_impact"].map((key) => <div key={key}><span>{key.replace("_", " ")}</span><strong>{data.comparison.summary_json[key] || 0}</strong></div>)}
        </div>
        <div className="mt-4 flex gap-2">
          <select data-testid="change-filter" className="field max-w-44" value={changeTypeFilter} onChange={(e) => setChangeTypeFilter(e.target.value)}><option>ALL</option><option>MODIFIED</option><option>ADDED</option><option>REMOVED</option></select>
          <select data-testid="severity-filter" className="field max-w-44" value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}><option>ALL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select>
        </div>
        <div className="table mt-4">{rows.map((row) => <button data-testid="change-row" key={row.id} className="tr w-full text-left" onClick={() => setSelected(row.id)}><span>{row.external_id}</span><span className={`badge ${row.change_type.toLowerCase()}`}>{row.change_type}</span><span>{data.findings.filter((f) => f.requirement_change_id === row.id).length} impacts</span></button>)}</div>
      </div>
      <aside className="panel">
        <div className="flex items-center justify-between"><h3 className="section-title">{change?.external_id}</h3><ExportButtons projectId={projectId} comparisonId={data.comparison.id} /></div>
        <div className="mb-2 text-xs font-semibold text-slate-600">OLD / NEW word diff</div>
        <pre data-testid="change-diff" className="diff">{change?.text_diff}</pre>
        <ImpactReview findings={findings} />
      </aside>
    </section>
  );
}

function ExportButtons({ projectId, comparisonId }: { projectId: string; comparisonId: string }) {
  const exportReport = async (format: "csv" | "pdf") => {
    const result = await request<{ filename: string; media_type: string; content_base64: string }>(`/projects/${projectId}/comparisons/${comparisonId}/export.${format}`);
    downloadBase64(result.filename, result.media_type, result.content_base64);
  };
  return <div className="flex gap-2"><button data-testid="export-csv" className="icon-btn" title="Export CSV" onClick={() => exportReport("csv")}><Download size={16} /></button><button data-testid="export-pdf" className="icon-btn" title="Export PDF" onClick={() => exportReport("pdf")}><Download size={16} /></button></div>;
}

function ImpactReview({ findings }: { findings: Finding[] }) {
  const queryClient = useQueryClient();
  const [notes, setNotes] = useState<Record<string, string>>({});
  const review = useMutation({ mutationFn: ({ id, payload }: { id: string; payload: Record<string, string> }) => request(`/findings/${id}`, { method: "PATCH", body: JSON.stringify(payload) }), onSuccess: () => queryClient.invalidateQueries() });
  return <div className="mt-4 space-y-3">{findings.map((finding, index) => <div data-testid="impact-finding" className="finding" key={finding.id}><div className="flex items-center justify-between"><strong>{finding.impacted_requirement_external_id}</strong><span className={`badge ${finding.severity.toLowerCase()}`}>{finding.severity}</span></div><p>{finding.reason}</p><div className="grid grid-cols-2 gap-2 text-xs"><span>Confidence {(finding.confidence * 100).toFixed(0)}%</span><span>{finding.detection_method}</span></div><div className="mt-2 flex flex-wrap gap-2"><button data-testid={index === 0 ? "confirm-finding" : undefined} className="small-btn" onClick={() => review.mutate({ id: finding.id, payload: { review_status: "CONFIRMED" } })}>Confirm</button><button data-testid={index === 1 ? "dismiss-finding" : undefined} className="small-btn" onClick={() => review.mutate({ id: finding.id, payload: { review_status: "DISMISSED" } })}>Dismiss</button><select data-testid={index === 0 ? "severity-override" : undefined} className="small-btn" value={finding.severity} onChange={(e) => review.mutate({ id: finding.id, payload: { severity: e.target.value } })}><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select><input data-testid={index === 0 ? "reviewer-note" : undefined} className="field max-w-44 py-1" placeholder="Reviewer note" value={notes[finding.id] ?? finding.reviewer_note ?? ""} onChange={(e) => setNotes({ ...notes, [finding.id]: e.target.value })} /><button data-testid={index === 0 ? "save-note" : undefined} className="small-btn" onClick={() => review.mutate({ id: finding.id, payload: { reviewer_note: notes[finding.id] || "" } })}>Save note</button><span className="text-xs text-slate-500">{finding.review_status}</span></div></div>)}</div>;
}

ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
