"use client";

import { AnalysisState, ModuleHeader } from "@/components/analysis-state";
import { useState } from "react";
import { caseApi } from "@/lib/api";
import { useCurrentAnalysis } from "@/lib/use-current-analysis";
import { useCurrentCase } from "@/lib/use-current-case";

export default function ScientificEvidencePage() {
  const { analysis, loading, error } = useCurrentAnalysis();
  const currentCase = useCurrentCase();
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const evidence = analysis?.result.scientific_evidence;
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
            <div className="rounded-3xl border border-border bg-surface p-6"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Official references</p><h2 className="mt-2 text-2xl font-semibold">Sources supporting this screening</h2><div className="mt-5 space-y-3">{evidence.citations.map((source) => <a key={source.id} href={source.url} target="_blank" rel="noreferrer" className="block rounded-xl border border-border bg-background p-4 transition hover:border-accent"><div className="flex justify-between gap-4"><p className="text-sm font-semibold">{source.title}</p><span className="font-mono text-[9px] text-ink-muted">{source.jurisdiction}</span></div><p className="mt-2 text-xs text-ink-muted">{source.authority} · {source.support_status}</p><p className="mt-3 text-xs leading-5 text-ink-muted">{source.excerpt}</p></a>)}</div></div>
          </section>
          <section className="mt-8 rounded-3xl border border-border bg-surface p-6"><div className="flex flex-col justify-between gap-4 md:flex-row md:items-center"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Case evidence vault</p><h2 className="mt-2 text-xl font-semibold">Attach a controlled evidence document</h2><p className="mt-2 text-xs text-ink-muted">PDF, TXT or DOCX · maximum 10 MB · stored with a SHA-256 integrity record</p></div><label className="cursor-pointer rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white"><input type="file" accept=".pdf,.txt,.docx" className="sr-only" onChange={(event) => { const file = event.target.files?.[0]; if (!file || !currentCase.backendId) return; setUploadStatus("Uploading and hashing…"); void caseApi.uploadDocument(currentCase.backendId, file).then((document) => setUploadStatus(`Stored ${document.filename} · ${document.sha256.slice(0, 12)}…`)).catch((caught: unknown) => setUploadStatus(caught instanceof Error ? caught.message : "Upload failed.")); }} />Attach evidence</label></div>{uploadStatus && <p role="status" className="mt-4 rounded-xl border border-border bg-background p-3 text-xs text-ink-muted">{uploadStatus}</p>}</section>
        </>
      )}
    </div>
  );
}

function EvidenceCard({ number, title, status, summary, confidence }: { number: string; title: string; status: string; summary: string; confidence: number }) {
  return <article className="rounded-2xl border border-border bg-surface p-6"><div className="flex items-center justify-between"><span className="font-mono text-[10px] text-accent">{number}</span><span className="rounded-full bg-accent-subtle px-2 py-1 font-mono text-[9px] uppercase text-accent">{status.replaceAll("_", " ")}</span></div><h2 className="mt-5 text-lg font-semibold">{title}</h2><p className="mt-3 text-sm leading-6 text-ink-muted">{summary}</p><div className="mt-5 h-1.5 rounded-full bg-accent-subtle"><div className="h-full rounded-full bg-accent" style={{ width: `${confidence * 100}%` }} /></div><p className="mt-2 font-mono text-[9px] text-ink-muted">{Math.round(confidence * 100)}% screening confidence</p></article>;
}
