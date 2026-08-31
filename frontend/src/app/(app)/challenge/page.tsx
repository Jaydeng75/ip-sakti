"use client";

import { useMemo, useState } from "react";
import { AnalysisState, ModuleHeader } from "@/components/analysis-state";
import { caseApi } from "@/lib/api";
import { useCurrentAnalysis } from "@/lib/use-current-analysis";
import { useCurrentCase } from "@/lib/use-current-case";

const reviewerLabels: Record<string, string> = {
  patent_examiner: "Patent Examiner",
  regulatory_reviewer: "Regulatory Reviewer",
  abs_reviewer: "ABS Reviewer",
  scientific_evidence_reviewer: "Scientific Evidence Reviewer",
};

export default function ChallengeInnovationPage() {
  const currentCase = useCurrentCase();
  const { analysis, loading, error } = useCurrentAnalysis();
  const challenges = analysis?.result.challenges;
  const keys = useMemo(() => Object.keys(challenges ?? {}), [challenges]);
  const [active, setActive] = useState("patent_examiner");
  const [reviewStatus, setReviewStatus] = useState<string | null>(null);
  const selected = challenges?.[active] ?? challenges?.[keys[0]];
  return (
    <div className="py-8 md:py-10">
      <ModuleHeader eyebrow="Challenge My Innovation" title="Try to break the idea before a reviewer does." description="Simulate adversarial patent, regulatory, ABS and scientific review to expose objections, missing facts and concrete next actions." />
      {!challenges || !selected ? <AnalysisState loading={loading} error={error} /> : (
        <>
          <section className="mt-8 rounded-3xl border border-border bg-surface p-6"><div className="flex flex-col justify-between gap-5 md:flex-row md:items-start"><div><p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-muted">Innovation under review</p><h2 className="mt-2 text-2xl font-semibold">{currentCase.title}</h2><p className="mt-3 max-w-3xl text-sm leading-7 text-ink-muted">{currentCase.productDescription}</p></div><span className="rounded-full bg-danger/10 px-3 py-1.5 text-xs font-medium text-danger">Adversarial mode</span></div></section>
          <section className="mt-8 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{keys.map((key) => <button key={key} type="button" onClick={() => setActive(key)} className={`rounded-2xl border p-5 text-left transition ${key === active ? "border-accent bg-accent-subtle" : "border-border bg-surface hover:bg-background"}`}><span className="font-mono text-[9px] uppercase text-ink-muted">Reviewer</span><p className="mt-3 text-sm font-semibold">{reviewerLabels[key] ?? key.replaceAll("_", " ")}</p><p className={`mt-2 text-xs ${key === active ? "text-accent" : "text-ink-muted"}`}>{challenges[key].length} objections</p></button>)}</section>
          <section className="mt-8 grid gap-6 lg:grid-cols-[1.25fr_0.75fr]"><div className="rounded-3xl border border-border bg-surface p-6 md:p-8"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">{reviewerLabels[active]}</p><h2 className="mt-2 text-2xl font-semibold">Adversarial review findings</h2><div className="mt-7 space-y-5">{selected.map((finding, index) => <article key={`${finding.objection}-${index}`} className="rounded-2xl border border-border bg-background p-5"><div className="flex items-start justify-between gap-4"><span className="font-mono text-[10px] text-ink-muted">OBJECTION {String(index + 1).padStart(2, "0")}</span><span className={finding.severity === "high" ? "rounded-full bg-danger/10 px-2.5 py-1 text-[10px] font-medium text-danger" : "rounded-full bg-warm-subtle px-2.5 py-1 text-[10px] font-medium text-warm"}>{finding.severity} severity</span></div><ReviewRow label="Likely objection" text={finding.objection} tone="danger" /><ReviewRow label="Missing evidence / fact" text={finding.missing} tone="warn" /><ReviewRow label="Recommended next step" text={finding.next_step} tone="accent" /></article>)}</div></div><aside className="rounded-3xl border border-border bg-[#16212B] p-7 text-white"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/50">Stress-test posture</p><h2 className="mt-3 text-2xl font-semibold">Assume the burden is yours.</h2><p className="mt-3 text-sm leading-7 text-white/65">The reviewer will not infer novelty, efficacy, lawful resource access or correct classification from an incomplete description. Turn each objection into a dated evidence record.</p><div className="mt-7 space-y-3">{analysis.result.next_actions.map((action, index) => <div key={action} className="flex gap-3 rounded-xl border border-white/10 bg-white/5 p-4"><span className="font-mono text-[9px] text-white/40">{String(index + 1).padStart(2, "0")}</span><p className="text-xs leading-5 text-white/75">{action}</p></div>)}</div>{currentCase.backendId && <button type="button" onClick={() => { setReviewStatus("Submitting review request…"); void caseApi.requestExpertReview(currentCase.backendId!, active === "patent_examiner" ? "patent" : active === "regulatory_reviewer" ? "regulatory" : active === "abs_reviewer" ? "abs" : "scientific").then(() => setReviewStatus("Expert review requested and added to the audit record.")).catch((caught: unknown) => setReviewStatus(caught instanceof Error ? caught.message : "Request failed.")); }} className="mt-6 w-full rounded-xl bg-white px-5 py-3 text-sm font-semibold text-ink">Request human expert review</button>}{reviewStatus && <p role="status" className="mt-3 text-xs leading-5 text-white/60">{reviewStatus}</p>}</aside></section>
        </>
      )}
    </div>
  );
}

function ReviewRow({ label, text, tone }: { label: string; text: string; tone: "danger" | "warn" | "accent" }) {
  const color = tone === "danger" ? "text-danger" : tone === "warn" ? "text-warm" : "text-accent";
  return <div className="mt-5 border-t border-border pt-4"><p className={`font-mono text-[9px] uppercase tracking-[0.14em] ${color}`}>{label}</p><p className="mt-2 text-sm leading-6 text-ink-muted">{text}</p></div>;
}
