"use client";

import Link from "next/link";
import { AnalysisState, ModuleHeader } from "@/components/analysis-state";
import { useCurrentAnalysis } from "@/lib/use-current-analysis";

export default function IPStrategyPage() {
  const { analysis, loading, error } = useCurrentAnalysis();
  const strategy = analysis?.result.ip_strategy;
  const strongest = strategy?.routes.reduce((best, route) => route.strength > best.strength ? route : best, strategy.routes[0]);
  return (
    <div className="py-8 md:py-10">
      <ModuleHeader eyebrow="IP Strategy" title="Protect the differentiator, not the theme." description="Compare patents, trademarks, trade secrets, designs and geographical indications against the actual technical and commercial value in this case." />
      {!strategy || !strongest ? <AnalysisState loading={loading} error={error} /> : (
        <>
          <section className="mt-8 rounded-3xl border border-border bg-[#16212B] p-7 text-white md:p-8"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/50">Recommended lead route</p><div className="mt-3 flex flex-col gap-5 md:flex-row md:items-end md:justify-between"><div><h2 className="text-3xl font-semibold">{strongest.name}</h2><p className="mt-3 max-w-3xl text-sm leading-7 text-white/65">{strongest.protects}</p></div><div className="rounded-xl border border-white/15 px-4 py-3 text-right"><p className="text-2xl font-semibold">{strongest.strength}</p><p className="font-mono text-[9px] uppercase text-white/50">screening strength</p></div></div></section>
          <section className="mt-10"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Protection portfolio</p><h2 className="mt-2 text-2xl font-semibold">Possible rights and control mechanisms</h2><div className="mt-6 grid gap-4 md:grid-cols-2">{strategy.routes.map((route, index) => <article key={route.name} className="rounded-2xl border border-border bg-surface p-6"><div className="flex items-start justify-between gap-4"><div><p className="font-mono text-[9px] text-ink-muted">{String(index + 1).padStart(2, "0")}</p><h3 className="mt-2 text-xl font-semibold">{route.name}</h3></div><span className="rounded-full bg-accent-subtle px-3 py-1 text-xs font-medium text-accent">{route.relevance}</span></div><div className="mt-5 h-2 rounded-full bg-accent-subtle"><div className="h-full rounded-full bg-accent" style={{ width: `${route.strength}%` }} /></div><p className="mt-2 font-mono text-[9px] text-ink-muted">{route.strength}/100 relevance-strength signal</p><div className="mt-5 border-t border-border pt-5"><p className="text-sm leading-6 text-ink-muted">{route.protects}</p><p className="mt-3 text-xs leading-5 text-warm"><strong>Caution:</strong> {route.caution}</p></div></article>)}</div></section>
          <section className="mt-10 grid gap-6 lg:grid-cols-[1fr_0.7fr]"><div className="rounded-3xl border border-border bg-surface p-7"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Recommended protection strategy</p><div className="mt-5 space-y-3">{strategy.recommended_strategy.map((step, index) => <div key={step} className="flex gap-4 rounded-xl border border-border bg-background p-4"><span className="font-mono text-[10px] text-accent">{String(index + 1).padStart(2, "0")}</span><p className="text-sm leading-6">{step}</p></div>)}</div></div><div className="rounded-3xl border border-warm/25 bg-warm-subtle p-7"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-warm">Adversarial check</p><h2 className="mt-3 text-2xl font-semibold">Test the strategy before filing.</h2><p className="mt-3 text-sm leading-6 text-ink-muted">See how a patent examiner could challenge novelty, inventive step and traditional-knowledge exposure.</p><Link href="/challenge" className="mt-6 inline-flex font-medium text-warm hover:underline">Challenge this innovation →</Link></div></section>
          <div className="mt-8 flex flex-wrap gap-2">{strategy.citations.map((source) => <a key={source.id} href={source.url} target="_blank" rel="noreferrer" className="rounded-full border border-border bg-surface px-3 py-2 text-xs text-ink-muted hover:border-accent hover:text-accent">{source.authority} ↗</a>)}</div>
        </>
      )}
    </div>
  );
}
