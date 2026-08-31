"use client";

import { AnalysisState, ModuleHeader } from "@/components/analysis-state";
import { openCitation } from "@/lib/api";
import { useCurrentAnalysis } from "@/lib/use-current-analysis";

export default function DesignAroundPage() {
  const { analysis, loading, error } = useCurrentAnalysis();
  const design = analysis?.result.design_around;

  return (
    <div className="py-8 md:py-10">
      <ModuleHeader
        eyebrow="Innovation Design-Around"
        title="Change the technical facts, not just the wording."
        description="Turn reviewer objections into counterfactual product, process, claim and portfolio directions—with the new evidence burden kept visible."
      />
      {!design ? <AnalysisState loading={loading} error={error} /> : (
        <>
          <section className="mt-8 rounded-2xl border border-warm/30 bg-warm-subtle p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-warm">Human-review boundary</p>
            <p className="mt-2 text-sm leading-6 text-ink">{design.notice}</p>
          </section>
          <section className="mt-8 grid gap-5 xl:grid-cols-2">
            {design.alternatives.map((alternative, index) => (
              <article key={alternative.id} className="rounded-3xl border border-border bg-surface p-6">
                <div className="flex items-center justify-between gap-4">
                  <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-accent">Direction {String(index + 1).padStart(2, "0")}</span>
                  <span className="rounded-full bg-accent-subtle px-3 py-1 font-mono text-[9px] uppercase text-accent">inference · review required</span>
                </div>
                <h2 className="mt-5 text-2xl font-semibold">{alternative.dimension}</h2>
                {alternative.basis && <div className="mt-4 rounded-xl border border-accent/20 bg-accent-subtle p-3"><p className="font-mono text-[9px] uppercase tracking-[0.14em] text-accent">Case-specific basis</p><p className="mt-1 text-xs leading-5 text-ink">{alternative.basis}</p></div>}
                <p className="mt-4 text-sm leading-6 text-ink">{alternative.proposed_change}</p>
                <p className="mt-3 text-sm leading-6 text-ink-muted">{alternative.rationale}</p>
                <div className="mt-6 grid gap-4 sm:grid-cols-2">
                  <ListBlock title="Evidence to generate" items={alternative.evidence_required} tone="accent" />
                  <ListBlock title="Residual risks" items={alternative.residual_risks} tone="warm" />
                </div>
                <div className="mt-5 flex flex-wrap gap-2">
                  {alternative.citations.map((citation) => (
                    <button key={citation.id} type="button" onClick={() => void openCitation(citation)} className="rounded-full border border-border px-3 py-1.5 text-[10px] font-semibold text-ink-muted transition hover:border-accent hover:text-accent">
                      {citation.title} ↗
                    </button>
                  ))}
                </div>
              </article>
            ))}
          </section>
          <section className="mt-8 rounded-3xl border border-border bg-[#16212B] p-7 text-white">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/50">Recommended protection sequence</p>
            <div className="mt-5 grid gap-3 lg:grid-cols-2">
              {design.recommended_route.map((step, index) => (
                <div key={step} className="flex gap-4 rounded-2xl border border-white/10 bg-white/5 p-4">
                  <span className="font-mono text-xs text-[#9BD0C0]">{String(index + 1).padStart(2, "0")}</span>
                  <p className="text-sm leading-6 text-white/80">{step}</p>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function ListBlock({ title, items, tone }: { title: string; items: string[]; tone: "accent" | "warm" }) {
  return (
    <div className="rounded-2xl border border-border bg-background p-4">
      <p className={`text-xs font-semibold ${tone === "accent" ? "text-accent" : "text-warm"}`}>{title}</p>
      <ul className="mt-3 space-y-2">
        {items.map((item) => <li key={item} className="text-xs leading-5 text-ink-muted">• {item}</li>)}
      </ul>
    </div>
  );
}
