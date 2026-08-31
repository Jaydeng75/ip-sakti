"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AnalysisState, ModuleHeader } from "@/components/analysis-state";
import { ApiCase, caseApi } from "@/lib/api";
import { saveCaseSnapshot } from "@/lib/case-store";
import { notifyAnalysisUpdated } from "@/lib/use-current-analysis";

export default function SavedCasesPage() {
  const router = useRouter();
  const [cases, setCases] = useState<ApiCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const load = window.setTimeout(async () => {
      try { setCases(await caseApi.list()); } catch (caught) { setError(caught instanceof Error ? caught.message : "Cases could not be loaded."); } finally { setLoading(false); }
    }, 0);
    return () => window.clearTimeout(load);
  }, []);

  async function openCase(item: ApiCase) {
    try {
      const analysis = await caseApi.latestAnalysis(item.id);
      saveCaseSnapshot({ id: `case-ip360-${item.id}`, backendId: item.id, title: item.title, productDescription: item.description, ingredients: item.ingredients, jurisdiction: item.target_markets.join(" · "), productType: analysis.result.classification.label, createdAt: item.created_at, updatedAt: item.updated_at, status: item.status });
      notifyAnalysisUpdated();
      router.push("/dashboard");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "The case could not be opened."); }
  }

  return (
    <div className="py-8 md:py-10">
      <ModuleHeader eyebrow="Saved Cases" title="Your innovation portfolio." description="Return to an existing project and restore its analysis context across every intelligence module." />
      {loading ? <AnalysisState loading error={null} /> : error && !cases.length ? <AnalysisState loading={false} error={error} /> : cases.length ? <section className="mt-8"><div className="flex items-end justify-between"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Saved portfolio</p><h2 className="mt-2 text-2xl font-semibold">Recent innovation cases</h2></div><span className="font-mono text-xs text-ink-muted">{String(cases.length).padStart(2, "0")} cases</span></div><div className="mt-6 grid gap-4 md:grid-cols-2">{cases.map((item) => <article key={item.id} className="rounded-3xl border border-border bg-surface p-6"><div className="flex items-start justify-between gap-3"><span className="rounded-full bg-accent-subtle px-3 py-1 font-mono text-[9px] uppercase text-accent">{item.status.replaceAll("_", " ")}</span><span className="font-mono text-[9px] text-ink-muted">CASE-{String(item.id).padStart(5, "0")}</span></div><h3 className="mt-5 text-xl font-semibold">{item.title}</h3><p className="mt-3 line-clamp-3 text-sm leading-6 text-ink-muted">{item.description}</p><div className="mt-4 flex flex-wrap gap-2">{item.target_markets.map((market) => <span key={market} className="rounded-full border border-border px-2.5 py-1 text-[10px] text-ink-muted">{market}</span>)}</div><div className="mt-6 flex items-center justify-between border-t border-border pt-5"><span className="text-xs text-ink-muted">Updated {new Date(item.updated_at).toLocaleDateString("en-IN")}</span><button type="button" onClick={() => void openCase(item)} className="text-sm font-semibold text-accent hover:underline">Open case →</button></div></article>)}</div></section> : <div className="mt-8 rounded-3xl border border-dashed border-border bg-surface p-8"><h2 className="text-2xl font-semibold">No saved cases yet.</h2><Link href="/analyze" className="mt-5 inline-flex rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white">Create the first case →</Link></div>}
      {error && cases.length > 0 && <p role="alert" className="mt-5 rounded-xl bg-danger-subtle p-4 text-sm text-danger">{error}</p>}
    </div>
  );
}
