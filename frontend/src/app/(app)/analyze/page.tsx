"use client";

import { useState } from "react";
import Link from "next/link";
import {
  MOCK_CASE,
  MOCK_GENOME_NODES,
} from "@/lib/mock-data";

export default function AnalyzeInnovationPage() {
  const [description, setDescription] = useState("");
  const [showDetails, setShowDetails] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzed, setAnalyzed] = useState(false);

  function handleAnalyze() {
    if (!description.trim()) return;

    setAnalyzing(true);
    setAnalyzed(false);

    setTimeout(() => {
      setAnalyzing(false);
      setAnalyzed(true);
    }, 1800);
  }

  return (
    <main className="min-h-screen bg-background text-ink">
      <div className="mx-auto max-w-6xl px-6 py-10 md:px-10 md:py-14">
        {/* HEADER */}
        <header className="border-b border-border pb-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
            IP-SAKTI 360 / Analyze Innovation
          </p>

          <h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">
            Tell us about your innovation.
          </h1>

          <p className="mt-3 max-w-2xl text-base leading-7 text-ink-muted">
            Describe your product in your own words. We&apos;ll break it down
            into the knowledge, evidence, IP and regulatory questions that
            matter.
          </p>
        </header>

        {/* MAIN INPUT */}
        <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8">
          <div>
            <label
              htmlFor="innovation"
              className="text-sm font-medium text-ink"
            >
              What are you building?
            </label>

            <textarea
              id="innovation"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Describe your formulation, process, product or invention..."
              className="mt-3 min-h-56 w-full resize-none rounded-2xl border border-border bg-background p-5 text-base leading-7 outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
            />
          </div>

          {/* OPTIONS */}
          <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Field label="Jurisdiction" value={MOCK_CASE.jurisdiction} />
            <Field label="Product form" value="Film-coated tablet" />
            <Field label="Intended use" value="Stress management" />
            <Field label="Target market" value="India" />
          </div>

          {/* MORE DETAILS */}
          <button
            type="button"
            onClick={() => setShowDetails(!showDetails)}
            className="mt-6 text-sm font-medium text-accent"
          >
            {showDetails ? "Hide additional details ↑" : "Add more details ↓"}
          </button>

          {showDetails && (
            <div className="mt-5 grid gap-4 border-t border-border pt-5 md:grid-cols-2">
              <Field label="Classical formulation?" value="No" />
              <Field
                label="Biological-resource sourcing"
                value="Madhya Pradesh"
              />
              <Field label="Manufacturing process" value="Co-extraction" />
              <Field label="Brand / product name" value="Not provided" />
            </div>
          )}

          {/* ACTION */}
          <div className="mt-7 flex flex-col gap-4 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs leading-5 text-ink-muted">
              Your description helps us identify what needs to be checked.
            </p>

            <button
              type="button"
              onClick={handleAnalyze}
              disabled={!description.trim() || analyzing}
              className="inline-flex h-12 items-center justify-center rounded-xl bg-accent px-7 text-sm font-medium text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {analyzing ? "Analyzing your innovation..." : "Analyze innovation →"}
            </button>
          </div>
        </section>

        {/* ANALYSIS RESULT */}
        {(analyzing || analyzed) && (
          <section className="mt-8">
            {analyzing ? (
              <AnalysisLoading />
            ) : (
              <AnalysisWorkspace />
            )}
          </section>
        )}

        {/* EMPTY STATE / EXAMPLE */}
        {!analyzing && !analyzed && (
          <section className="mt-8 grid gap-4 md:grid-cols-3">
            <InfoCard
              number="01"
              title="What is already known?"
              text="Traditional knowledge, prior art and existing uses."
            />

            <InfoCard
              number="02"
              title="What may be new?"
              text="Potentially inventive parts of your product or process."
            />

            <InfoCard
              number="03"
              title="What needs checking?"
              text="Evidence, IP, regulation and biological-resource obligations."
            />
          </section>
        )}

        {/* EXISTING CASE QUICK LOAD */}
        <div className="mt-8 flex items-center justify-between rounded-2xl border border-border bg-surface px-5 py-4">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-muted">
              Existing case
            </p>

            <p className="mt-1 text-sm font-medium">
              {MOCK_CASE.name}
            </p>
          </div>

          <button
            type="button"
            onClick={() => setDescription(MOCK_CASE.productDescription)}
            className="text-sm font-medium text-accent hover:underline"
          >
            Load example
          </button>
        </div>
      </div>
    </main>
  );
}

function Field({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-background p-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">
        {label}
      </p>

      <p className="mt-2 text-sm font-medium">{value}</p>
    </div>
  );
}

function InfoCard({
  number,
  title,
  text,
}: {
  number: string;
  title: string;
  text: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-6">
      <span className="font-mono text-xs font-semibold text-accent">
        {number}
      </span>

      <h2 className="mt-8 text-lg font-semibold tracking-tight">
        {title}
      </h2>

      <p className="mt-2 text-sm leading-6 text-ink-muted">
        {text}
      </p>
    </div>
  );
}

function AnalysisLoading() {
  const steps = [
    "Understanding your product",
    "Breaking down the innovation",
    "Mapping traditional knowledge",
    "Checking evidence and IP",
    "Assessing regulatory questions",
  ];

  return (
    <div className="rounded-3xl border border-border bg-surface p-7 md:p-9">
      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
        Analysis in progress
      </p>

      <h2 className="mt-3 text-2xl font-semibold tracking-tight">
        Looking into your innovation...
      </h2>

      <div className="mt-7 space-y-4">
        {steps.map((step, index) => (
          <div key={step} className="flex items-center gap-4">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-subtle font-mono text-[10px] font-semibold text-accent">
              {String(index + 1).padStart(2, "0")}
            </span>

            <span className="text-sm text-ink-muted">{step}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AnalysisWorkspace() {
  return (
    <div className="space-y-6">
      {/* RESULT HEADER */}
      <div className="rounded-3xl border border-border bg-surface p-6 md:p-8">
        <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
              Analysis complete
            </p>

            <h2 className="mt-2 text-3xl font-semibold tracking-tight">
              Your innovation map is ready.
            </h2>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
              We&apos;ve separated the known, the supported, the uncertain
              and the potentially inventive.
            </p>
          </div>

          <span className="rounded-full bg-accent-subtle px-3 py-1.5 text-xs font-medium text-accent">
            Evidence-first
          </span>
        </div>
      </div>

      {/* WORKSPACE */}
      <div className="grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
        {/* GENOME */}
        <div className="rounded-3xl border border-border bg-surface p-6 md:p-8">
          <div className="flex items-end justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
                Innovation Genome
              </p>

              <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                What we found
              </h2>
            </div>

            <span className="font-mono text-xs text-ink-muted">
              {MOCK_GENOME_NODES.length} findings
            </span>
          </div>

          <div className="mt-6 space-y-3">
            {MOCK_GENOME_NODES.map((node) => (
              <div
                key={node.id}
                className="rounded-2xl border border-border p-4 transition hover:bg-background"
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-sm font-medium">{node.label}</p>

                    <p className="mt-1 text-xs leading-5 text-ink-muted">
                      {node.description}
                    </p>
                  </div>

                  <div className="flex shrink-0 gap-2">
                    <StatusBadge
                      label={node.layer}
                      tone="accent"
                    />

                    <StatusBadge
                      label={node.status.replace("-", " ")}
                      tone={
                        node.status === "inventive"
                          ? "success"
                          : node.status === "needs-evidence" ||
                              node.status === "uncertain"
                            ? "warn"
                            : "neutral"
                      }
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* SUMMARY */}
        <div className="space-y-4">
          <SummaryCard
            title="Traditional Knowledge"
            value="Review"
            text="Existing traditional uses were identified."
          />

          <SummaryCard
            title="Patent Opportunity"
            value="Promising"
            text="A potentially inventive process has been identified."
          />

          <SummaryCard
            title="Evidence Strength"
            value="Mixed"
            text="Some claims are supported; others need more evidence."
          />

          <SummaryCard
            title="ABS Review"
            value="Required"
            text="Biological-resource sourcing needs review."
          />

          <Link
            href="/ip-strategy"
            className="flex items-center justify-between rounded-2xl bg-accent px-5 py-4 text-sm font-medium text-white transition hover:bg-accent/90"
          >
            Explore your IP strategy
            <span>→</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({
  title,
  value,
  text,
}: {
  title: string;
  value: string;
  text: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-ink-muted">
        {title}
      </p>

      <p className="mt-3 text-xl font-semibold tracking-tight">
        {value}
      </p>

      <p className="mt-2 text-xs leading-5 text-ink-muted">
        {text}
      </p>
    </div>
  );
}

function StatusBadge({
  label,
  tone,
}: {
  label: string;
  tone: "neutral" | "accent" | "warn" | "success";
}) {
  const styles = {
    neutral: "bg-ink/5 text-ink-muted",
    accent: "bg-accent-subtle text-accent",
    warn: "bg-warm-subtle text-warm",
    success: "bg-success/10 text-success",
  };

  return (
    <span
      className={`rounded-full px-2.5 py-1 text-[10px] font-medium capitalize ${styles[tone]}`}
    >
      {label}
    </span>
  );
}