"use client";

import { useState } from "react";
import Link from "next/link";
import {
  MOCK_EVIDENCE,
  MOCK_IP_ROUTES,
  MOCK_REGULATORY_STEPS,
} from "@/lib/mock-data";
import { useCurrentCase } from "@/lib/use-current-case";

export default function ReportsPage() {
  const currentCase = useCurrentCase();
  const [previewOpen, setPreviewOpen] = useState(false);

  const strongRoutes = MOCK_IP_ROUTES.filter(
    (route) => route.relevance === "High"
  );

  const missingRequirements = MOCK_REGULATORY_STEPS.filter(
    (step) => step.type === "missing"
  );

  const evidenceGaps = MOCK_EVIDENCE.filter(
    (item) => item.status === "uncertain"
  );

  return (
    <main className="min-h-screen bg-background text-ink">
      <div className="mx-auto max-w-6xl px-6 py-10 md:px-10 md:py-14">
        {/* HEADER */}
        <header className="border-b border-border pb-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
            IP-SAKTI 360 / Reports
          </p>

          <h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">
            Your reports.
          </h1>

          <p className="mt-3 max-w-2xl text-base leading-7 text-ink-muted">
            View and prepare a structured summary of your innovation analysis.
          </p>
        </header>

        {/* SUMMARY CARDS */}
        <section className="mt-8 grid gap-6 md:grid-cols-2">
          {/* CURRENT CASE */}
          <div className="rounded-3xl border border-border bg-surface p-6 md:p-8">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
              Current case
            </p>

            <h2 className="mt-3 text-2xl font-semibold tracking-tight">
              Current innovation
            </h2>

            <p className="mt-3 text-sm leading-7 text-ink-muted">
              {currentCase.productDescription}
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-full bg-accent-subtle px-3 py-1.5 text-xs font-medium text-accent">
                {currentCase.jurisdiction}
              </span>

              <span className="rounded-full border border-border px-3 py-1.5 text-xs text-ink-muted">
                {currentCase.status}
              </span>
            </div>

            <Link
              href="/dashboard"
              className="mt-7 inline-flex h-11 items-center rounded-xl bg-accent px-5 text-sm font-medium text-white transition hover:bg-accent/90"
            >
              View analysis →
            </Link>
          </div>

          {/* REPORT */}
          <div className="rounded-3xl border border-border bg-[#16212B] p-6 text-white md:p-8">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/50">
              Report
            </p>

            <h2 className="mt-3 text-2xl font-semibold tracking-tight">
              Innovation analysis report
            </h2>

            <p className="mt-3 text-sm leading-7 text-white/65">
              A consolidated view of the innovation, evidence, IP strategy
              and regulatory considerations.
            </p>

            <button
              type="button"
              onClick={() => setPreviewOpen((open) => !open)}
              className="mt-7 rounded-xl bg-white px-5 py-3 text-sm font-medium text-ink transition hover:bg-background"
            >
              {previewOpen ? "Hide preview" : "Generate preview"}
            </button>
          </div>
        </section>

        {/* REPORT PREVIEW */}
        {previewOpen && (
          <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8">
            <div className="flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
                  Report preview
                </p>

                <h2 className="mt-2 text-3xl font-semibold tracking-tight">
                  Innovation analysis summary
                </h2>

                <p className="mt-2 text-sm text-ink-muted">
                  Case {currentCase.id} · {currentCase.jurisdiction}
                </p>
              </div>

              <span className="w-fit rounded-full bg-warm-subtle px-3 py-1.5 text-xs font-medium text-warm">
                Prototype report
              </span>
            </div>

            {/* CASE */}
            <div className="mt-7">
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-accent">
                01 / Innovation
              </p>

              <p className="mt-3 text-sm leading-7 text-ink-muted">
                {currentCase.productDescription}
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                {currentCase.ingredients.map((ingredient) => (
                  <span
                    key={ingredient}
                    className="rounded-full border border-border px-3 py-1.5 text-xs text-ink-muted"
                  >
                    {ingredient.split(" (")[0]}
                  </span>
                ))}
              </div>
            </div>

            {/* EVIDENCE */}
            <div className="mt-8 border-t border-border pt-7">
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-accent">
                02 / Evidence
              </p>

              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <ReportMetric
                  value={String(MOCK_EVIDENCE.length)}
                  label="Sources reviewed"
                />

                <ReportMetric
                  value={String(evidenceGaps.length)}
                  label="Evidence gaps"
                />

                <ReportMetric
                  value={
                    MOCK_EVIDENCE.filter(
                      (item) => item.confidence === "High"
                    ).length.toString()
                  }
                  label="High-confidence sources"
                />
              </div>
            </div>

            {/* IP */}
            <div className="mt-8 border-t border-border pt-7">
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-accent">
                03 / IP strategy
              </p>

              <div className="mt-4 space-y-3">
                {strongRoutes.map((route) => (
                  <div
                    key={route.name}
                    className="rounded-2xl border border-border bg-background p-4"
                  >
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <h3 className="text-sm font-semibold">
                        {route.name}
                      </h3>

                      <span className="w-fit rounded-full bg-accent-subtle px-2.5 py-1 text-[10px] font-medium text-accent">
                        High relevance
                      </span>
                    </div>

                    <p className="mt-2 text-sm leading-6 text-ink-muted">
                      {route.reason}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* REGULATORY */}
            <div className="mt-8 border-t border-border pt-7">
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-accent">
                04 / Regulatory
              </p>

              <div className="mt-4 space-y-3">
                {missingRequirements.map((requirement) => (
                  <div
                    key={requirement.title}
                    className="rounded-2xl border border-warm/20 bg-warm-subtle p-4"
                  >
                    <p className="text-sm font-semibold">
                      {requirement.title}
                    </p>

                    <p className="mt-2 text-sm leading-6 text-ink-muted">
                      {requirement.detail}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* DISCLAIMER */}
            <div className="mt-8 border-t border-border pt-6">
              <p className="text-xs leading-5 text-ink-muted">
                Prototype report generated from the current mock analysis.
                This information is for guidance and review and does not
                constitute legal, patent, scientific, or regulatory advice.
              </p>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}

function ReportMetric({
  value,
  label,
}: {
  value: string;
  label: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-background p-5">
      <p className="text-3xl font-semibold tracking-tight">{value}</p>

      <p className="mt-2 text-sm text-ink-muted">{label}</p>
    </div>
  );
}