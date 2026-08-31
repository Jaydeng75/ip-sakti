import Link from "next/link";

export function AnalysisState({ loading, error }: { loading: boolean; error: string | null }) {
  if (loading) {
    return <div className="mt-8 animate-pulse rounded-3xl border border-border bg-surface p-8 text-sm text-ink-muted">Loading the active case analysis…</div>;
  }
  return (
    <div className="mt-8 rounded-3xl border border-border bg-surface p-8">
      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Analysis required</p>
      <h2 className="mt-2 text-2xl font-semibold">No linked analysis is available.</h2>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-ink-muted">{error ?? "Create an innovation case to populate this module with source-grounded findings."}</p>
      <Link href="/analyze" className="mt-5 inline-flex rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white">Analyze an innovation →</Link>
    </div>
  );
}

export function ModuleHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <header className="border-b border-border pb-8">
      <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">IP-SAKTI 360 / {eyebrow}</p>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">{title}</h1>
      <p className="mt-3 max-w-3xl text-base leading-7 text-ink-muted">{description}</p>
    </header>
  );
}
