import { MOCK_CASE } from "@/lib/mock-data";

const CASE_STORAGE_KEY = "ip-sakti-current-case";

export function getCurrentCase() {
  if (typeof window === "undefined") {
    return MOCK_CASE;
  }

  const stored = window.localStorage.getItem(CASE_STORAGE_KEY);

  if (!stored) {
    return MOCK_CASE;
  }

  try {
    return JSON.parse(stored);
  } catch {
    return MOCK_CASE;
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

  return updatedCase;
}