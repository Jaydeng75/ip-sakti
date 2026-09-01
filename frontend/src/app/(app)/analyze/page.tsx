"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AnalysisResponse, caseApi } from "@/lib/api";
import { saveCaseSnapshot } from "@/lib/case-store";
import { EXAMPLE_CASE } from "@/lib/case-data";
import { notifyAnalysisUpdated } from "@/lib/use-current-analysis";

const EXAMPLE = {
  description: EXAMPLE_CASE.productDescription,
  ingredients: EXAMPLE_CASE.ingredients.join("\n"),
  productForm: "Film-coated tablet",
  intendedUse: "Daily stress management and mental resilience support",
  targetMarkets: "India, European Union, United States",
  sourcing: "Cultivated Indian botanical resources sourced through documented domestic suppliers",
  manufacturing: "Separate hydroethanolic extraction, vacuum concentration below 55°C, fixed-ratio blending and aqueous film coating",
  quantitativeComposition: "Per tablet: Withania somnifera root extract 300 mg; Bacopa monnieri whole-plant extract 150 mg; Ocimum tenuiflorum leaf extract 100 mg",
  standardization: "Withania: 5% total withanolides; Bacopa: 20% bacosides; Tulsi: 2% ursolic acid",
  extractionRatio: "Withania 10:1, Bacopa 8:1, Tulsi 5:1; 70:30 ethanol:water extracts",
  dose: "One tablet twice daily after food for 8 weeks; total daily extract exposure 1,100 mg",
  releaseProfile: "Target: 20–35% marker release at 2 h, 55–75% at 6 h and at least 85% at 12 h in the proposed dissolution method",
  processParameters: "Extraction 50–55°C for 4 h; concentrate under vacuum; blend 18 min at 12 rpm; film-coat weight gain 3.0–3.5%",
  proposedClaim: "Supports stress resilience in adults with perceived stress, measured after 8 weeks, without a disease-treatment claim",
  classicalReference: "",
  brand: "",
  classical: false,
};

export default function AnalyzeInnovationPage() {
  const [form, setForm] = useState({
    description: "",
    ingredients: "",
    productForm: "",
    intendedUse: "",
    targetMarkets: "India",
    sourcing: "",
    manufacturing: "",
    quantitativeComposition: "",
    standardization: "",
    extractionRatio: "",
    dose: "",
    releaseProfile: "",
    processParameters: "",
    proposedClaim: "",
    classicalReference: "",
    brand: "",
    classical: false,
  });
  const [showDetails, setShowDetails] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const draft = window.sessionStorage.getItem("ip-sakti-analysis-draft");
    if (draft) {
      window.sessionStorage.removeItem("ip-sakti-analysis-draft");
      window.setTimeout(() => setForm((current) => ({ ...current, description: draft })), 0);
    }
  }, []);

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setAnalysis(null);
  }

  async function handleAnalyze() {
    if (form.description.trim().length < 20 || analyzing) return;
    setAnalyzing(true);
    setError(null);
    try {
      const title = form.description.trim().split(/[.!?\n]/)[0].slice(0, 110) || "Untitled innovation";
      const ingredients = form.ingredients
        .split(/\n/)
        .map((item) => item.trim())
        .filter(Boolean);
      const markets = form.targetMarkets
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      const created = await caseApi.create({
        title,
        description: form.description.trim(),
        ingredients,
        product_form: form.productForm || null,
        intended_use: form.intendedUse || null,
        target_markets: markets.length ? markets : ["India"],
        classical_formulation: form.classical,
        biological_sourcing: form.sourcing || null,
        metadata_json: {
          manufacturing_process: form.manufacturing,
          quantitative_composition: form.quantitativeComposition,
          standardization: form.standardization,
          extraction_ratio: form.extractionRatio,
          dose: form.dose,
          release_profile: form.releaseProfile,
          process_parameters: form.processParameters,
          proposed_claim: form.proposedClaim,
          classical_reference: form.classicalReference,
          brand: form.brand,
        },
      });
      const nextAnalysis = await caseApi.analyze(created.id);
      saveCaseSnapshot({
        id: `case-ip360-${created.id}`,
        backendId: created.id,
        title: created.title,
        productDescription: created.description,
        ingredients: created.ingredients,
        jurisdiction: created.target_markets.join(" · "),
        productType: nextAnalysis.result.classification.label,
        createdAt: created.created_at,
        updatedAt: created.updated_at,
        status: "analyzed",
      });
      setAnalysis(nextAnalysis);
      notifyAnalysisUpdated();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The analysis could not be completed.");
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <div className="py-8 md:py-10">
      <header className="border-b border-border pb-8">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">IP-SAKTI 360 / Analyze Innovation</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">Build an evidence-grounded innovation case.</h1>
        <p className="mt-3 max-w-3xl text-base leading-7 text-ink-muted">
          Describe the invention once, add the facts that affect classification and rights, then move through every module without losing case context.
        </p>
      </header>

      <section className="mt-8 rounded-3xl border border-border bg-surface p-6 shadow-sm md:p-8">
        <label htmlFor="innovation" className="text-sm font-semibold text-ink">Product, process or invention</label>
        <textarea
          id="innovation"
          value={form.description}
          onChange={(event) => update("description", event.target.value)}
          placeholder="Describe the formulation, technical differentiation, dose or delivery mechanism, proposed claims and sourcing..."
          className="mt-3 min-h-56 w-full resize-y rounded-2xl border border-border bg-background p-5 text-base leading-7 outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
        />

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <TextField label="Ingredients (one per line)" value={form.ingredients} onChange={(value) => update("ingredients", value)} placeholder="Withania somnifera root extract" multiline />
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label="Product form" value={form.productForm} onChange={(value) => update("productForm", value)} placeholder="Tablet, cream, extract..." />
            <TextField label="Target markets" value={form.targetMarkets} onChange={(value) => update("targetMarkets", value)} placeholder="India, EU, US" />
            <div className="sm:col-span-2">
              <TextField label="Intended use / claim" value={form.intendedUse} onChange={(value) => update("intendedUse", value)} placeholder="Exact consumer or therapeutic purpose" />
            </div>
          </div>
        </div>

        <button type="button" onClick={() => setShowDetails((value) => !value)} className="mt-6 text-sm font-semibold text-accent">
          {showDetails ? "Hide sourcing and technical details ↑" : "Add sourcing and technical details ↓"}
        </button>

        {showDetails && (
          <div className="mt-5 grid gap-4 border-t border-border pt-5 md:grid-cols-2">
            <div className="md:col-span-2 rounded-2xl border border-accent/20 bg-accent-subtle p-4">
              <p className="text-sm font-semibold text-accent">Specificity inputs</p>
              <p className="mt-1 text-xs leading-5 text-ink-muted">These values drive feature-level patent comparison, exposure-matched science, regulatory classification and evidence-backed design-around options.</p>
            </div>
            <TextField label="Quantitative composition" value={form.quantitativeComposition} onChange={(value) => update("quantitativeComposition", value)} placeholder="Amount of every active per tablet, capsule, mL or daily dose" multiline />
            <TextField label="Standardization / fingerprint" value={form.standardization} onChange={(value) => update("standardization", value)} placeholder="Marker compounds and acceptance ranges" multiline />
            <TextField label="Extraction ratio and solvent" value={form.extractionRatio} onChange={(value) => update("extractionRatio", value)} placeholder="DER or ratio, solvent system and extract type" />
            <TextField label="Dose, frequency and duration" value={form.dose} onChange={(value) => update("dose", value)} placeholder="Example: 300 mg twice daily for 8 weeks" />
            <TextField label="Release / performance profile" value={form.releaseProfile} onChange={(value) => update("releaseProfile", value)} placeholder="Method, timepoints and target acceptance ranges" multiline />
            <TextField label="Critical process parameters" value={form.processParameters} onChange={(value) => update("processParameters", value)} placeholder="Temperature, time, pH, pressure and defined ranges" multiline />
            <TextField label="Exact proposed claim" value={form.proposedClaim} onChange={(value) => update("proposedClaim", value)} placeholder="Population, outcome, duration and exact claim wording" multiline />
            <TextField label="Exact classical reference" value={form.classicalReference} onChange={(value) => update("classicalReference", value)} placeholder="Text, chapter, formulation, verse and page" multiline />
            <TextField label="Biological-resource sourcing" value={form.sourcing} onChange={(value) => update("sourcing", value)} placeholder="Species, source location, supplier and access date" />
            <TextField label="Manufacturing / technical process" value={form.manufacturing} onChange={(value) => update("manufacturing", value)} placeholder="Extraction, standardization, delivery or process steps" />
            <TextField label="Brand / product name" value={form.brand} onChange={(value) => update("brand", value)} placeholder="Optional" />
            <label className="flex min-h-20 cursor-pointer items-center gap-3 rounded-xl border border-border bg-background p-4 text-sm">
              <input type="checkbox" checked={form.classical} onChange={(event) => update("classical", event.target.checked)} className="h-4 w-4 accent-[var(--accent)]" />
              <span><strong className="block">Derived from a classical formulation</strong><span className="mt-1 block text-xs text-ink-muted">This raises a traditional-knowledge and prior-art review flag.</span></span>
            </label>
          </div>
        )}

        {error && <div role="alert" className="mt-5 rounded-xl border border-danger/30 bg-danger-subtle p-4 text-sm text-danger">{error} Check that the backend is running at the configured API URL.</div>}

        <div className="mt-7 flex flex-col gap-4 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
          <button type="button" onClick={() => { setForm(EXAMPLE); setShowDetails(true); }} className="text-left text-sm font-medium text-accent hover:underline">Load complete example</button>
          <button type="button" onClick={handleAnalyze} disabled={form.description.trim().length < 20 || analyzing} className="inline-flex h-12 items-center justify-center rounded-xl bg-accent px-7 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-40">
            {analyzing ? "Running grounded analysis…" : "Analyze innovation →"}
          </button>
        </div>
      </section>

      {analyzing && <AnalysisLoading />}
      {analysis && <AnalysisWorkspace analysis={analysis} />}
    </div>
  );
}

function TextField({ label, value, onChange, placeholder, multiline = false }: { label: string; value: string; onChange: (value: string) => void; placeholder: string; multiline?: boolean }) {
  const className = "mt-2 w-full rounded-xl border border-border bg-background px-4 py-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10";
  return (
    <label className="block text-xs font-medium text-ink-muted">
      {label}
      {multiline ? <textarea value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className={`${className} min-h-36 resize-y`} /> : <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className={className} />}
    </label>
  );
}

function AnalysisLoading() {
  return (
    <section aria-live="polite" className="mt-8 rounded-3xl border border-border bg-surface p-8">
      <div className="h-1.5 overflow-hidden rounded-full bg-accent-subtle"><div className="h-full w-2/3 animate-pulse rounded-full bg-accent" /></div>
      <p className="mt-5 font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Grounded analysis in progress</p>
      <h2 className="mt-2 text-2xl font-semibold">Classifying the product and mapping the innovation genome…</h2>
      <p className="mt-2 text-sm text-ink-muted">Checking traditional knowledge, scientific evidence, IP routes, regulation, ABS and market-specific concerns.</p>
    </section>
  );
}

function AnalysisWorkspace({ analysis }: { analysis: AnalysisResponse }) {
  const result = analysis.result;
  const specific = result.case_specific_analysis;
  return (
    <section className="mt-8 space-y-6">
      <div className="rounded-3xl border border-accent/25 bg-accent-subtle p-6 md:p-8">
        <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
          <div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Analysis complete · corpus {result.corpus_version}</p><h2 className="mt-2 text-3xl font-semibold">Your innovation workspace is ready.</h2><p className="mt-3 max-w-3xl text-sm leading-6 text-ink-muted">{result.executive_summary}</p></div>
          <div className="rounded-xl border border-accent/20 bg-surface px-4 py-3 text-right"><p className="font-mono text-[10px] text-ink-muted">SCREENING CONFIDENCE</p><p className="mt-1 text-lg font-semibold text-accent">{Math.round(result.confidence.score * 100)}%</p></div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-3xl border border-border bg-surface p-6 md:p-8">
          <div className="flex items-end justify-between"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Innovation Genome</p><h3 className="mt-2 text-2xl font-semibold">Technical and knowledge components</h3></div><span className="font-mono text-xs text-ink-muted">{result.genome.nodes.length} nodes</span></div>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            {result.genome.nodes.filter((node) => node.id !== "invention").map((node) => (
              <div key={node.id} className="rounded-2xl border border-border bg-background p-4"><div className="flex items-start justify-between gap-3"><p className="font-mono text-[9px] uppercase tracking-[0.14em] text-accent">{node.type.replaceAll("_", " ")}</p><Status level={node.status} /></div><p className="mt-3 text-sm font-medium leading-6">{node.label}</p></div>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          {result.risk_cards.map((card) => (
            <div key={card.key} className="rounded-2xl border border-border bg-surface p-5"><div className="flex items-start justify-between gap-4"><div><p className="text-sm font-semibold">{card.title}</p><p className="mt-2 text-xs font-medium leading-5 text-ink">{card.finding ?? card.primary_finding}</p><p className="mt-2 text-xs leading-5 text-ink-muted">{card.fix ?? card.summary}</p></div><div className="text-right"><p className="text-lg font-semibold text-accent">{card.display_value ?? card.score}</p><p className="font-mono text-[9px] uppercase text-ink-muted">{card.level}</p></div></div></div>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[0.72fr_1.28fr]">
        <div className="rounded-3xl border border-border bg-[#16212B] p-6 text-white md:p-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/50">Decision-input completeness</p>
          <p className="mt-4 text-5xl font-semibold text-[#9BD0C0]">{specific.input_completeness.score}%</p>
          <p className="mt-3 text-sm text-white/70">{specific.input_completeness.supplied_count} of {specific.input_completeness.required_count} critical facts supplied.</p>
          <div className="mt-6 space-y-2">{specific.input_completeness.missing.slice(0, 4).map((item) => <div key={item.key} className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-xs font-semibold">Missing: {item.label}</p><p className="mt-1 text-[11px] leading-5 text-white/55">{item.request}</p></div>)}</div>
        </div>
        <div className="rounded-3xl border border-border bg-surface p-6 md:p-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Case-specific recommendations</p>
          <h3 className="mt-2 text-2xl font-semibold">Advice tied to submitted facts</h3>
          <div className="mt-5 space-y-3">{specific.specific_recommendations.slice(0, 5).map((item, index) => <article key={`${item.title}-${index}`} className="rounded-2xl border border-border bg-background p-4"><div className="flex gap-3"><span className="font-mono text-[10px] text-accent">{String(index + 1).padStart(2, "0")}</span><div><p className="text-sm font-semibold">{item.title}</p><p className="mt-1 text-xs leading-5 text-accent">Basis: {item.basis}</p><p className="mt-2 text-xs leading-5 text-ink-muted">{item.action}</p><p className="mt-2 text-[11px] font-medium text-ink">Output: {item.decision_output}</p></div></div></article>)}</div>
        </div>
      </div>

      <div className="rounded-3xl border border-border bg-surface p-6 md:p-8">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Provisional classification</p><h3 className="mt-2 text-2xl font-semibold">{result.classification.label}</h3><p className="mt-3 max-w-3xl text-sm leading-6 text-ink-muted">{result.classification.pathway}</p></div><span className="rounded-full bg-warm-subtle px-3 py-1.5 text-xs font-medium text-warm">Human review required</span></div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{[["Traditional Knowledge", "/traditional-knowledge"], ["Scientific Evidence", "/evidence"], ["IP Strategy", "/ip-strategy"], ["Challenge My Innovation", "/challenge"]].map(([label, href]) => <Link key={href} href={href} className="rounded-xl border border-border bg-background p-4 text-sm font-semibold transition hover:border-accent hover:text-accent">{label} →</Link>)}</div>
      </div>

      <p className="rounded-xl border border-border bg-background p-4 text-xs leading-5 text-ink-muted">{result.warnings[0]}</p>
    </section>
  );
}

function Status({ level }: { level: string }) {
  return <span className="rounded-full bg-accent-subtle px-2 py-1 font-mono text-[9px] uppercase text-accent">{level.replaceAll("_", " ")}</span>;
}
