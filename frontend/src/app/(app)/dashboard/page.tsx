import Link from "next/link";
import { MOCK_CASE, MOCK_GENOME_NODES, MOCK_IP_ROUTES, MOCK_REGULATORY_STEPS, MOCK_ROADMAP_STEPS } from "@/lib/mock-data";

export default function DashboardPage() {
  const evidenceGaps = MOCK_GENOME_NODES.filter(
    (node) => node.status === "needs-evidence" || node.status === "uncertain"
  ).length;

  const strongIPRoutes = MOCK_IP_ROUTES.filter(
    (route) => route.relevance === "High"
  ).length;

  const completedSteps = MOCK_ROADMAP_STEPS.filter(
    (step) => step.status === "complete"
  ).length;

  const roadmapProgress = Math.round(
    (completedSteps / MOCK_ROADMAP_STEPS.length) * 100
  );

  const absReviewRequired = MOCK_REGULATORY_STEPS.some(
    (step) =>
      step.title.toLowerCase().includes("biological diversity") &&
      step.type === "missing"
  );

  return (
    <main className="min-h-screen bg-background text-ink">
      <div className="mx-auto max-w-6xl px-6 py-10 md:px-10 md:py-14">
        {/* HEADER */}
        <header className="border-b border-border pb-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
            IP-SAKTI 360
          </p>

          <div className="mt-3 flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
            <div>
              <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
                Your innovation at a glance.
              </h1>

              <p className="mt-3 max-w-2xl text-base leading-7 text-ink-muted">
                Everything important about your current case, without the
                noise. Pick up where you left off or explore a specific part.
              </p>
            </div>

            <div className="font-mono text-xs text-ink-muted">
              {MOCK_CASE.jurisdiction} · CASE {MOCK_CASE.id}
            </div>
          </div>
        </header>

        {/* ACTIVE CASE */}
        <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8">
          <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
            <div className="max-w-3xl">
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-muted">
                Active innovation
              </p>

              <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                {MOCK_CASE.name}
              </h2>

              <p className="mt-3 text-sm leading-7 text-ink-muted">
                {MOCK_CASE.productDescription}
              </p>
            </div>

            <Link
              href="/analyze"
              className="inline-flex h-11 items-center justify-center rounded-xl bg-accent px-5 text-sm font-medium text-white transition hover:bg-accent/90"
            >
              Continue analysis →
            </Link>
          </div>

          <div className="mt-7 flex flex-wrap gap-2">
            {MOCK_CASE.ingredients.map((ingredient) => (
              <span
                key={ingredient}
                className="rounded-full border border-border px-3 py-1.5 text-xs text-ink-muted"
              >
                {ingredient.split(" (")[0]}
              </span>
            ))}
          </div>
        </section>

        {/* ATTENTION */}
        <section className="mt-8">
          <div className="mb-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
              What needs your attention
            </p>

            <h2 className="mt-2 text-2xl font-semibold tracking-tight">
              Start here
            </h2>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <AttentionCard
              label="Evidence"
              value={`${evidenceGaps} gaps`}
              description="Some findings still need stronger evidence."
              href="/evidence"
              tone="warn"
            />

            <AttentionCard
              label="IP strategy"
              value={`${strongIPRoutes} strong routes`}
              description="Promising protection routes have been identified."
              href="/ip-strategy"
              tone="success"
            />

            <AttentionCard
              label="ABS review"
              value={absReviewRequired ? "Required" : "No action"}
              description="Check your biological-resource sourcing."
              href="/regulatory"
              tone={absReviewRequired ? "warn" : "success"}
            />
          </div>
        </section>

        {/* PROGRESS */}
        <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
                Your progress
              </p>

              <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                From idea to market
              </h2>
            </div>

            <span className="font-mono text-sm text-ink-muted">
              {roadmapProgress}% complete
            </span>
          </div>

          <div className="mt-7 h-2 overflow-hidden rounded-full bg-accent-subtle">
            <div
              className="h-full rounded-full bg-accent transition-all"
              style={{ width: `${roadmapProgress}%` }}
            />
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-4">
            <ProgressItem
              label="Innovation"
              active={true}
            />
            <ProgressItem
              label="Evidence"
              active={evidenceGaps === 0}
            />
            <ProgressItem
              label="IP strategy"
              active={strongIPRoutes > 0}
            />
            <ProgressItem
              label="Regulatory"
              active={completedSteps >= 4}
            />
          </div>
        </section>

        {/* NEXT BEST ACTION */}
        <section className="mt-8 grid gap-6 md:grid-cols-[1.25fr_0.75fr]">
          <div className="rounded-3xl border border-border bg-[#16212B] p-7 text-white md:p-8">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/50">
              Next best action
            </p>

            <h2 className="mt-3 max-w-xl text-3xl font-semibold tracking-tight">
              Review the evidence behind your claims.
            </h2>

            <p className="mt-3 max-w-xl text-sm leading-6 text-white/65">
              Your current case has evidence gaps around the specific
              three-herb combination. Understanding those gaps can strengthen
              the next decisions you make.
            </p>

            <Link
              href="/evidence"
              className="mt-7 inline-flex h-11 items-center rounded-xl bg-white px-5 text-sm font-medium text-ink transition hover:bg-[#F7F8F6]"
            >
              Review evidence →
            </Link>
          </div>

          <div className="rounded-3xl border border-border bg-surface p-7">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
              Explore
            </p>

            <div className="mt-5 space-y-2">
              <QuickLink href="/traditional-knowledge" label="Traditional Knowledge" />
              <QuickLink href="/ip-strategy" label="IP Strategy" />
              <QuickLink href="/jurisdiction" label="Compare markets" />
              <QuickLink href="/ask" label="Ask IP-SAKTI" />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function AttentionCard({
  label,
  value,
  description,
  href,
  tone,
}: {
  label: string;
  value: string;
  description: string;
  href: string;
  tone: "warn" | "success";
}) {
  const toneClass =
    tone === "warn"
      ? "bg-warm-subtle text-warm"
      : "bg-accent-subtle text-accent";

  return (
    <Link
      href={href}
      className="group rounded-2xl border border-border bg-surface p-6 transition hover:-translate-y-0.5 hover:shadow-sm"
    >
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-muted">
        {label}
      </p>

      <div className="mt-5 flex items-center justify-between gap-3">
        <p className="text-xl font-semibold tracking-tight">{value}</p>

        <span
          className={`rounded-full px-2.5 py-1 text-[10px] font-medium ${toneClass}`}
        >
          Review
        </span>
      </div>

      <p className="mt-2 text-sm leading-6 text-ink-muted">
        {description}
      </p>

      <p className="mt-5 text-sm font-medium text-accent transition-transform group-hover:translate-x-1">
        Open →
      </p>
    </Link>
  );
}

function ProgressItem({
  label,
  active,
}: {
  label: string;
  active: boolean;
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span
        className={`h-2.5 w-2.5 rounded-full ${
          active ? "bg-accent" : "bg-border"
        }`}
      />

      <span className={active ? "text-ink" : "text-ink-muted"}>
        {label}
      </span>
    </div>
  );
}

function QuickLink({
  href,
  label,
}: {
  href: string;
  label: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-center justify-between rounded-xl border border-border px-4 py-3 text-sm transition hover:bg-background"
    >
      <span>{label}</span>
      <span className="text-ink-muted">→</span>
    </Link>
  );
}