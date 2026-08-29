"use client";

import { useState } from "react";

const reviewerTabs = [
  {
    id: "patent",
    label: "Patent Examiner",
    short: "Patent",
    objection:
      "The claimed formulation may rely heavily on known traditional uses of the individual ingredients.",
    weakPoint:
      "The inventive contribution needs to be separated clearly from what is already documented.",
    missingEvidence:
      "Stronger evidence supporting the novelty of the specific combination or process.",
    nextStep:
      "Define the precise technical feature that distinguishes the invention from known formulations.",
  },
  {
    id: "regulatory",
    label: "Regulatory Reviewer",
    short: "Regulatory",
    objection:
      "The intended use and product classification may create additional regulatory requirements.",
    weakPoint:
      "Some product claims could extend beyond the evidence currently available.",
    missingEvidence:
      "A clearer classification and supporting documentation for the proposed claims.",
    nextStep:
      "Confirm product classification and align all claims with the applicable regulatory framework.",
  },
  {
    id: "abs",
    label: "ABS Reviewer",
    short: "ABS",
    objection:
      "The source and collection pathway of biological resources has not been fully demonstrated.",
    weakPoint:
      "Brahmi sourcing documentation and biodiversity clearance remain unresolved.",
    missingEvidence:
      "Confirmed documentation showing the applicable biodiversity / ABS position.",
    nextStep:
      "Complete the sourcing record and confirm the relevant biodiversity authority requirements.",
  },
  {
    id: "science",
    label: "Scientific Evidence Reviewer",
    short: "Scientific",
    objection:
      "Evidence for the individual ingredients does not automatically establish efficacy for the combined formulation.",
    weakPoint:
      "The specific three-herb combination has limited direct clinical evidence.",
    missingEvidence:
      "Combination-level evidence supporting the proposed product claims.",
    nextStep:
      "Generate or obtain evidence that directly addresses the combined formulation and its claims.",
  },
];

export default function ChallengeInnovationPage() {
  const [activeTab, setActiveTab] = useState("patent");

  const reviewer =
    reviewerTabs.find((tab) => tab.id === activeTab) ?? reviewerTabs[0];

  return (
    <main className="min-h-screen bg-background text-ink">
      <div className="mx-auto max-w-6xl px-6 py-10 md:px-10 md:py-14">
        {/* HEADER */}
        <header className="border-b border-border pb-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
            IP-SAKTI 360 / Challenge My Innovation
          </p>

          <h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">
            Try to break your idea.
          </h1>

          <p className="mt-3 max-w-2xl text-base leading-7 text-ink-muted">
            See how an examiner, regulator, ABS reviewer, or scientific
            reviewer might challenge the assumptions behind your innovation.
          </p>
        </header>

        {/* CASE */}
        <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-muted">
                Innovation under review
              </p>

              <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                Herbal stress-management formulation
              </h2>

              <p className="mt-2 text-sm text-ink-muted">
                India · Ayurvedic proprietary medicine
              </p>
            </div>

            <span className="w-fit rounded-full bg-warm-subtle px-3 py-1.5 text-xs font-medium text-warm">
              Review mode
            </span>
          </div>
        </section>

        {/* REVIEWER TABS */}
        <section className="mt-8">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {reviewerTabs.map((tab) => {
              const active = tab.id === activeTab;

              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`rounded-2xl border p-5 text-left transition ${
                    active
                      ? "border-accent bg-accent-subtle"
                      : "border-border bg-surface hover:bg-background"
                  }`}
                >
                  <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-muted">
                    {tab.short}
                  </span>

                  <p className="mt-4 text-sm font-semibold tracking-tight">
                    {tab.label}
                  </p>

                  <p
                    className={`mt-2 text-xs ${
                      active ? "text-accent" : "text-ink-muted"
                    }`}
                  >
                    {active ? "Currently reviewing" : "Run review"}
                  </p>
                </button>
              );
            })}
          </div>
        </section>

        {/* REVIEW RESULT */}
        <section className="mt-8 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-3xl border border-border bg-surface p-6 md:p-8">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
                  Adversarial review
                </p>

                <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                  {reviewer.label}
                </h2>
              </div>

              <span className="rounded-full bg-danger/10 px-3 py-1.5 text-xs font-medium text-danger">
                {reviewerTabs.indexOf(reviewer) + 2} issues found
              </span>
            </div>

            <div className="mt-8 space-y-6">
              <ReviewBlock
                label="Likely objection"
                text={reviewer.objection}
                tone="danger"
              />

              <ReviewBlock
                label="Weak point"
                text={reviewer.weakPoint}
                tone="warn"
              />

              <ReviewBlock
                label="Evidence gap"
                text={reviewer.missingEvidence}
                tone="neutral"
              />

              <ReviewBlock
                label="Recommended next step"
                text={reviewer.nextStep}
                tone="accent"
              />
            </div>
          </div>

          {/* SCORE */}
          <div className="rounded-3xl border border-border bg-[#16212B] p-6 text-white md:p-8">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/50">
              Stress test
            </p>

            <h2 className="mt-3 text-2xl font-semibold tracking-tight">
              How exposed is the idea?
            </h2>

            <div className="mt-10">
              <div className="flex items-end justify-between">
                <span className="text-6xl font-semibold tracking-tight">
                  62
                </span>

                <span className="mb-2 text-sm text-white/50">
                  / 100
                </span>
              </div>

              <div className="mt-5 h-2 overflow-hidden rounded-full bg-white/10">
                <div className="h-full w-[62%] rounded-full bg-[#B86B52]" />
              </div>

              <p className="mt-4 text-sm leading-6 text-white/60">
                The innovation has promising elements, but several
                assumptions should be strengthened before external review.
              </p>
            </div>

            <div className="mt-10 space-y-3 border-t border-white/10 pt-6">
              <ScoreRow label="Novelty exposure" value="Medium" />
              <ScoreRow label="Evidence exposure" value="High" />
              <ScoreRow label="Regulatory exposure" value="Medium" />
              <ScoreRow label="ABS exposure" value="Medium" />
            </div>
          </div>
        </section>

        {/* BOTTOM */}
        <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
                Before you move forward
              </p>

              <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                Fix the weak points first.
              </h2>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
                A stronger innovation is not just one with a good idea. It is
                one that can survive scrutiny from multiple directions.
              </p>
            </div>

            <button
              type="button"
              className="rounded-xl bg-accent px-5 py-3 text-sm font-medium text-white transition hover:bg-accent/90"
            >
              Re-run challenge →
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}

function ReviewBlock({
  label,
  text,
  tone,
}: {
  label: string;
  text: string;
  tone: "danger" | "warn" | "neutral" | "accent";
}) {
  const styles = {
    danger: "border-danger/20 bg-danger/5",
    warn: "border-warm/20 bg-warm-subtle/50",
    neutral: "border-border bg-background",
    accent: "border-accent/20 bg-accent-subtle/50",
  };

  const labelStyles = {
    danger: "text-danger",
    warn: "text-warm",
    neutral: "text-ink-muted",
    accent: "text-accent",
  };

  return (
    <div className={`rounded-2xl border p-5 ${styles[tone]}`}>
      <p
        className={`font-mono text-[10px] uppercase tracking-[0.16em] ${labelStyles[tone]}`}
      >
        {label}
      </p>

      <p className="mt-3 text-sm leading-7 text-ink">
        {text}
      </p>
    </div>
  );
}

function ScoreRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <span className="text-white/60">{label}</span>

      <span className="font-medium text-white">{value}</span>
    </div>
  );
}