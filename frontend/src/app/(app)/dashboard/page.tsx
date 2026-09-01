"use client";

import Link from "next/link";
import { useState } from "react";
import { AnalysisState, ModuleHeader } from "@/components/analysis-state";
import { RiskCard } from "@/lib/api";
import { useCurrentAnalysis } from "@/lib/use-current-analysis";
import { useCurrentCase } from "@/lib/use-current-case";

export default function DashboardPage() {
  const currentCase = useCurrentCase();
  const { analysis, loading, error } = useCurrentAnalysis();
  const result = analysis?.result;
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const selected = result?.risk_cards.find((card) => card.key === selectedKey) ?? null;

  return (
    <div className="py-8 md:py-10">
      <ModuleHeader eyebrow="Command Dashboard" title="Case decisions, not abstract scores." description="See what is protectable, exposed, unsupported and unresolved—then open every screening signal to inspect its basis and gaps." />
      {!result ? <AnalysisState loading={loading} error={error} /> : (
        <>
          <section className="mt-8 rounded-3xl border border-border bg-[#16212B] p-6 text-white md:p-8">
            <div className="flex flex-col justify-between gap-5 md:flex-row md:items-start">
              <div><p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#9BD0C0]">Case decision brief · CASE-{String(currentCase.backendId).padStart(5, "0")}</p><h2 className="mt-3 text-3xl font-semibold">{currentCase.title}</h2><p className="mt-3 max-w-3xl text-sm leading-6 text-white/60">{result.executive_summary}</p></div>
              <Link href="/analyze" className="inline-flex rounded-xl bg-white px-5 py-3 text-sm font-semibold text-ink">New analysis →</Link>
            </div>
            <div className="mt-8 grid gap-px overflow-hidden rounded-2xl bg-white/10 sm:grid-cols-2 xl:grid-cols-3">
              <Decision label="Strongest protectable element" value={result.decision_brief.strongest_protectable_element} />
              <Decision label="Highest legal / TK risk" value={result.decision_brief.highest_tk_risk} />
              <Decision label="Largest scientific gap" value={result.decision_brief.largest_scientific_gap} />
              <Decision label="Regulatory status" value={result.decision_brief.regulatory_status} />
              <Decision label="ABS status" value={result.decision_brief.abs_status} />
              <Decision label="Most important next step" value={result.decision_brief.most_important_next_step} />
            </div>
          </section>

          <section className="mt-8 grid gap-5 lg:grid-cols-2">
            <FactList title="What we know" items={result.decision_brief.known} established />
            <FactList title="What is not yet established" items={result.decision_brief.not_established} />
          </section>

          <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8">
            <div className="flex flex-col justify-between gap-3 md:flex-row md:items-end"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Explainable screening</p><h2 className="mt-2 text-2xl font-semibold">Open a signal to inspect the reasoning.</h2></div><p className="max-w-md text-xs leading-5 text-ink-muted">Numbers are internal screening indices—not probabilities, legal conclusions or efficacy percentages.</p></div>
            <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              {result.risk_cards.map((card) => <SignalButton key={card.key} card={card} selected={selectedKey === card.key} onClick={() => setSelectedKey(selectedKey === card.key ? null : card.key)} />)}
            </div>
            {selected && <SignalDetail card={selected} />}
          </section>

          <section className="mt-8 grid gap-6 lg:grid-cols-[1fr_1fr]">
            <div className="rounded-3xl border border-border bg-surface p-7"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Classification decision</p><h2 className="mt-3 text-2xl font-semibold">{result.classification.label}</h2><p className="mt-3 text-sm leading-6 text-ink-muted">{result.classification.pathway}</p><div className="mt-5 flex flex-wrap gap-2">{result.classification.candidate_pathways?.map((path) => <span key={path} className="rounded-full border border-border bg-background px-3 py-1.5 text-xs text-ink-muted">{path}</span>)}</div></div>
            <div className="rounded-3xl border border-border bg-surface p-7"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Next best actions</p><div className="mt-5 space-y-3">{result.next_actions.map((action, index) => <div key={action} className="flex gap-3 rounded-xl border border-border bg-background p-4"><span className="font-mono text-[9px] text-accent">{String(index + 1).padStart(2, "0")}</span><p className="text-xs leading-5">{action}</p></div>)}</div></div>
          </section>
          <section className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{[["Knowledge lineage", "/traditional-knowledge"], ["Scientific evidence", "/evidence"], ["Protection portfolio", "/ip-strategy"], ["Jurisdiction comparison", "/jurisdiction"]].map(([label, href]) => <Link key={href} href={href} className="rounded-2xl border border-border bg-surface p-5 text-sm font-semibold transition hover:border-accent hover:text-accent">{label} →</Link>)}</section>
        </>
      )}
    </div>
  );
}

function Decision({ label, value }: { label: string; value: string }) { return <div className="bg-[#16212B] p-5"><p className="font-mono text-[9px] uppercase tracking-[0.15em] text-white/40">{label}</p><p className="mt-2 text-sm font-medium leading-6 text-white/85">→ {value}</p></div>; }
function FactList({ title, items, established = false }: { title: string; items: string[]; established?: boolean }) { return <div className="rounded-3xl border border-border bg-surface p-6"><h2 className="text-xl font-semibold">{title}</h2><div className="mt-5 space-y-3">{items.map((item) => <div key={item} className="flex gap-3 text-sm leading-6"><span className={established ? "text-accent" : "text-danger"}>{established ? "✓" : "✕"}</span><span>{item}</span></div>)}</div></div>; }
function SignalButton({ card, selected, onClick }: { card: RiskCard; selected: boolean; onClick: () => void }) { return <button type="button" aria-expanded={selected} onClick={onClick} className={`rounded-2xl border p-4 text-left transition ${selected ? "border-accent bg-accent-subtle" : "border-border bg-background hover:border-accent"}`}><div className="flex items-start justify-between gap-2"><p className="text-sm font-semibold">{card.title}</p><span className="font-mono text-sm font-semibold text-accent">{card.display_value ?? card.score}</span></div><p className="mt-3 text-xs leading-5 text-ink-muted">{card.primary_finding ?? card.summary}</p><p className="mt-4 font-mono text-[9px] uppercase text-accent">{selected ? "Hide rationale ↑" : "Explain signal ↓"}</p></button>; }
function SignalDetail({ card }: { card: RiskCard }) { return <div className="mt-5 rounded-2xl border border-accent/30 bg-background p-5"><div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4"><DetailColumn title="Why / positive signals" items={card.positive_signals ?? []} /><DetailColumn title="Risks / negative signals" items={card.negative_signals ?? []} /><DetailColumn title="Missing evidence" items={card.missing_evidence ?? []} /><DetailColumn title="What could change it" items={card.what_changes_score ?? []} /></div><p className="mt-5 border-t border-border pt-4 text-xs leading-5 text-ink-muted">{card.summary}</p></div>; }
function DetailColumn({ title, items }: { title: string; items: string[] }) { return <div><p className="font-mono text-[9px] uppercase tracking-[0.15em] text-accent">{title}</p><ul className="mt-3 space-y-2 text-xs leading-5 text-ink-muted">{items.map((item) => <li key={item}>• {item}</li>)}</ul></div>; }
