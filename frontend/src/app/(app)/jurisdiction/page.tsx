"use client";

import { AnalysisState, ModuleHeader } from "@/components/analysis-state";
import { useCurrentAnalysis } from "@/lib/use-current-analysis";
import { useCurrentCase } from "@/lib/use-current-case";

export default function JurisdictionPage() {
  const currentCase = useCurrentCase();
  const { analysis, loading, error } = useCurrentAnalysis();
  const markets = analysis?.result.jurisdictions;
  return (
    <div className="py-8 md:py-10">
      <ModuleHeader eyebrow="Jurisdiction Compare" title="One innovation. Different legal landscapes." description="Compare patent, traditional-knowledge, regulatory, evidence and market-entry questions while keeping territorial rules clearly separated." />
      {!markets ? <AnalysisState loading={loading} error={error} /> : (
        <>
          <section className="mt-8 rounded-3xl border border-border bg-surface p-6"><div className="flex flex-col justify-between gap-4 md:flex-row md:items-end"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Current case</p><h2 className="mt-2 text-2xl font-semibold">{currentCase.title}</h2><p className="mt-2 text-sm text-ink-muted">Requested markets: {currentCase.jurisdiction}</p></div><span className="rounded-full bg-accent-subtle px-3 py-1.5 text-xs font-medium text-accent">{currentCase.productType}</span></div></section>
          <section className="mt-10"><div className="mb-6"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Territorial comparison</p><h2 className="mt-2 text-2xl font-semibold">Review each column independently.</h2></div><div className="overflow-x-auto rounded-3xl border border-border bg-surface"><table className="w-full min-w-[1050px] border-collapse text-left"><thead><tr className="border-b border-border bg-background"><th className="w-48 p-5 font-mono text-[10px] uppercase tracking-[0.15em] text-ink-muted">Area</th>{markets.map((market) => <th key={market.name} className={market.selected ? "bg-accent-subtle/50 p-5" : "p-5"}><div className="flex items-center gap-2"><span className="text-sm font-semibold">{market.name}</span>{market.selected && <span className="rounded-full bg-accent px-2 py-0.5 font-mono text-[8px] uppercase text-white">target</span>}</div></th>)}</tr></thead><tbody><Comparison label="Patent issues" values={markets.map((item) => item.patent)} active={markets.map((item) => item.selected)} /><Comparison label="Traditional knowledge" values={markets.map((item) => item.tk)} active={markets.map((item) => item.selected)} /><Comparison label="Regulatory pathway" values={markets.map((item) => item.regulation)} active={markets.map((item) => item.selected)} /><Comparison label="Evidence requirements" values={markets.map((item) => item.evidence)} active={markets.map((item) => item.selected)} /><Comparison label="Market-entry complexity" values={markets.map((item) => item.market_entry)} active={markets.map((item) => item.selected)} last /></tbody></table></div></section>
          <section className="mt-8 grid gap-4 md:grid-cols-2">{markets.filter((market) => market.selected).map((market) => <div key={market.name} className="rounded-2xl border border-border bg-surface p-6"><p className="font-mono text-[10px] uppercase tracking-[0.16em] text-accent">{market.name} sources</p><div className="mt-4 space-y-2">{market.citations.map((source) => <a key={source.id} href={source.url} target="_blank" rel="noreferrer" className="block rounded-xl border border-border bg-background p-3 text-xs font-medium hover:border-accent hover:text-accent">{source.title} ↗<span className="mt-1 block font-normal text-ink-muted">{source.support_status} · {source.effective_date}</span></a>)}</div></div>)}</section>
          <p className="mt-8 text-center text-xs text-ink-muted">This is a screening comparison, not a freedom-to-operate opinion, filing opinion or market authorization.</p>
        </>
      )}
    </div>
  );
}

function Comparison({ label, values, active, last = false }: { label: string; values: string[]; active: boolean[]; last?: boolean }) {
  return <tr className={last ? "" : "border-b border-border"}><td className="p-5 align-top text-sm font-semibold">{label}</td>{values.map((value, index) => <td key={`${label}-${index}`} className={`p-5 align-top text-sm leading-6 ${active[index] ? "bg-accent-subtle/25 text-ink" : "text-ink-muted"}`}>{value}</td>)}</tr>;
}
