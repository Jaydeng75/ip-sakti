import { useEffect, useState } from "react";
import { MOCK_CASE } from "@/lib/mock-data";
import { getCurrentCase } from "@/lib/case-store";

export function useCurrentCase() {
  const [currentCase, setCurrentCase] = useState(MOCK_CASE);

  useEffect(() => {
    setCurrentCase(getCurrentCase());
  }, []);

  return currentCase;
}