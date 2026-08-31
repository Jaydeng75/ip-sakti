"use client";

import { AnalysisState, ModuleHeader } from "@/components/analysis-state";
import { useCurrentAnalysis } from "@/lib/use-current-analysis";

export default function RegulatoryPage() {
  const { analysis, loading, error } = useCurrentAnalysis();
  const regulatory = analysis?.result.regulatory_abs;
  return (
    <div className="py-8 md:py-10">
      <ModuleHeader eyebrow="Regulatory & ABS" title="Turn classification into a market-entry plan." description="Move step by step from product classification through applicable regulation, biological-resource review, evidence, documentation and authorization." />
      {!regulatory ? <AnalysisState loading={loading} error={error} /> : (
        <>
          <section className="mt-8 grid gap-3 md:grid-cols-6">{regulatory.steps.map((step) => <div key={step.order} className={`rounded-2xl border p-4 ${step.order === 1 ? "border-accent bg-accent-subtle" : "border-border bg-surface"}`}><span className="font-mono text-[10px] font-semibold text-accent">{String(step.order).padStart(2, "0")}</span><p className="mt-5 text-sm font-semibold leading-5">{step.name}</p><p className="mt-3 font-mono text-[9px] uppercase text-ink-muted">{step.status}</p></div>)}</section>
          <section className="mt-10"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Decision pathway</p><h2 className="mt-2 text-2xl font-semibold">Required decisions and controlled outputs</h2><div className="mt-6 space-y-4">{regulatory.steps.map((step) => <article key={step.order} className="rounded-2xl border border-border bg-surface p-6"><div className="flex flex-col gap-4 md:flex-row md:items-start"><span className="font-mono text-xs text-accent">{String(step.order).padStart(2, "0")}</span><div className="flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className="text-lg font-semibold">{step.name}</h3><span className="rounded-full bg-warm-subtle px-2.5 py-1 font-mono text-[9px] uppercase text-warm">{step.status}</span></div><p className="mt-3 text-sm leading-7 text-ink-muted">{step.detail}</p><div className="mt-4 rounded-xl border border-border bg-background p-3"><p className="font-mono text-[9px] uppercase text-ink-muted">Required deliverable</p><p className="mt-1 text-xs font-medium">{step.deliverable}</p></div></div></div></article>)}</div></section>
          <section className="mt-10 grid gap-6 md:grid-cols-2"><div className={`rounded-3xl border p-7 ${regulatory.abs_flag ? "border-warm/30 bg-warm-subtle" : "border-border bg-surface"}`}><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-warm">Biological resources / ABS</p><h2 className="mt-3 text-2xl font-semibold">{regulatory.abs_flag ? "ABS screening is required." : "No current ABS flag."}</h2><p className="mt-3 text-sm leading-7 text-ink-muted">{regulatory.abs_summary}</p></div><div className="rounded-3xl border border-border bg-[#16212B] p-7 text-white"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/50">Control principle</p><h2 className="mt-3 text-2xl font-semibold">Classification comes before the dossier.</h2><p className="mt-3 text-sm leading-7 text-white/65">Claims, intended use and product form determine which authority, evidence package and market-entry route apply.</p></div></section>
          <div className="mt-8 flex flex-wrap gap-2">{regulatory.citations.map((source) => <a key={source.id} href={source.url} target="_blank" rel="noreferrer" className="rounded-full border border-border bg-surface px-3 py-2 text-xs text-ink-muted hover:border-accent hover:text-accent">{source.title} ↗</a>)}</div>
        </>
      )}
    </div>
  );
}
