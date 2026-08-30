"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { MOCK_CASE } from "@/lib/mock-data";
import { getCurrentCase } from "@/lib/case-store";

type CurrentCase = typeof MOCK_CASE;

export default function SavedCasesPage() {
  const [currentCase, setCurrentCase] = useState<CurrentCase>(MOCK_CASE);

  useEffect(() => {
    setCurrentCase(getCurrentCase());
  }, []);

  const updatedDate = new Date(currentCase.updatedAt).toLocaleDateString(
    "en-IN"
  );

  return (
    <main className="min-h-screen bg-background text-ink">
      <div className="mx-auto max-w-6xl px-6 py-10 md:px-10 md:py-14">
        <header className="border-b border-border pb-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
            IP-SAKTI 360 / Saved Cases
          </p>

          <h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">
            Your cases.
          </h1>

          <p className="mt-3 max-w-2xl text-base leading-7 text-ink-muted">
            Keep your innovations together and return to an analysis whenever
            you need it.
          </p>
        </header>

        <section className="mt-8">
          <div className="flex items-end justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
                Saved
              </p>

              <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                Recent innovations
              </h2>
            </div>

            <span className="font-mono text-xs text-ink-muted">
              01 case
            </span>
          </div>

          <div className="mt-6 rounded-3xl border border-border bg-surface p-6 md:p-8">
            <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap gap-2">
                  <span className="rounded-full bg-accent-subtle px-3 py-1.5 text-xs font-medium text-accent">
                    {currentCase.jurisdiction}
                  </span>

                  <span className="rounded-full bg-warm-subtle px-3 py-1.5 text-xs font-medium text-warm">
                    Review needed
                  </span>
                </div>

                <h3 className="mt-4 text-2xl font-semibold tracking-tight">
                  Current innovation
                </h3>

                <p className="mt-3 max-w-2xl text-sm leading-7 text-ink-muted">
                  {currentCase.productDescription}
                </p>
              </div>

              <Link
                href="/analyze"
                className="inline-flex h-11 shrink-0 items-center justify-center rounded-xl bg-accent px-5 text-sm font-medium text-white hover:bg-accent/90"
              >
                Open case →
              </Link>
            </div>

            <div className="mt-6 border-t border-border pt-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">
                Last updated
              </p>

              <p className="mt-1 text-sm text-ink">
                {updatedDate}
              </p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}