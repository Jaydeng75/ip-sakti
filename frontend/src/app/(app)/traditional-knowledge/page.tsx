"use client";

import { useMemo, useState } from "react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { AnalysisState, ModuleHeader } from "@/components/analysis-state";
import { caseApi, openCitation } from "@/lib/api";
import { notifyAnalysisUpdated, useCurrentAnalysis } from "@/lib/use-current-analysis";
import { useCurrentCase } from "@/lib/use-current-case";

const TKDL_SEARCH_URL = "https://www.tkdl.res.in/tkdl/langdefault/common/TKDLSearch.asp?GL=Eng";

export default function TraditionalKnowledgePage() {
  const { analysis, loading, error, refresh } = useCurrentAnalysis();
  const currentCase = useCurrentCase();
  const graph = analysis?.result.knowledge_graph;
  const tk = analysis?.result.case_specific_analysis?.traditional_knowledge;
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [authorizedImport, setAuthorizedImport] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [bridgeStatus, setBridgeStatus] = useState<string | null>(null);
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

  async function copyQuery() {
    if (!tk?.query) return;
    await navigator.clipboard.writeText(tk.query);
    setBridgeStatus("Case-specific TKDL search terms copied.");
  }

  async function importAuthorizedResult(file: File) {
    if (!currentCase.backendId || !authorizedImport) return;
    setProcessing(true);
    setBridgeStatus("Importing, indexing and extracting exact TK passages…");
    try {
      const document = await caseApi.uploadDocument(currentCase.backendId, file);
      setBridgeStatus(`Indexed ${document.filename} into ${document.chunk_count} traceable passage(s). Refreshing the case analysis…`);
      await caseApi.analyze(currentCase.backendId);
      notifyAnalysisUpdated();
      await refresh();
      setBridgeStatus(`Authorized source imported: ${document.filename}. Exact matches now retain page/chunk and SHA-256 lineage.`);
    } catch (caught) {
      setBridgeStatus(caught instanceof Error ? caught.message : "The TKDL result could not be imported.");
    } finally {
      setProcessing(false);
    }
  }

  return (
    <div className="py-8 md:py-10">
      <ModuleHeader eyebrow="Traditional Knowledge / Prior Art" title="Trace what was known before the invention." description="Map the relationship between biological ingredients, traditional texts, scientific literature, patent families and the current innovation." />
      {!graph ? <AnalysisState loading={loading} error={error} /> : (
        <>
          {tk && <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8">
            <div className="flex flex-col justify-between gap-5 md:flex-row md:items-start"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">TKDL Bridge</p><h2 className="mt-2 text-2xl font-semibold">Official search → authorized import → exact citation</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-ink-muted">{tk.limitation}</p></div><span className="rounded-full bg-accent-subtle px-3 py-1.5 font-mono text-[9px] uppercase text-accent">Access-aware integration</span></div>
            <div className="mt-6 grid gap-3 lg:grid-cols-4">
              <TkdlStep number="01" title="Build query" detail="Botanical identities, classical reference and claimed use are kept together." />
              <TkdlStep number="02" title="Search official TKDL" detail="Continue in the official session-aware TKDL interface." />
              <TkdlStep number="03" title="Import authorized result" detail="Attach a legally obtained PDF, TXT or DOCX export or source extract." />
              <TkdlStep number="04" title="Verify exact passage" detail="Review formulation text, location, matched ingredients and content hash." />
            </div>
            <div className="mt-5 rounded-2xl border border-border bg-background p-5">
              <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
                <div><p className="font-mono text-[9px] uppercase tracking-[0.14em] text-accent">Case-specific TKDL search terms</p><p className="mt-2 max-w-3xl text-xs leading-5 text-ink-muted">{tk.query || "Add botanical names, formulation and intended use to generate a case-specific query."}</p></div>
                <div className="flex flex-wrap gap-2"><button type="button" onClick={() => void copyQuery()} disabled={!tk.query} className="rounded-xl border border-border px-4 py-2 text-xs font-semibold text-ink disabled:opacity-40">Copy query</button><a href={tk.search_url || TKDL_SEARCH_URL} target="_blank" rel="noreferrer" className="rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-white">Open official TKDL ↗</a></div>
              </div>
            </div>
            <div className="mt-4 rounded-2xl border border-warm/30 bg-warm-subtle p-5">
              <p className="text-sm font-semibold text-warm">TKDL access boundary</p>
              <p className="mt-2 text-xs leading-5 text-ink-muted">{tk.access_scope ?? "Full TKDL access is governed by the official service and applicable access agreement."} IP-SAKTI does not scrape, bypass authentication or claim that a failed search proves absence of traditional prior art.</p>
              <label className="mt-4 flex items-start gap-3 text-xs leading-5 text-ink"><input type="checkbox" checked={authorizedImport} onChange={(event) => setAuthorizedImport(event.target.checked)} className="mt-1 size-4 accent-[#0F6B5C]" /><span>I confirm that this result/export was obtained lawfully and may be processed for this case.</span></label>
              <div className="mt-4 flex flex-wrap items-center gap-3"><label className={`rounded-xl px-4 py-2.5 text-xs font-semibold text-white ${authorizedImport && currentCase.backendId && !processing ? "cursor-pointer bg-accent" : "cursor-not-allowed bg-ink-muted/40"}`}><input type="file" accept=".pdf,.txt,.docx" disabled={!authorizedImport || !currentCase.backendId || processing} className="sr-only" onChange={(event) => { const file = event.target.files?.[0]; if (file) void importAuthorizedResult(file); event.currentTarget.value = ""; }} />{processing ? "Processing authorized source…" : "Import authorized TKDL result"}</label><span className="font-mono text-[9px] uppercase text-ink-muted">PDF · TXT · DOCX · exact lineage retained</span></div>
              {bridgeStatus && <p role="status" className="mt-4 rounded-xl border border-border bg-surface p-3 text-xs leading-5 text-ink-muted">{bridgeStatus}</p>}
            </div>
            <div className="mt-8"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Exact passage register</p><h3 className="mt-2 text-xl font-semibold">Formulations and locations, not generic matches</h3></div>
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

function TkdlStep({ number, title, detail }: { number: string; title: string; detail: string }) {
  return <div className="rounded-2xl border border-border bg-background p-4"><span className="font-mono text-[9px] text-accent">{number}</span><p className="mt-3 text-sm font-semibold">{title}</p><p className="mt-2 text-xs leading-5 text-ink-muted">{detail}</p></div>;
}
