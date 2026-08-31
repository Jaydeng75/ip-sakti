"use client";

import { useCurrentCase } from "@/lib/use-current-case";

export default function CaseHeader() {
  const currentCase = useCurrentCase();
  return (
    <div className="mb-8 rounded-2xl border border-border bg-surface px-5 py-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink">
            {currentCase.title ?? "Herbal stress-management formulation"}
          </p>

          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-ink-muted">
            <span>{currentCase.jurisdiction}</span>
            <span>·</span>
            <span>{currentCase.productType}</span>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span className="rounded-full bg-warm-subtle px-2.5 py-1 font-mono text-[10px] font-medium text-warm">
            {currentCase.status.replaceAll("_", " ").replace("-", " ")}
          </span>

          <span className="rounded-full border border-border px-2.5 py-1 font-mono text-[10px] text-ink-muted">
            {currentCase.backendId ? `CASE-${String(currentCase.backendId).padStart(5, "0")}` : currentCase.id}
          </span>
        </div>
      </div>
    </div>
  );
}
