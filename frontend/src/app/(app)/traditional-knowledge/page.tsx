"use client";

import { useMemo, useState } from "react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { AnalysisState, ModuleHeader } from "@/components/analysis-state";
import { openCitation } from "@/lib/api";
import { useCurrentAnalysis } from "@/lib/use-current-analysis";

export default function TraditionalKnowledgePage() {
  const { analysis, loading, error } = useCurrentAnalysis();
  const graph = analysis?.result.knowledge_graph;
  const tk = analysis?.result.case_specific_analysis?.traditional_knowledge;
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const nodes: Node[] = useMemo(() => {
    if (!graph) return [];
    const columns: Record<string, number> = { traditional_text: 40, ingredient: 320, case_document: 630, paper: 630, patent: 630, invention: 960 };
    const counts: Record<string, number> = {};
    return graph.nodes.map((item) => {
      const count = counts[item.type] ?? 0;
      counts[item.type] = count + 1;
      const highlighted = item.type === "invention";
      return {
        id: item.id,
        position: { x: columns[item.type] ?? 320, y: 80 + count * 145 },
        data: { label: item.label, itemType: item.type, risk: item.risk },
        style: {
          width: 230,
          borderRadius: 16,
          border: highlighted ? "2px solid #0F6B5C" : "1px solid #E1E5E1",
          background: highlighted ? "#E4F2EE" : "#FFFFFF",
          color: "#16212B",
          fontSize: 12,
          lineHeight: 1.5,
          padding: 16,
          boxShadow: "0 4px 18px rgba(22,33,43,.06)",
        },
      };
    });
  }, [graph]);
  const edges: Edge[] = useMemo(() => graph?.edges.map((edge) => ({ id: edge.id, source: edge.source, target: edge.target, label: edge.label, type: "smoothstep", style: { stroke: "#0F6B5C", strokeWidth: 1.4 }, labelStyle: { fontSize: 9, fill: "#5B6660" } })) ?? [], [graph]);
  const selected = graph?.nodes.find((node) => node.id === selectedId);

  return (
    <div className="py-8 md:py-10">
      <ModuleHeader eyebrow="Traditional Knowledge / Prior Art" title="Trace what was known before the invention." description="Map the relationship between biological ingredients, traditional texts, scientific literature, patent families and the current innovation." />
      {!graph ? <AnalysisState loading={loading} error={error} /> : (
        <>
          {tk && <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8">
            <div className="flex flex-col justify-between gap-5 md:flex-row md:items-start"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Exact passage register</p><h2 className="mt-2 text-2xl font-semibold">Formulations and locations, not generic matches</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-ink-muted">{tk.limitation}</p></div><a href={tk.search_url} target="_blank" rel="noreferrer" className="rounded-xl border border-accent px-4 py-2 text-xs font-semibold text-accent">Open authorized-search entry point ↗</a></div>
            {tk.records.length === 0 ? <div className="mt-6 rounded-2xl border border-warm/30 bg-warm-subtle p-5"><p className="text-sm font-semibold text-warm">No exact traditional-knowledge passage was retrieved.</p><p className="mt-2 text-xs leading-5 text-ink-muted">This does not mean the formulation or use is absent from prior art. Upload an authorized text extract with page/verse data or complete a qualified TKDL search.</p></div> : <div className="mt-6 grid gap-4 lg:grid-cols-2">{tk.records.map((record, index) => <article key={`${record.content_sha256}-${index}`} className="rounded-2xl border border-border bg-background p-5"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-semibold">{record.source_title}</p><span className="font-mono text-[9px] uppercase text-accent">{record.locator ?? "locator unavailable"}</span></div><p className="mt-3 text-xs font-medium text-ink">{record.formulation}</p><blockquote className="mt-3 border-l-2 border-accent pl-4 text-xs leading-6 text-ink-muted">{record.exact_passage}</blockquote><p className="mt-3 font-mono text-[9px] text-ink-muted">SHA-256 {record.content_sha256?.slice(0, 18) ?? "not available"}…</p><button type="button" onClick={() => void openCitation(record.citation)} className="mt-3 text-xs font-semibold text-accent hover:underline">Open exact source location ↗</button></article>)}</div>}
          </section>}
          <div className="mt-6 flex flex-wrap gap-2">{["Traditional text", "Ingredient", "Scientific paper", "Patent", "Your invention"].map((label) => <span key={label} className="rounded-full border border-border bg-surface px-3 py-1.5 text-xs text-ink-muted">{label}</span>)}</div>
          <section className="mt-6 grid gap-6 lg:grid-cols-[1fr_350px]">
            <div className="h-[690px] overflow-hidden rounded-3xl border border-border bg-surface"><ReactFlow nodes={nodes} edges={edges} fitView fitViewOptions={{ padding: 0.18 }} onNodeClick={(_, node) => setSelectedId(node.id)}><Background gap={24} size={1} color="#E1E5E1" /><MiniMap pannable zoomable nodeColor="#0F6B5C" /><Controls /></ReactFlow></div>
            <aside className="rounded-3xl border border-border bg-surface p-6">{selected ? <><div className="flex justify-between gap-3"><span className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Selected node</span><button type="button" onClick={() => setSelectedId(null)} className="text-xs text-ink-muted">Close</button></div><h2 className="mt-4 text-2xl font-semibold">{selected.label}</h2><div className="mt-4 flex gap-2"><span className="rounded-full bg-accent-subtle px-2.5 py-1 text-[10px] font-medium text-accent">{selected.type.replaceAll("_", " ")}</span><span className="rounded-full bg-warm-subtle px-2.5 py-1 text-[10px] font-medium text-warm">{selected.risk}</span></div><p className="mt-6 text-sm leading-7 text-ink-muted">This node is a screening relationship, not a definitive prior-art search result. Review the dated source record before relying on it.</p></> : <><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Knowledge lineage</p><h2 className="mt-3 text-2xl font-semibold">Select a graph node.</h2><p className="mt-3 text-sm leading-7 text-ink-muted">Inspect how each source or component connects to the invention.</p></>}
              <div className="mt-7 border-t border-border pt-6"><p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-muted">Current findings</p><div className="mt-3 space-y-3">{graph.findings.map((finding) => <p key={finding} className="rounded-xl border border-border bg-background p-3 text-xs leading-5 text-ink-muted">{finding}</p>)}</div></div>
              <div className="mt-6 space-y-2">{graph.citations.map((source) => <button type="button" onClick={() => void openCitation(source)} key={source.id} className="block text-left text-xs font-medium text-accent hover:underline">{source.title}{source.locator ? ` · ${source.locator}` : ""} ↗</button>)}</div>
            </aside>
          </section>
        </>
      )}
    </div>
  );
}
