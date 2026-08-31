"use client";

import { useCallback, useEffect, useState } from "react";
import { AnalysisResponse, caseApi } from "@/lib/api";
import { getCurrentCase } from "@/lib/case-store";

const ANALYSIS_EVENT = "ip-sakti:analysis-updated";

export function notifyAnalysisUpdated() {
  window.dispatchEvent(new Event(ANALYSIS_EVENT));
}

export function useCurrentAnalysis() {
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const currentCase = getCurrentCase();
    if (!currentCase.backendId) {
      setAnalysis(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const next = await caseApi.latestAnalysis(currentCase.backendId);
      setAnalysis(next);
      setError(null);
    } catch (caught) {
      setAnalysis(null);
      setError(caught instanceof Error ? caught.message : "Analysis could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => void refresh(), 0);
    window.addEventListener(ANALYSIS_EVENT, refresh);
    window.addEventListener("ip-sakti:case-updated", refresh);
    return () => {
      window.clearTimeout(initialLoad);
      window.removeEventListener(ANALYSIS_EVENT, refresh);
      window.removeEventListener("ip-sakti:case-updated", refresh);
    };
  }, [refresh]);

  return { analysis, loading, error, refresh };
}
