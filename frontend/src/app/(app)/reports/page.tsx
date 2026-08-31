"use client";

import { useState } from "react";
import { AnalysisState, ModuleHeader } from "@/components/analysis-state";
import { caseApi } from "@/lib/api";
import { useCurrentAnalysis } from "@/lib/use-current-analysis";
import { useCurrentCase } from "@/lib/use-current-case";

export default function ReportsPage() {
  const currentCase = useCurrentCase();
  const { analysis, loading, error } = useCurrentAnalysis();
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const result = analysis?.result;

  async function download() {
    if (!currentCase.backendId) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      const report = await caseApi.report(currentCase.backendId);
      const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `ip-sakti-case-${currentCase.backendId}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (caught) { setDownloadError(caught instanceof Error ? caught.message : "The report could not be generated."); } finally { setDownloading(false); }
  }

  return (
    <div className="py-8 md:py-10">
      <ModuleHeader eyebrow="Reports" title="A decision record you can review and export." description="Consolidate the current innovation, source-grounded findings, protection strategy, evidence gaps, regulatory pathway and limitations." />
      {!result ? <AnalysisState loading={loading} error={error} /> : (
        <>
          <section className="mt-8 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]"><div className="rounded-3xl border border-border bg-surface p-7"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Current case</p><h2 className="mt-3 text-2xl font-semibold">{currentCase.title}</h2><p className="mt-3 text-sm leading-7 text-ink-muted">{currentCase.productDescription}</p><div className="mt-5 flex flex-wrap gap-2"><span className="rounded-full bg-accent-subtle px-3 py-1 text-xs text-accent">{currentCase.productType}</span><span className="rounded-full border border-border px-3 py-1 text-xs text-ink-muted">corpus {result.corpus_version}</span></div></div><div className="rounded-3xl border border-border bg-[#16212B] p-7 text-white"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/50">Controlled export</p><h2 className="mt-3 text-2xl font-semibold">Innovation intelligence report</h2><p className="mt-3 text-sm leading-7 text-white/65">Includes source URLs, confidence, limitations and a generated-at record for downstream review.</p><button type="button" onClick={() => void download()} disabled={downloading} className="mt-7 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-ink disabled:opacity-50">{downloading ? "Generating…" : "Download structured report ↓"}</button></div></section>
          {downloadError && <p role="alert" className="mt-5 rounded-xl bg-danger-subtle p-4 text-sm text-danger">{downloadError}</p>}
          <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8"><div className="border-b border-border pb-6"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Report preview</p><h2 className="mt-2 text-3xl font-semibold">Executive innovation analysis</h2><p className="mt-2 text-xs text-ink-muted">CASE-{String(currentCase.backendId).padStart(5, "0")} · {result.generated_by}</p></div><ReportSection number="01" title="Executive summary"><p>{result.executive_summary}</p></ReportSection><ReportSection number="02" title="Risk and opportunity signals"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{result.risk_cards.map((card) => <div key={card.key} className="rounded-xl border border-border bg-background p-4"><p className="text-xl font-semibold text-accent">{card.score}</p><p className="mt-1 text-xs font-medium">{card.title}</p></div>)}</div></ReportSection><ReportSection number="03" title="Protection strategy"><div className="space-y-2">{result.ip_strategy.recommended_strategy.map((item) => <p key={item} className="rounded-xl border border-border bg-background p-3">{item}</p>)}</div></ReportSection><ReportSection number="04" title="Next actions"><ol className="space-y-2">{result.next_actions.map((item, index) => <li key={item}>{index + 1}. {item}</li>)}</ol></ReportSection><div className="mt-8 border-t border-border pt-6 text-xs leading-5 text-ink-muted">{result.warnings.join(" ")}</div></section>
        </>
      )}
    </div>
  );
}

function ReportSection({ number, title, children }: { number: string; title: string; children: React.ReactNode }) {
  return <section className="mt-8 border-t border-border pt-7 first:border-0"><p className="font-mono text-[10px] uppercase tracking-[0.16em] text-accent">{number} / {title}</p><div className="mt-4 text-sm leading-7 text-ink-muted">{children}</div></section>;
}
