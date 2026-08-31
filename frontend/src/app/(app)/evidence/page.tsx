"use client";

import { AnalysisState, ModuleHeader } from "@/components/analysis-state";
import { useCallback, useEffect, useState } from "react";
import { caseApi, openCitation } from "@/lib/api";
import { notifyAnalysisUpdated, useCurrentAnalysis } from "@/lib/use-current-analysis";
import { useCurrentCase } from "@/lib/use-current-case";

export default function ScientificEvidencePage() {
  const { analysis, loading, error } = useCurrentAnalysis();
  const currentCase = useCurrentCase();
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [documents, setDocuments] = useState<Array<{ id: number; filename: string; sha256: string; status: string; page_count: number; chunk_count: number; size_bytes: number; embedding_provider?: string | null; embedding_model?: string | null; embedding_revision?: string | null }>>([]);
  const [jobs, setJobs] = useState<Array<{ id: number; status: string; embedding_model: string; embedding_revision: string }>>([]);
  const [sourceSnapshots, setSourceSnapshots] = useState<Array<{ id: number; source_id: string; status: string; checked_at: string }>>([]);
  const [processing, setProcessing] = useState(false);
  const evidence = analysis?.result.scientific_evidence;
  const retrieval = analysis?.result.evidence_retrieval;
  const claimGraph = analysis?.result.claim_evidence_graph;
  const studies = analysis?.result.case_specific_analysis?.scientific_studies;

  const refreshDocuments = useCallback(async () => {
    if (!currentCase.backendId) return;
    try { setDocuments(await caseApi.documents(currentCase.backendId)); } catch { setDocuments([]); }
  }, [currentCase.backendId]);

  const refreshJobs = useCallback(async () => {
    if (!currentCase.backendId) return;
    try { setJobs(await caseApi.reindexJobs(currentCase.backendId)); } catch { setJobs([]); }
  }, [currentCase.backendId]);

  const refreshSourceSnapshots = useCallback(async () => {
    try { setSourceSnapshots((await caseApi.sourceChanges()).snapshots); } catch { setSourceSnapshots([]); }
  }, []);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => {
      void Promise.all([refreshDocuments(), refreshJobs(), refreshSourceSnapshots()]);
    }, 0);
    return () => window.clearTimeout(initialLoad);
  }, [refreshDocuments, refreshJobs, refreshSourceSnapshots]);

  async function reindex() {
    if (!currentCase.backendId) return;
    setProcessing(true);
    setUploadStatus("Queueing a versioned evidence reindex…");
    try {
      const job = await caseApi.reindex(currentCase.backendId);
      setUploadStatus(`Reindex job ${job.id} queued · ${job.embedding_model} · ${job.embedding_revision}`);
      await refreshJobs();
    } catch (caught) {
      setUploadStatus(caught instanceof Error ? caught.message : "Reindex failed.");
    } finally {
      setProcessing(false);
    }
  }

  async function upload(file: File) {
    if (!currentCase.backendId) return;
    setProcessing(true);
    setUploadStatus("Extracting, chunking and indexing evidence…");
    try {
      const document = await caseApi.uploadDocument(currentCase.backendId, file);
      setUploadStatus(`Indexed ${document.filename} · ${document.page_count} page(s) · ${document.chunk_count} searchable passage(s) · ${document.sha256.slice(0, 12)}…`);
      await caseApi.analyze(currentCase.backendId);
      notifyAnalysisUpdated();
      await refreshDocuments();
    } catch (caught) {
      setUploadStatus(caught instanceof Error ? caught.message : "Upload failed.");
    } finally {
      setProcessing(false);
    }
  }
  return (
    <div className="py-8 md:py-10">
      <ModuleHeader eyebrow="Scientific Evidence" title="What does the evidence actually establish?" description="Traditional use, modern research, safety and confidence remain separate so a historic-use record is never presented as clinical proof." />
      {!evidence ? <AnalysisState loading={loading} error={error} /> : (
        <>
          <section className="mt-8 rounded-2xl border border-warm/30 bg-warm-subtle p-5"><p className="text-sm font-semibold text-warm">Important evidence boundary</p><p className="mt-2 text-base leading-6 text-ink">{evidence.notice}</p></section>
          <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <EvidenceCard number="01" title="Traditional-use claims" status={evidence.traditional_use.status} summary={evidence.traditional_use.summary} confidence={evidence.traditional_use.confidence} />
            <EvidenceCard number="02" title="Modern scientific evidence" status={evidence.modern_science.status} summary={evidence.modern_science.summary} confidence={evidence.modern_science.confidence} />
            <EvidenceCard number="03" title="Safety information" status={evidence.safety.status} summary={evidence.safety.summary} confidence={evidence.safety.confidence} />
            <div className="rounded-2xl border border-border bg-[#16212B] p-6 text-white"><p className="font-mono text-[10px] uppercase tracking-[0.16em] text-white/50">04 / Evidence confidence</p><p className="mt-5 text-3xl font-semibold">{Math.round(evidence.confidence.score * 100)}%</p><p className="mt-2 text-sm font-medium">{evidence.confidence.label}</p><p className="mt-3 text-xs leading-5 text-white/60">{evidence.confidence.basis}</p></div>
          </section>
          {studies && <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8"><div className="flex flex-col justify-between gap-5 md:flex-row md:items-start"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Structured study appraisal</p><h2 className="mt-2 text-2xl font-semibold">Population, dose, endpoints and limitations</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-ink-muted">Query: {studies.query}. {studies.notice}</p></div><a href={studies.search_url} target="_blank" rel="noreferrer" className="rounded-xl border border-accent px-4 py-2 text-xs font-semibold text-accent">Open PubMed search ↗</a></div>{studies.records.length === 0 ? <div className="mt-6 rounded-2xl border border-warm/30 bg-warm-subtle p-5"><p className="text-sm font-semibold text-warm">No study record was retrieved for this exact query.</p><p className="mt-2 text-xs leading-5 text-ink-muted">Do not substitute ingredient-level popularity for product-specific evidence. Refine the query or upload the relevant full text.</p></div> : <div className="mt-6 space-y-4">{studies.records.map((study, index) => <article key={`${study.pmid ?? study.locator}-${index}`} className="rounded-2xl border border-border bg-background p-5"><div className="flex flex-col justify-between gap-2 md:flex-row"><div><p className="text-sm font-semibold">{study.title}</p><p className="mt-1 text-xs text-ink-muted">{study.journal} · {study.publication_date} · {study.pmid ? `PMID ${study.pmid}` : study.locator ?? study.source_status}</p></div><a href={study.url} target="_blank" rel="noreferrer" className="text-xs font-semibold text-accent">Source ↗</a></div><div className="mt-5 grid gap-3 md:grid-cols-2"><StudyFact label="Population" value={study.population} /><StudyFact label="Dose / exposure" value={study.dose} /><StudyFact label="Endpoints / results" value={study.endpoints} /><StudyFact label="Limitations" value={study.limitations} /></div></article>)}</div>}</section>}
          <section className="mt-10 grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
            <div className="rounded-3xl border border-border bg-surface p-6"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Evidence gaps</p><h2 className="mt-2 text-2xl font-semibold">What is still missing?</h2><div className="mt-5 space-y-3">{evidence.gaps.map((gap, index) => <div key={gap} className="flex gap-3 rounded-xl border border-border bg-background p-4"><span className="font-mono text-[10px] text-accent">{String(index + 1).padStart(2, "0")}</span><p className="text-sm">{gap}</p></div>)}</div></div>
            <div className="rounded-3xl border border-border bg-surface p-6"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Evidence references</p><h2 className="mt-2 text-2xl font-semibold">Sources supporting this screening</h2><div className="mt-5 space-y-3">{evidence.citations.map((source) => <button type="button" onClick={() => void openCitation(source)} key={source.id} className="block w-full rounded-xl border border-border bg-background p-4 text-left transition hover:border-accent"><div className="flex justify-between gap-4"><p className="text-sm font-semibold">{source.title}</p><span className="font-mono text-[9px] text-ink-muted">{source.locator ?? source.jurisdiction}</span></div><p className="mt-2 text-xs text-ink-muted">{source.authority} · {source.support_status}</p><p className="mt-3 text-xs leading-5 text-ink-muted">{source.excerpt}</p></button>)}</div></div>
          </section>
          {claimGraph && <section className="mt-8 rounded-3xl border border-border bg-surface p-6"><div className="flex flex-col justify-between gap-5 md:flex-row md:items-end"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Claim-to-evidence graph</p><h2 className="mt-2 text-2xl font-semibold">Trace every screening claim.</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-ink-muted">{claimGraph.notice}</p></div><div className="rounded-2xl bg-[#16212B] px-6 py-4 text-white"><p className="text-3xl font-semibold">{Math.round(claimGraph.summary.coverage * 100)}%</p><p className="mt-1 text-[10px] uppercase tracking-[0.16em] text-white/50">traceability coverage</p></div></div><div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{claimGraph.claims.slice(0, 9).map((claim) => { const links = claimGraph.edges.filter((edge) => edge.target === claim.id).length; return <article key={claim.id} className="rounded-2xl border border-border bg-background p-4"><div className="flex items-center justify-between gap-3"><span className="font-mono text-[9px] uppercase text-accent">{claim.claim_type}</span><span className="font-mono text-[9px] uppercase text-ink-muted">{links} source link{links === 1 ? "" : "s"}</span></div><p className="mt-3 line-clamp-3 text-xs leading-5 text-ink">{claim.text}</p><p className="mt-3 text-[10px] font-semibold uppercase text-ink-muted">{claim.status}</p></article>; })}</div></section>}
          <section className="mt-8 rounded-3xl border border-border bg-[#16212B] p-6 text-white"><div className="flex flex-col justify-between gap-5 md:flex-row md:items-end"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#9BD0C0]">Authoritative-source change monitor</p><h2 className="mt-2 text-2xl font-semibold">Know when the legal baseline moves.</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-white/60">Scheduled snapshots use content hashes and HTTP validators. Every detected change is held for qualified human review before the corpus version changes.</p></div><div className="grid grid-cols-2 gap-3"><DarkMetric label="Snapshots" value={sourceSnapshots.length} /><DarkMetric label="Change flags" value={sourceSnapshots.filter((item) => item.status === "changed").length} /></div></div>{sourceSnapshots.length === 0 && <p className="mt-5 rounded-2xl border border-white/10 bg-white/5 p-4 text-xs text-white/55">No source snapshots yet. An administrator or deployment scheduler must run the controlled monitor.</p>}</section>
          <section className="mt-8 rounded-3xl border border-border bg-surface p-6"><div className="flex flex-col justify-between gap-4 md:flex-row md:items-center"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Case evidence vault</p><h2 className="mt-2 text-xl font-semibold">Attach, embed and rerank controlled evidence</h2><p className="mt-2 text-xs text-ink-muted">PDF, TXT or DOCX · maximum 10 MB · OCR · SHA-256 integrity · page/chunk lineage · versioned embeddings</p></div><div className="flex flex-wrap gap-3"><button type="button" disabled={processing || (retrieval?.indexed_document_count ?? documents.length) === 0} onClick={() => void reindex()} className="rounded-xl border border-accent px-5 py-3 text-sm font-semibold text-accent disabled:cursor-not-allowed disabled:opacity-40">Reindex evidence</button><label className={`rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white ${processing ? "cursor-wait opacity-50" : "cursor-pointer"}`}><input disabled={processing} type="file" accept=".pdf,.txt,.docx" className="sr-only" onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload(file); event.currentTarget.value = ""; }} />{processing ? "Processing…" : "Attach evidence"}</label></div></div>{uploadStatus && <p role="status" className="mt-4 rounded-xl border border-border bg-background p-3 text-xs text-ink-muted">{uploadStatus}</p>}<div className="mt-5 grid gap-3 md:grid-cols-4"><VaultMetric label="Indexed documents" value={retrieval?.indexed_document_count ?? documents.filter((item) => item.status === "indexed").length} /><VaultMetric label="Searchable passages" value={retrieval?.chunk_count ?? documents.reduce((sum, item) => sum + item.chunk_count, 0)} /><VaultMetric label="Prefetch candidates" value={retrieval?.prefetch_limit ?? 0} /><VaultMetric label="Retrieved this run" value={retrieval?.retrieved_passage_count ?? 0} /></div>{retrieval && <div className="mt-5 grid gap-3 rounded-2xl border border-border bg-background p-4 md:grid-cols-3"><PipelineFact label="Embedding" value={`${retrieval.embedding_model} · ${retrieval.embedding_revision}`} /><PipelineFact label="Reranker" value={retrieval.reranker} /><PipelineFact label="Pipeline" value={retrieval.method} /></div>}{jobs.length > 0 && <p className="mt-4 text-xs text-ink-muted">Latest reindex job: <span className="font-semibold text-ink">#{jobs[0].id} · {jobs[0].status}</span></p>}{documents.length > 0 && <div className="mt-5 space-y-2">{documents.map((document) => <div key={document.id} className="flex flex-col gap-3 rounded-xl border border-border bg-background p-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-sm font-semibold">{document.filename}</p><p className="mt-1 font-mono text-[9px] uppercase text-ink-muted">{document.status} · {document.page_count} page(s) · {document.chunk_count} passages · SHA {document.sha256.slice(0, 12)}…</p><p className="mt-1 text-[10px] text-ink-muted">{document.embedding_model ?? "embedding pending"} · {document.embedding_revision ?? "unversioned"}</p></div><button type="button" onClick={() => { if (!currentCase.backendId) return; void caseApi.deleteDocument(currentCase.backendId, document.id).then(async () => { await caseApi.analyze(currentCase.backendId!); notifyAnalysisUpdated(); await refreshDocuments(); }); }} className="text-xs font-semibold text-danger hover:underline">Remove</button></div>)}</div>}</section>
        </>
      )}
    </div>
  );
}

function EvidenceCard({ number, title, status, summary, confidence }: { number: string; title: string; status: string; summary: string; confidence: number }) {
  return <article className="rounded-2xl border border-border bg-surface p-6"><div className="flex items-center justify-between"><span className="font-mono text-[10px] text-accent">{number}</span><span className="rounded-full bg-accent-subtle px-2 py-1 font-mono text-[9px] uppercase text-accent">{status.replaceAll("_", " ")}</span></div><h2 className="mt-5 text-lg font-semibold">{title}</h2><p className="mt-3 text-sm leading-6 text-ink-muted">{summary}</p><div className="mt-5 h-1.5 rounded-full bg-accent-subtle"><div className="h-full rounded-full bg-accent" style={{ width: `${confidence * 100}%` }} /></div><p className="mt-2 font-mono text-[9px] text-ink-muted">{Math.round(confidence * 100)}% screening confidence</p></article>;
}

function VaultMetric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl border border-border bg-background p-4"><p className="text-2xl font-semibold text-accent">{value}</p><p className="mt-1 text-xs text-ink-muted">{label}</p></div>;
}

function PipelineFact({ label, value }: { label: string; value: string }) {
  return <div><p className="font-mono text-[9px] uppercase tracking-[0.14em] text-accent">{label}</p><p className="mt-2 text-xs leading-5 text-ink-muted">{value}</p></div>;
}

function DarkMetric({ label, value }: { label: string; value: number }) {
  return <div className="min-w-28 rounded-2xl border border-white/10 bg-white/5 px-4 py-3"><p className="text-2xl font-semibold text-[#9BD0C0]">{value}</p><p className="mt-1 text-[9px] uppercase tracking-[0.15em] text-white/45">{label}</p></div>;
}

function StudyFact({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-border bg-surface p-4"><p className="font-mono text-[9px] uppercase tracking-[0.14em] text-accent">{label}</p><p className="mt-2 text-xs leading-5 text-ink-muted">{value}</p></div>;
}
