import { MOCK_CASE } from "@/lib/mock-data";

const jurisdictions = [
  {
    name: "India",
    code: "IN",
    patent: "Traditional-knowledge screening is important",
    traditional: "High relevance",
    regulation: "AYUSH + biodiversity requirements",
    evidence: "Product-specific evidence may be needed",
    market: "Medium complexity",
    highlight: true,
  },
  {
    name: "European Union",
    code: "EU",
    patent: "Novelty and inventive step",
    traditional: "Prior-art review recommended",
    regulation: "Depends on product classification",
    evidence: "Claims must match permitted framework",
    market: "High complexity",
    highlight: false,
  },
  {
    name: "United States",
    code: "US",
    patent: "Novelty + non-obviousness",
    traditional: "Prior-art considerations",
    regulation: "Classification determines pathway",
    evidence: "Claim-specific support important",
    market: "High complexity",
    highlight: false,
  },
  {
    name: "Japan",
    code: "JP",
    patent: "Novelty and inventive step",
    traditional: "Traditional-use context may matter",
    regulation: "Product classification driven",
    evidence: "Evidence requirements vary",
    market: "Medium-high complexity",
    highlight: false,
  },
];

export default function JurisdictionPage() {
  return (
    <main className="min-h-screen bg-background text-ink">
      <div className="mx-auto max-w-7xl px-6 py-10 md:px-10 md:py-14">
        {/* HEADER */}
        <header className="border-b border-border pb-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
            IP-SAKTI 360 / Jurisdiction Compare
          </p>

          <h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">
            Where should you take it?
          </h1>

          <p className="mt-3 max-w-2xl text-base leading-7 text-ink-muted">
            Compare how your innovation may be treated across different
            markets before deciding where to focus your next move.
          </p>
        </header>

        {/* CASE */}
        <section className="mt-8 rounded-3xl border border-border bg-surface p-6 md:p-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
            Current case
          </p>

          <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">
                Herbal stress-management formulation
              </h2>

              <p className="mt-2 text-sm text-ink-muted">
                Current jurisdiction: {MOCK_CASE.jurisdiction}
              </p>
            </div>

            <span className="rounded-full bg-accent-subtle px-3 py-1.5 text-xs font-medium text-accent">
              {MOCK_CASE.productType}
            </span>
          </div>
        </section>

        {/* COMPARISON */}
        <section className="mt-10">
          <div className="mb-6">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
              Market comparison
            </p>

            <h2 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
              One innovation. Four regulatory landscapes.
            </h2>
          </div>

          <div className="overflow-x-auto rounded-3xl border border-border bg-surface">
            <table className="w-full min-w-[950px] border-collapse text-left">
              <thead>
                <tr className="border-b border-border bg-background">
                  <th className="w-52 p-5 font-mono text-[10px] uppercase tracking-[0.15em] text-ink-muted">
                    Area
                  </th>

                  {jurisdictions.map((market) => (
                    <th
                      key={market.code}
                      className="p-5 align-top"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] text-ink-muted">
                          {market.code}
                        </span>

                        <span className="text-sm font-semibold">
                          {market.name}
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                <ComparisonRow
                  label="Patent"
                  values={jurisdictions.map((item) => item.patent)}
                  active={jurisdictions.map((item) => item.highlight)}
                />

                <ComparisonRow
                  label="Traditional knowledge"
                  values={jurisdictions.map((item) => item.traditional)}
                  active={jurisdictions.map((item) => item.highlight)}
                />

                <ComparisonRow
                  label="Regulation"
                  values={jurisdictions.map((item) => item.regulation)}
                  active={jurisdictions.map((item) => item.highlight)}
                />

                <ComparisonRow
                  label="Evidence"
                  values={jurisdictions.map((item) => item.evidence)}
                  active={jurisdictions.map((item) => item.highlight)}
                />

                <ComparisonRow
                  label="Market entry"
                  values={jurisdictions.map((item) => item.market)}
                  active={jurisdictions.map((item) => item.highlight)}
                  last
                />
              </tbody>
            </table>
          </div>
        </section>

        {/* TAKEAWAY */}
        <section className="mt-8 grid gap-6 md:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-3xl border border-border bg-[#16212B] p-7 text-white md:p-8">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/50">
              Current signal
            </p>

            <h2 className="mt-3 text-3xl font-semibold tracking-tight">
              India should be your first review point.
            </h2>

            <p className="mt-3 max-w-2xl text-sm leading-7 text-white/65">
              Your current case is structured around the Indian market, so
              classification, traditional knowledge, biodiversity and IP
              questions should be resolved before comparing expansion routes.
            </p>
          </div>

          <div className="rounded-3xl border border-border bg-surface p-7 md:p-8">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
              Compare before deciding
            </p>

            <div className="mt-5 space-y-3">
              <NextStep text="Check patentability" />
              <NextStep text="Review evidence requirements" />
              <NextStep text="Compare regulatory burden" />
              <NextStep text="Assess market-entry complexity" />
            </div>
          </div>
        </section>

        <p className="mt-8 text-center text-xs text-ink-muted">
          This comparison is a prototype and does not constitute legal or
          regulatory advice.
        </p>
      </div>
    </main>
  );
}

function ComparisonRow({
  label,
  values,
  active,
  last = false,
}: {
  label: string;
  values: string[];
  active: boolean[];
  last?: boolean;
}) {
  return (
    <tr className={last ? "" : "border-b border-border"}>
      <td className="p-5 align-top text-sm font-medium text-ink">
        {label}
      </td>

      {values.map((value, index) => (
        <td
          key={`${label}-${index}`}
          className={`p-5 align-top text-sm leading-6 ${
            active[index]
              ? "bg-accent-subtle/40 text-ink"
              : "text-ink-muted"
          }`}
        >
          {value}
        </td>
      ))}
    </tr>
  );
}

function NextStep({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border px-4 py-3">
      <span className="h-2 w-2 rounded-full bg-accent" />
      <span className="text-sm">{text}</span>
    </div>
  );
}