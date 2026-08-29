import {
  MOCK_EVIDENCE,
  MOCK_GENOME_NODES,
} from "@/lib/mock-data";

export default function ScientificEvidencePage() {
  const traditional = MOCK_GENOME_NODES.filter(
    (node) => node.layer === "traditional"
  );

  const scientific = MOCK_GENOME_NODES.filter(
    (node) => node.layer === "evidence"
  );

  return (
    <main className="min-h-screen bg-background text-ink">
      <div className="mx-auto max-w-6xl px-6 py-10 md:px-10 md:py-14">
        {/* HEADER */}
        <header className="border-b border-border pb-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
            IP-SAKTI 360 / Scientific Evidence
          </p>

          <h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">
            What does the evidence actually say?
          </h1>

          <p className="mt-3 max-w-2xl text-base leading-7 text-ink-muted">
            Separate traditional use from modern scientific evidence, see
            where confidence is strong, and identify claims that still need
            support.
          </p>
        </header>

        {/* WARNING */}
        <section className="mt-8 rounded-2xl border border-warm/20 bg-warm-subtle p-5">
          <p className="text-sm font-semibold text-warm">
            Important distinction
          </p>

          <p className="mt-2 text-sm leading-6 text-ink-muted">
            Traditional use is not equivalent to clinically established
            efficacy. IP-SAKTI keeps these evidence types separate.
          </p>
        </section>

        {/* SUMMARY */}
        <section className="mt-8 grid gap-4 sm:grid-cols-3">
          <Summary
            value={String(traditional.length)}
            label="Traditional-use findings"
          />

          <Summary
            value={String(scientific.length)}
            label="Scientific findings"
          />

          <Summary
            value={String(MOCK_EVIDENCE.length)}
            label="Sources reviewed"
          />
        </section>

        {/* TRADITIONAL USE */}
        <section className="mt-10">
          <SectionTitle
            eyebrow="01 / Traditional use"
            title="What has been traditionally documented?"
          />

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {traditional.map((item) => (
              <EvidenceCard
                key={item.id}
                title={item.label}
                description={item.description}
                status="Traditional use"
                confidence={item.confidence}
              />
            ))}
          </div>
        </section>

        {/* SCIENTIFIC */}
        <section className="mt-10">
          <SectionTitle
            eyebrow="02 / Scientific evidence"
            title="What has modern research found?"
          />

          <div className="mt-5 space-y-4">
            {scientific.map((item) => (
              <EvidenceCard
                key={item.id}
                title={item.label}
                description={item.description}
                status={
                  item.status === "needs-evidence"
                    ? "Needs evidence"
                    : "Supported finding"
                }
                confidence={item.confidence}
              />
            ))}
          </div>
        </section>

        {/* SOURCES */}
        <section className="mt-10">
          <SectionTitle
            eyebrow="03 / Sources"
            title="Evidence behind the analysis"
          />

          <div className="mt-5 space-y-3">
            {MOCK_EVIDENCE.map((item, index) => (
              <div
                key={`${item.source}-${index}`}
                className="rounded-2xl border border-border bg-surface p-5"
              >
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold leading-5">
                      {item.source}
                    </p>

                    <p className="mt-2 text-xs text-ink-muted">
                      {item.authority}
                    </p>

                    <p className="mt-1 text-xs leading-5 text-ink-muted">
                      {item.section}
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <span
                      className={`rounded-full px-2.5 py-1 text-[10px] font-medium ${
                        item.status === "supports"
                          ? "bg-accent-subtle text-accent"
                          : item.status === "inference"
                            ? "bg-warm-subtle text-warm"
                            : "bg-danger/10 text-danger"
                      }`}
                    >
                      {item.status}
                    </span>

                    <span className="rounded-full bg-ink/5 px-2.5 py-1 text-[10px] font-medium text-ink-muted">
                      {item.confidence}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

function SectionTitle({
  eyebrow,
  title,
}: {
  eyebrow: string;
  title: string;
}) {
  return (
    <div>
      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
        {eyebrow}
      </p>

      <h2 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
        {title}
      </h2>
    </div>
  );
}

function Summary({
  value,
  label,
}: {
  value: string;
  label: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-6">
      <p className="text-3xl font-semibold tracking-tight">{value}</p>

      <p className="mt-2 text-sm text-ink-muted">{label}</p>
    </div>
  );
}

function EvidenceCard({
  title,
  description,
  status,
  confidence,
}: {
  title: string;
  description: string;
  status: string;
  confidence: "High" | "Medium" | "Low";
}) {
  return (
    <article className="rounded-2xl border border-border bg-surface p-6 transition hover:shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-base font-semibold tracking-tight">
          {title}
        </h3>

        <div className="flex gap-2">
          <span className="rounded-full bg-accent-subtle px-2.5 py-1 text-[10px] font-medium text-accent">
            {status}
          </span>

          <span className="rounded-full border border-border px-2.5 py-1 text-[10px] font-medium text-ink-muted">
            {confidence} confidence
          </span>
        </div>
      </div>

      <p className="mt-4 text-sm leading-7 text-ink-muted">
        {description}
      </p>
    </article>
  );
}