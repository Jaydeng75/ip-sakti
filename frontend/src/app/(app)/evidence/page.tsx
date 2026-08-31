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
  const [documents, setDocuments] = useState<Array<{ id: number; filename: string; sha256: string; status: string; page_count: number; chunk_count: number; size_bytes: number }>>([]);
  const [processing, setProcessing] = useState(false);
  const evidence = analysis?.result.scientific_evidence;
  const retrieval = analysis?.result.evidence_retrieval;

  const refreshDocuments = useCallback(async () => {
    if (!currentCase.backendId) return;
    try { setDocuments(await caseApi.documents(currentCase.backendId)); } catch { setDocuments([]); }
  }, [currentCase.backendId]);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => void refreshDocuments(), 0);
    return () => window.clearTimeout(initialLoad);
  }, [refreshDocuments]);

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
          <section className="mt-10 grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
            <div className="rounded-3xl border border-border bg-surface p-6"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Evidence gaps</p><h2 className="mt-2 text-2xl font-semibold">What is still missing?</h2><div className="mt-5 space-y-3">{evidence.gaps.map((gap, index) => <div key={gap} className="flex gap-3 rounded-xl border border-border bg-background p-4"><span className="font-mono text-[10px] text-accent">{String(index + 1).padStart(2, "0")}</span><p className="text-sm">{gap}</p></div>)}</div></div>
            <div className="rounded-3xl border border-border bg-surface p-6"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Evidence references</p><h2 className="mt-2 text-2xl font-semibold">Sources supporting this screening</h2><div className="mt-5 space-y-3">{evidence.citations.map((source) => <button type="button" onClick={() => void openCitation(source)} key={source.id} className="block w-full rounded-xl border border-border bg-background p-4 text-left transition hover:border-accent"><div className="flex justify-between gap-4"><p className="text-sm font-semibold">{source.title}</p><span className="font-mono text-[9px] text-ink-muted">{source.locator ?? source.jurisdiction}</span></div><p className="mt-2 text-xs text-ink-muted">{source.authority} · {source.support_status}</p><p className="mt-3 text-xs leading-5 text-ink-muted">{source.excerpt}</p></button>)}</div></div>
          </section>
          <section className="mt-8 rounded-3xl border border-border bg-surface p-6"><div className="flex flex-col justify-between gap-4 md:flex-row md:items-center"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Case evidence vault</p><h2 className="mt-2 text-xl font-semibold">Attach and index controlled evidence</h2><p className="mt-2 text-xs text-ink-muted">PDF, TXT or DOCX · maximum 10 MB · automatic scanned-PDF OCR · SHA-256 integrity · page/chunk lineage</p></div><label className={`rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white ${processing ? "cursor-wait opacity-50" : "cursor-pointer"}`}><input disabled={processing} type="file" accept=".pdf,.txt,.docx" className="sr-only" onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload(file); event.currentTarget.value = ""; }} />{processing ? "Indexing…" : "Attach evidence"}</label></div>{uploadStatus && <p role="status" className="mt-4 rounded-xl border border-border bg-background p-3 text-xs text-ink-muted">{uploadStatus}</p>}<div className="mt-5 grid gap-3 md:grid-cols-3"><VaultMetric label="Indexed documents" value={retrieval?.indexed_document_count ?? documents.filter((item) => item.status === "indexed").length} /><VaultMetric label="Searchable passages" value={retrieval?.chunk_count ?? documents.reduce((sum, item) => sum + item.chunk_count, 0)} /><VaultMetric label="Retrieved this run" value={retrieval?.retrieved_passage_count ?? 0} /></div>{documents.length > 0 && <div className="mt-5 space-y-2">{documents.map((document) => <div key={document.id} className="flex flex-col gap-3 rounded-xl border border-border bg-background p-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-sm font-semibold">{document.filename}</p><p className="mt-1 font-mono text-[9px] uppercase text-ink-muted">{document.status} · {document.page_count} page(s) · {document.chunk_count} passages · SHA {document.sha256.slice(0, 12)}…</p></div><button type="button" onClick={() => { if (!currentCase.backendId) return; void caseApi.deleteDocument(currentCase.backendId, document.id).then(async () => { await caseApi.analyze(currentCase.backendId!); notifyAnalysisUpdated(); await refreshDocuments(); }); }} className="text-xs font-semibold text-danger hover:underline">Remove</button></div>)}</div>}</section>
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
