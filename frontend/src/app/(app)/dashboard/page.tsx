"use client";

import Link from "next/link";
import { AnalysisState, ModuleHeader } from "@/components/analysis-state";
import { useCurrentAnalysis } from "@/lib/use-current-analysis";
import { useCurrentCase } from "@/lib/use-current-case";

export default function DashboardPage() {
  const currentCase = useCurrentCase();
  const { analysis, loading, error } = useCurrentAnalysis();
  const result = analysis?.result;
  return (
    <div className="py-8 md:py-10">
      <ModuleHeader eyebrow="Command Dashboard" title="Your innovation at a glance." description="Track the active case across traditional knowledge, evidence, IP, regulatory, ABS and jurisdiction work without losing context." />
      {!result ? <AnalysisState loading={loading} error={error} /> : (
        <>
          <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8"><div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between"><div className="max-w-3xl"><div className="flex flex-wrap gap-2"><span className="rounded-full bg-accent-subtle px-3 py-1 font-mono text-[9px] uppercase text-accent">Active case</span><span className="rounded-full border border-border px-3 py-1 font-mono text-[9px] text-ink-muted">CASE-{String(currentCase.backendId).padStart(5, "0")}</span></div><h2 className="mt-4 text-2xl font-semibold">{currentCase.title}</h2><p className="mt-3 text-sm leading-7 text-ink-muted">{currentCase.productDescription}</p></div><Link href="/analyze" className="inline-flex h-11 items-center justify-center rounded-xl bg-accent px-5 text-sm font-semibold text-white">New analysis →</Link></div><div className="mt-6 flex flex-wrap gap-2">{currentCase.ingredients.map((ingredient) => <span key={ingredient} className="rounded-full border border-border bg-background px-3 py-1.5 text-xs text-ink-muted">{ingredient}</span>)}</div></section>
          <section className="mt-8"><div className="flex items-end justify-between"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Risk and opportunity signals</p><h2 className="mt-2 text-2xl font-semibold">What needs attention</h2></div><span className="font-mono text-[10px] text-ink-muted">{result.confidence.label}</span></div><div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-5">{result.risk_cards.map((card) => <div key={card.key} className="rounded-2xl border border-border bg-surface p-5"><div className="flex items-start justify-between gap-3"><p className="text-sm font-semibold">{card.title}</p><span className="text-xl font-semibold text-accent">{card.score}</span></div><p className="mt-3 text-xs leading-5 text-ink-muted">{card.summary}</p><p className="mt-4 font-mono text-[9px] uppercase text-warm">{card.level}</p></div>)}</div></section>
          <section className="mt-8 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]"><div className="rounded-3xl border border-border bg-[#16212B] p-7 text-white"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/50">Executive screening</p><h2 className="mt-3 text-3xl font-semibold">{result.classification.label}</h2><p className="mt-4 text-sm leading-7 text-white/65">{result.executive_summary}</p><Link href="/challenge" className="mt-7 inline-flex rounded-xl bg-white px-5 py-3 text-sm font-semibold text-ink">Challenge the analysis →</Link></div><div className="rounded-3xl border border-border bg-surface p-7"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Next best actions</p><div className="mt-5 space-y-3">{result.next_actions.map((action, index) => <div key={action} className="flex gap-3 rounded-xl border border-border bg-background p-4"><span className="font-mono text-[9px] text-accent">{String(index + 1).padStart(2, "0")}</span><p className="text-xs leading-5">{action}</p></div>)}</div></div></section>
          <section className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{[["Knowledge lineage", "/traditional-knowledge"], ["Scientific evidence", "/evidence"], ["Protection portfolio", "/ip-strategy"], ["Jurisdiction comparison", "/jurisdiction"]].map(([label, href]) => <Link key={href} href={href} className="rounded-2xl border border-border bg-surface p-5 text-sm font-semibold transition hover:border-accent hover:text-accent">{label} →</Link>)}</section>
        </>
      )}
    </div>
  );
}
