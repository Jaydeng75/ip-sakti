import { useEffect, useState } from "react";
import { DEFAULT_CASE } from "@/lib/case-data";
import { getCurrentCase } from "@/lib/case-store";

export function useCurrentCase() {
  const [currentCase, setCurrentCase] = useState(DEFAULT_CASE);

  useEffect(() => {
    const refresh = () => setCurrentCase(getCurrentCase());
    refresh();
    window.addEventListener("ip-sakti:case-updated", refresh);
    return () => window.removeEventListener("ip-sakti:case-updated", refresh);
  }, []);

  return currentCase;
}
