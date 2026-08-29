import { MOCK_CASE, MOCK_REGULATORY_STEPS } from "@/lib/mock-data";

export default function RegulatoryPage() {
  const completeSteps = MOCK_REGULATORY_STEPS.filter(
    (step) => step.type === "fact"
  ).length;

  return (
    <main className="min-h-screen bg-background text-ink">
      <div className="mx-auto max-w-6xl px-6 py-10 md:px-10 md:py-14">
        {/* HEADER */}
        <header className="border-b border-border pb-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
            IP-SAKTI 360 / Regulatory & ABS
          </p>

          <h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">
            What needs to happen before market entry?
          </h1>

          <p className="mt-3 max-w-2xl text-base leading-7 text-ink-muted">
            Follow the regulatory path for your innovation and see which
            requirements are confirmed, uncertain, or still missing.
          </p>
        </header>

        {/* CASE CONTEXT */}
        <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-muted">
                Active case
              </p>

              <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                Herbal stress-management formulation
              </h2>

              <p className="mt-2 text-sm text-ink-muted">
                {MOCK_CASE.jurisdiction} · {MOCK_CASE.productType}
              </p>
            </div>

            <div className="text-sm text-ink-muted">
              {completeSteps} of {MOCK_REGULATORY_STEPS.length} requirements
              classified
            </div>
          </div>
        </section>

        {/* FLOW */}
        <section className="mt-10">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
              Regulatory pathway
            </p>

            <h2 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
              From classification to market
            </h2>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-6">
            {[
              "Product Classification",
              "Applicable Regulation",
              "Biological Resource / ABS Check",
              "Required Evidence",
              "Documentation",
              "Market Entry",
            ].map((step, index) => (
              <div
                key={step}
                className="rounded-2xl border border-border bg-surface p-4"
              >
                <span className="font-mono text-[10px] font-semibold text-accent">
                  0{index + 1}
                </span>

                <p className="mt-5 text-sm font-medium leading-5">
                  {step}
                </p>

                {index < 5 && (
                  <p className="mt-3 hidden text-xs text-ink-muted md:block">
                    →
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* REQUIREMENTS */}
        <section className="mt-10">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
              Current assessment
            </p>

            <h2 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
              What we know so far
            </h2>
          </div>

          <div className="mt-6 space-y-4">
            {MOCK_REGULATORY_STEPS.map((step, index) => (
              <RequirementCard
                key={`${step.title}-${index}`}
                number={index + 1}
                title={step.title}
                type={step.type}
                detail={step.detail}
              />
            ))}
          </div>
        </section>

        {/* ABS */}
        <section className="mt-10 grid gap-6 md:grid-cols-2">
          <div className="rounded-3xl border border-warm/20 bg-warm-subtle p-6 md:p-8">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-warm">
              ABS review
            </p>

            <h2 className="mt-3 text-2xl font-semibold tracking-tight">
              Biological-resource sourcing needs attention.
            </h2>

            <p className="mt-3 text-sm leading-7 text-ink-muted">
              The current case contains a flagged sourcing issue involving
              Brahmi. The available record does not yet confirm the required
              biodiversity clearance.
            </p>

            <a
              href="#requirements"
              className="mt-6 inline-flex text-sm font-medium text-warm hover:underline"
            >
              Review requirement →
            </a>
          </div>

          <div className="rounded-3xl border border-border bg-[#16212B] p-6 text-white md:p-8">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/50">
              Principle
            </p>

            <h2 className="mt-3 text-2xl font-semibold tracking-tight">
              Don't confuse approval with evidence.
            </h2>

            <p className="mt-3 text-sm leading-7 text-white/65">
              A regulatory permission, scientific finding, or traditional-use
              record answers a different question. IP-SAKTI keeps those layers
              separate.
            </p>
          </div>
        </section>

        {/* DISCLAIMER */}
        <p className="mt-8 text-center text-xs text-ink-muted">
          Information shown here is for guidance and review, not legal or
          regulatory advice.
        </p>
      </div>
    </main>
  );
}

function RequirementCard({
  number,
  title,
  type,
  detail,
}: {
  number: number;
  title: string;
  type: "fact" | "interpretation" | "missing";
  detail: string;
}) {
  const statusStyles = {
    fact: "bg-accent-subtle text-accent",
    interpretation: "bg-warm-subtle text-warm",
    missing: "bg-danger/10 text-danger",
  };

  const statusLabel = {
    fact: "Confirmed",
    interpretation: "Interpretation",
    missing: "Missing",
  };

  return (
    <article
      id="requirements"
      className="rounded-2xl border border-border bg-surface p-6 md:p-7"
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-start">
        <span className="font-mono text-xs font-semibold text-ink-muted">
          {String(number).padStart(2, "0")}
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-semibold tracking-tight">
              {title}
            </h3>

            <span
              className={`rounded-full px-2.5 py-1 text-[10px] font-medium ${statusStyles[type]}`}
            >
              {statusLabel[type]}
            </span>
          </div>

          <p className="mt-3 text-sm leading-7 text-ink-muted">
            {detail}
          </p>
        </div>
      </div>
    </article>
  );
}
