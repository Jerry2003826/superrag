import React, { ChangeEvent, FormEvent, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowRight,
  BookOpen,
  DatabaseZap,
  FileText,
  FlaskConical,
  Loader2,
  Search,
  ShieldCheck,
  UploadCloud
} from "lucide-react";
import "./styles.css";

type RegisteredPaper = {
  paper_id: string;
  study_id: string;
  report_id: string;
  duplicate_kind: string | null;
};

type UploadResult = {
  object_uri: string;
  parsed_id: string;
  parse_status: string;
  chunk_count: number;
  evidence_span_count: number;
  evidence_span_ids: string[];
};

type QueryResult = {
  abstained: boolean;
  block_reasons: string[];
  sufficiency: string;
  sufficiency_reason: string;
  answer: {
    sentences: Array<{
      text: string;
      cited_result_ids: string[];
      cited_evidence_span_ids: string[];
    }>;
    reasons: string[];
  };
  claims: Array<{ claim_text: string; cited_result_ids: string[] }>;
  verification: Array<{ verdict: string; reason: string | null }>;
};

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

function App() {
  const [paper, setPaper] = useState<RegisteredPaper | null>(null);
  const [upload, setUpload] = useState<UploadResult | null>(null);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState("Ready");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    title: "Compound X reduces IL-6 in APP/PS1 mice",
    doi: `10.0000/local-${Date.now()}`,
    authors: "Li, Wang",
    year: "2026",
    journal: "Local Evidence Review",
    abstract: "Compound X reduced IL-6 in a mouse model.",
    query: "Does Compound X reduce IL-6 in animal studies?"
  });

  const evidenceId = upload?.evidence_span_ids?.[0] ?? "E00000001";

  const progress = useMemo(() => {
    return [
      { label: "Paper", done: Boolean(paper) },
      { label: "Document", done: Boolean(upload) },
      { label: "Evidence", done: Boolean(queryResult) }
    ];
  }, [paper, upload, queryResult]);

  function updateForm(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function registerPaper(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("register");
    setError(null);
    try {
      const payload = {
        title: form.title,
        doi: form.doi,
        authors: form.authors.split(",").map((author) => author.trim()).filter(Boolean),
        year: Number(form.year),
        journal: form.journal,
        abstract: form.abstract,
        source_database: "frontend",
        source_url: "http://localhost/frontend"
      };
      const result = await requestJson<RegisteredPaper>("/papers/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      setPaper(result);
      setStatus(`Registered ${result.paper_id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Registration failed");
    } finally {
      setBusy(null);
    }
  }

  async function uploadDocument() {
    if (!paper || !selectedFile) return;
    setBusy("upload");
    setError(null);
    try {
      const data = new FormData();
      data.append("source_format", selectedFile.name.toLowerCase().endsWith(".pdf") ? "PDF" : selectedFile.name.toLowerCase().endsWith(".txt") ? "TEXT" : "JATS_XML");
      data.append("document_id", selectedFile.name);
      data.append("file", selectedFile);
      const result = await requestJson<UploadResult>(`/papers/${paper.paper_id}/documents`, {
        method: "POST",
        body: data
      });
      setUpload(result);
      setStatus(`Parsed ${result.chunk_count} chunks`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Upload failed");
    } finally {
      setBusy(null);
    }
  }

  async function runSampleExtraction() {
    if (!paper) return;
    setBusy("extract");
    setError(null);
    try {
      await requestJson(`/extraction/${paper.paper_id}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          llm_output: {
            paper_id: paper.paper_id,
            extraction_status: "unverified",
            results: [
              {
                result_id: "R00000001",
                study_id: paper.study_id,
                paper_id: paper.paper_id,
                study_type: "animal",
                population_or_model: "APP/PS1 mouse model",
                species: "mouse",
                cell_line: null,
                intervention: "Compound X",
                comparator: "vehicle",
                outcome: "IL-6",
                assay: "ELISA",
                direction: "decreased",
                effect_size: "32%",
                p_value: "p=0.01",
                confidence_interval: null,
                sample_size: "n=12",
                dose: "10 mg/kg",
                duration: "8 weeks",
                unit: "pg/mL",
                scope: "animal",
                evidence_span_id: evidenceId,
                extraction_status: "unverified"
              }
            ]
          }
        })
      });
      setStatus("Extraction persisted");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Extraction failed");
    } finally {
      setBusy(null);
    }
  }

  async function runQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("query");
    setError(null);
    try {
      const result = await requestJson<QueryResult>("/query/full", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: form.query, query_scope: "animal" })
      });
      setQueryResult(result);
      setStatus(result.abstained ? "Answer abstained" : "Evidence answer ready");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Query failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="min-h-screen bg-mist text-ink">
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[248px_1fr]">
        <aside className="border-r border-line bg-white px-5 py-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal text-white">
              <FlaskConical size={21} />
            </div>
            <div>
              <p className="text-sm font-semibold">Evidence Bio RAG</p>
              <p className="text-xs text-slate">Single-node review engine</p>
            </div>
          </div>
          <nav className="mt-8 space-y-1">
            {[
              { label: "Register", href: "#register", icon: BookOpen },
              { label: "Upload", href: "#upload", icon: UploadCloud },
              { label: "Extract", href: "#extract", icon: DatabaseZap },
              { label: "Query", href: "#query", icon: Search },
              { label: "Verify", href: "#query", icon: ShieldCheck }
            ].map(({ label, href, icon: Icon }) => (
              <a key={label} className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate hover:bg-mist hover:text-ink" href={href}>
                {React.createElement(Icon as typeof BookOpen, { size: 17 })}
                {label}
              </a>
            ))}
          </nav>
          <div className="mt-8 rounded-lg border border-line bg-mist p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate">Runtime</p>
            <p className="mt-2 text-sm font-semibold">{status}</p>
            <div className="mt-4 space-y-2">
              {progress.map((item) => (
                <div key={item.label} className="flex items-center justify-between text-xs">
                  <span>{item.label}</span>
                  <span className={item.done ? "text-teal" : "text-slate"}>{item.done ? "ready" : "pending"}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>

        <section className="p-5 md:p-8">
          <header className="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
            <div>
              <p className="flex items-center gap-2 text-sm font-medium text-teal">
                <Activity size={16} /> Evidence-grounded systematic review
              </p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">
                Literature intake, extraction, and cited answers in one workspace.
              </h1>
            </div>
            <a className="inline-flex items-center gap-2 rounded-lg border border-line bg-white px-4 py-2 text-sm font-medium shadow-soft" href={`${apiBase}/docs`} target="_blank">
              API docs <ArrowRight size={16} />
            </a>
          </header>

          {error && <div className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

          <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
            <div className="space-y-5">
              <form id="register" onSubmit={registerPaper} className="rounded-lg border border-line bg-white p-5 shadow-soft">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Register literature</h2>
                  {paper && <span className="rounded-full bg-teal/10 px-3 py-1 text-xs font-medium text-teal">{paper.paper_id}</span>}
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <Input label="Title" value={form.title} onChange={(value) => updateForm("title", value)} className="md:col-span-2" />
                  <Input label="DOI" value={form.doi} onChange={(value) => updateForm("doi", value)} />
                  <Input label="Year" value={form.year} onChange={(value) => updateForm("year", value)} />
                  <Input label="Authors" value={form.authors} onChange={(value) => updateForm("authors", value)} />
                  <Input label="Journal" value={form.journal} onChange={(value) => updateForm("journal", value)} />
                </div>
                <label className="mt-3 block text-sm font-medium">
                  Abstract
                  <textarea className="mt-1 min-h-20 w-full rounded-lg border border-line px-3 py-2 text-sm outline-none focus:border-teal" value={form.abstract} onChange={(event) => updateForm("abstract", event.target.value)} />
                </label>
                <button className="mt-4 inline-flex items-center gap-2 rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={busy === "register"}>
                  {busy === "register" && <Loader2 className="animate-spin" size={16} />} Register paper
                </button>
              </form>

              <section id="upload" className="rounded-lg border border-line bg-white p-5 shadow-soft">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Upload source document</h2>
                  {upload && <span className="rounded-full bg-amber/10 px-3 py-1 text-xs font-medium text-amber">{upload.parse_status}</span>}
                </div>
                <label className="flex min-h-36 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-line bg-mist px-4 py-6 text-center hover:border-teal">
                  <FileText className="mb-3 text-teal" />
              <span className="text-sm font-medium">{selectedFile ? selectedFile.name : "PDF, XML, or TXT source"}</span>
              <span className="mt-1 text-xs text-slate">MinIO object, parsed chunks, evidence spans</span>
                  <input type="file" className="hidden" accept=".pdf,.xml,.txt" onChange={(event: ChangeEvent<HTMLInputElement>) => setSelectedFile(event.target.files?.[0] ?? null)} />
                </label>
                <button className="mt-4 inline-flex items-center gap-2 rounded-lg bg-teal px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={!paper || !selectedFile || busy === "upload"} onClick={uploadDocument}>
                  {busy === "upload" && <Loader2 className="animate-spin" size={16} />} Upload and parse
                </button>
                {upload && (
                  <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
                    <Metric label="Chunks" value={upload.chunk_count} />
                    <Metric label="Evidence" value={upload.evidence_span_count} />
                    <Metric label="Parsed" value={upload.parsed_id} />
                  </div>
                )}
              </section>

              <section id="extract" className="rounded-lg border border-line bg-white p-5 shadow-soft">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Extraction</h2>
                  <span className="text-xs text-slate">Structured results</span>
                </div>
                <button className="mt-4 inline-flex items-center gap-2 rounded-lg border border-line bg-white px-4 py-2 text-sm font-semibold disabled:opacity-50" disabled={!paper || !upload || busy === "extract"} onClick={runSampleExtraction}>
                  {busy === "extract" && <Loader2 className="animate-spin" size={16} />} Persist sample extraction
                </button>
              </section>
            </div>

            <aside id="query" className="rounded-lg border border-line bg-white p-5 shadow-soft">
              <h2 className="text-lg font-semibold">Evidence answer</h2>
              <form onSubmit={runQuery} className="mt-4 flex gap-2">
                <input className="min-w-0 flex-1 rounded-lg border border-line px-3 py-2 text-sm outline-none focus:border-teal" value={form.query} onChange={(event) => updateForm("query", event.target.value)} />
                <button className="inline-flex items-center gap-2 rounded-lg bg-teal px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={busy === "query"}>
                  {busy === "query" ? <Loader2 className="animate-spin" size={16} /> : <Search size={16} />} Query
                </button>
              </form>
              <div className="mt-5 rounded-lg border border-line bg-mist p-4">
                {!queryResult ? (
                  <p className="text-sm text-slate">Cited answer sentences, claims, and verification verdicts appear here.</p>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="rounded-full bg-white px-3 py-1 text-xs font-medium">{queryResult.sufficiency}</span>
                      <span className={queryResult.abstained ? "text-amber" : "text-teal"}>{queryResult.abstained ? "abstained" : "answered"}</span>
                    </div>
                    {queryResult.answer.sentences.map((sentence, index) => (
                      <article key={index} className="rounded-lg bg-white p-4">
                        <p className="text-sm leading-6">{sentence.text}</p>
                        <p className="mt-3 text-xs text-slate">
                          Results: {sentence.cited_result_ids.join(", ")} · Spans: {sentence.cited_evidence_span_ids.join(", ")}
                        </p>
                      </article>
                    ))}
                    {queryResult.verification.map((verdict, index) => (
                      <details key={index} className="rounded-lg bg-white p-3 text-sm">
                        <summary className="cursor-pointer font-medium">{verdict.verdict}</summary>
                        <p className="mt-2 text-slate">{verdict.reason}</p>
                      </details>
                    ))}
                  </div>
                )}
              </div>
            </aside>
          </div>
        </section>
      </div>
    </main>
  );
}

function Input({ label, value, onChange, className = "" }: { label: string; value: string; onChange: (value: string) => void; className?: string }) {
  return (
    <label className={`block text-sm font-medium ${className}`}>
      {label}
      <input className="mt-1 w-full rounded-lg border border-line px-3 py-2 text-sm outline-none focus:border-teal" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-line bg-mist p-3">
      <p className="text-xs text-slate">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold">{value}</p>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
