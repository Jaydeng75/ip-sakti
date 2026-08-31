import { Case, DEFAULT_CASE } from "@/lib/case-data";

const CASE_STORAGE_KEY = "ip-sakti-current-case";

export function getCurrentCase() {
  if (typeof window === "undefined") {
    return DEFAULT_CASE;
  }

  const stored = window.localStorage.getItem(CASE_STORAGE_KEY);

  if (!stored) {
    return DEFAULT_CASE;
  }

  try {
    return JSON.parse(stored);
  } catch {
    return DEFAULT_CASE;
  }
}

export function saveCurrentCase(description: string) {
  const currentCase = getCurrentCase();

  const updatedCase = {
    ...currentCase,
    productDescription: description,
    updatedAt: new Date().toISOString(),
    status: "analyzing",
  };

  window.localStorage.setItem(
    CASE_STORAGE_KEY,
    JSON.stringify(updatedCase)
  );

  window.dispatchEvent(new Event("ip-sakti:case-updated"));

  return updatedCase;
}

export function saveCaseSnapshot(currentCase: Case) {
  window.localStorage.setItem(CASE_STORAGE_KEY, JSON.stringify(currentCase));
  window.dispatchEvent(new Event("ip-sakti:case-updated"));
  return currentCase;
}
