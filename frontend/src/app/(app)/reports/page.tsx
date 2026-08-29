import Link from "next/link";
import { MOCK_CASE } from "@/lib/mock-data";

export default function ReportsPage() {
  return (
    <main className="min-h-screen bg-background text-ink">
      <div className="mx-auto max-w-6xl px-6 py-10 md:px-10 md:py-14">
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

        <section className="mt-8 grid gap-6 md:grid-cols-2">
          <div className="rounded-3xl border border-border bg-surface p-6 md:p-8">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
              Current case
            </p>

            <h2 className="mt-3 text-2xl font-semibold tracking-tight">
              Herbal stress-management formulation
            </h2>

            <p className="mt-2 text-sm text-ink-muted">
              {MOCK_CASE.jurisdiction} · {MOCK_CASE.status}
            </p>

            <Link
              href="/dashboard"
              className="mt-7 inline-flex h-11 items-center rounded-xl bg-accent px-5 text-sm font-medium text-white hover:bg-accent/90"
            >
              View analysis →
            </Link>
          </div>

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
              className="mt-7 rounded-xl bg-white px-5 py-3 text-sm font-medium text-ink hover:bg-background"
            >
              Generate preview
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}