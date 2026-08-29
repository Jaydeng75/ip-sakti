import Link from "next/link";
import { MOCK_IP_ROUTES } from "@/lib/mock-data";

export default function IPStrategyPage() {
  const rankedRoutes = [...MOCK_IP_ROUTES].sort((a, b) => {
    const score = { High: 0, Medium: 1, Low: 2 };
    return score[a.relevance] - score[b.relevance];
  });

  return (
    <main className="min-h-screen bg-background text-ink">
      <div className="mx-auto max-w-6xl px-6 py-10 md:px-10 md:py-14">
        <header className="border-b border-border pb-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
            IP-SAKTI 360 / IP Strategy
          </p>

          <h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">
            How could you protect it?
          </h1>

          <p className="mt-3 max-w-2xl text-base leading-7 text-ink-muted">
            Compare possible protection routes and understand where your
            strongest opportunities appear to be.
          </p>
        </header>

        <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
            Recommended direction
          </p>

          <div className="mt-3 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-3xl font-semibold tracking-tight">
                Build around the process.
              </h2>

              <p className="mt-3 max-w-2xl text-sm leading-7 text-ink-muted">
                The current analysis identifies the tri-herb standardization
                process as the strongest potential protection route.
              </p>
            </div>

            <span className="w-fit rounded-full bg-accent-subtle px-3 py-1.5 text-xs font-medium text-accent">
              High relevance
            </span>
          </div>
        </section>

        <section className="mt-10">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
              Protection routes
            </p>

            <h2 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
              What could protect your work?
            </h2>
          </div>

          <div className="mt-6 space-y-4">
            {rankedRoutes.map((route, index) => (
              <RouteCard
                key={route.name}
                number={index + 1}
                name={route.name}
                status={route.status}
                relevance={route.relevance}
                reason={route.reason}
                evidence={route.evidence}
                nextStep={route.nextStep}
              />
            ))}
          </div>
        </section>

        <section className="mt-10 grid gap-6 md:grid-cols-2">
          <div className="rounded-3xl border border-border bg-surface p-6 md:p-8">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
              Strongest opportunity
            </p>

            <h2 className="mt-3 text-2xl font-semibold tracking-tight">
              Process Patent
            </h2>

            <p className="mt-3 text-sm leading-7 text-ink-muted">
              Focus the protection strategy on the specific co-extraction and
              standardization process identified in the current analysis.
            </p>

            <Link
              href="/analyze"
              className="mt-6 inline-flex text-sm font-medium text-accent hover:underline"
            >
              Review the innovation genome →
            </Link>
          </div>

          <div className="rounded-3xl border border-warm/20 bg-warm-subtle p-6 md:p-8">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-warm">
              Important
            </p>

            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink">
              Not every route is equally strong.
            </h2>

            <p className="mt-3 text-sm leading-7 text-ink-muted">
              A route can be relevant without being a good protection
              strategy. The analysis should always be read together with its
              evidence and limitations.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}

function RouteCard({
  number,
  name,
  status,
  relevance,
  reason,
  evidence,
  nextStep,
}: {
  number: number;
  name: string;
  status: string;
  relevance: "High" | "Medium" | "Low";
  reason: string;
  evidence: string;
  nextStep: string;
}) {
  const badge =
    relevance === "High"
      ? "bg-accent-subtle text-accent"
      : relevance === "Medium"
        ? "bg-warm-subtle text-warm"
        : "bg-ink/5 text-ink-muted";

  return (
    <article className="rounded-2xl border border-border bg-surface p-6 transition hover:shadow-sm md:p-7">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex gap-4">
          <span className="font-mono text-xs font-semibold text-ink-muted">
            {String(number).padStart(2, "0")}
          </span>

          <div>
            <h3 className="text-xl font-semibold tracking-tight">{name}</h3>

            <p className="mt-1 text-sm font-medium text-accent">
              {status}
            </p>
          </div>
        </div>

        <span className={`w-fit rounded-full px-3 py-1.5 text-xs font-medium ${badge}`}>
          {relevance} relevance
        </span>
      </div>

      <div className="mt-6 grid gap-5 border-t border-border pt-5 md:grid-cols-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">
            Why
          </p>

          <p className="mt-2 text-sm leading-6 text-ink-muted">
            {reason}
          </p>
        </div>

        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">
            Evidence
          </p>

          <p className="mt-2 text-sm leading-6 text-ink-muted">
            {evidence}
          </p>
        </div>

        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">
            Next step
          </p>

          <p className="mt-2 text-sm leading-6 text-ink-muted">
            {nextStep}
          </p>
        </div>
      </div>
    </article>
  );
}
