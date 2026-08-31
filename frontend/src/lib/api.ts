export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const TOKEN_KEY = "ip-sakti-token";
const DEVICE_KEY = "ip-sakti-device-credentials";

export type ApiCase = {
  id: number;
  owner_id: number;
  title: string;
  description: string;
  status: "draft" | "analyzed" | "review_requested" | "archived";
  ingredients: string[];
  product_form: string | null;
  intended_use: string | null;
  target_markets: string[];
  classical_formulation: boolean;
  biological_sourcing: string | null;
  metadata_json: Record<string, string>;
  created_at: string;
  updated_at: string;
};

export type Citation = {
  id: string;
  title: string;
  authority: string;
  jurisdiction: string;
  effective_date: string;
  url: string;
  support_status: string;
  excerpt: string;
  locator?: string | null;
  source_type?: "official" | "case_document";
  content_sha256?: string | null;
  retrieval_score?: number | null;
  lexical_score?: number | null;
  semantic_score?: number | null;
  rerank_score?: number | null;
  prefetch_rank?: number | null;
  embedding_model?: string | null;
  reranker?: string | null;
};

export type RiskCard = {
  key: string;
  title: string;
  score: number;
  level: string;
  summary: string;
  claim_type?: "inference";
  citations?: Citation[];
};

export type AnalysisResult = {
  case: { id: number; title: string; status: string };
  executive_summary: string;
  classification: {
    label: string;
    pathway: string;
    confidence: number;
    requires_human_review: boolean;
    citations: Citation[];
  };
  genome: {
    nodes: Array<{
      id: string;
      label: string;
      type: string;
      status: string;
    }>;
    edges: Array<{
      id: string;
      source: string;
      target: string;
      relation: string;
    }>;
  };
  risk_cards: RiskCard[];
  knowledge_graph: {
    nodes: Array<{ id: string; label: string; type: string; risk: string }>;
    edges: Array<{
      id: string;
      source: string;
      target: string;
      label: string;
    }>;
    findings: string[];
    citations: Citation[];
  };
  scientific_evidence: {
    notice: string;
    traditional_use: EvidenceSection;
    modern_science: EvidenceSection;
    safety: EvidenceSection;
    confidence: { label: string; score: number; basis: string };
    gaps: string[];
    citations: Citation[];
  };
  ip_strategy: {
    routes: Array<{
      name: string;
      strength: number;
      relevance: string;
      protects: string;
      caution: string;
    }>;
    recommended_strategy: string[];
    citations: Citation[];
  };
  regulatory_abs: {
    steps: Array<{
      order: number;
      name: string;
      status: string;
      detail: string;
      deliverable: string;
    }>;
    abs_flag: boolean;
    abs_summary: string;
    citations: Citation[];
  };
  jurisdictions: Array<{
    name: string;
    selected: boolean;
    patent: string;
    tk: string;
    regulation: string;
    evidence: string;
    market_entry: string;
    citations: Citation[];
  }>;
  challenges: Record<
    string,
    Array<{
      severity: string;
      objection: string;
      missing: string;
      next_step: string;
      citations?: Citation[];
    }>
  >;
  claim_evidence_graph: {
    claims: Array<{ id: string; text: string; claim_type: string; status: string; confidence: number }>;
    evidence: Array<{ id: string; citation_id: string; title: string; source_type: string; support_status: string; jurisdiction: string; effective_date: string; locator?: string | null }>;
    edges: Array<{ id: string; source: string; target: string; relation: string }>;
    summary: { claim_count: number; evidence_count: number; supported_or_qualified: number; unsupported: number; coverage: number };
    notice: string;
  };
  design_around: {
    recommended_route: string[];
    alternatives: Array<{
      id: string;
      dimension: string;
      proposed_change: string;
      rationale: string;
      evidence_required: string[];
      residual_risks: string[];
      claim_type: "inference";
      requires_human_review: boolean;
      citations: Citation[];
    }>;
    reviewer_inputs: Record<string, string[]>;
    notice: string;
  };
  next_actions: string[];
  confidence: { score: number; label: string; basis: string };
  corpus_version: string;
  generated_by: string;
  warnings: string[];
  evidence_retrieval: {
    document_count: number;
    indexed_document_count: number;
    chunk_count: number;
    retrieved_passage_count: number;
    citations: Citation[];
    method: string;
    appraisal_status: string;
    prefetch_limit: number;
    embedding_provider: string;
    embedding_model: string;
    embedding_revision: string;
    reranker: string;
  };
};

type EvidenceSection = {
  status: string;
  summary: string;
  confidence: number;
};

export type AnalysisResponse = {
  id: number;
  case_id: number;
  corpus_version: string;
  created_at: string;
  result: AnalysisResult;
};

export type AskResponse = {
  answer: string;
  authoritative_answer: string;
  input_language: string;
  response_language: string;
  input_translation: TranslationInfo;
  output_translation: TranslationInfo;
  claim_type: "legal_fact" | "interpretation" | "inference" | "unsupported";
  confidence: number;
  citations: Citation[];
  requires_human_review: boolean;
  limitations: string[];
};

export type TranslationInfo = {
  provider: "IndicTrans2" | "none";
  status: "identity" | "translated" | "disabled" | "unavailable";
  source_language: string;
  target_language: string;
  model: string | null;
  machine_translated: boolean;
};

function deviceCredentials() {
  const existing = window.localStorage.getItem(DEVICE_KEY);
  if (existing) return JSON.parse(existing) as { email: string; password: string };
  const identifier = crypto.randomUUID();
  const credentials = {
    email: `analyst-${identifier}@ip-sakti.local`,
    password: `${crypto.randomUUID()}-IpS!9`,
  };
  window.localStorage.setItem(DEVICE_KEY, JSON.stringify(credentials));
  return credentials;
}

async function issueLocalSession() {
  if (process.env.NEXT_PUBLIC_DEMO_AUTH !== "true") {
    throw new Error("Sign in with an approved IP-SAKTI account to continue.");
  }
  const demo = await fetch(`${API_BASE_URL}/auth/demo`, { method: "POST" });
  if (demo.ok) return demo.json() as Promise<{ access_token: string }>;

  const credentials = deviceCredentials();
  const registration = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...credentials,
      display_name: "Innovation Analyst",
    }),
  });
  if (registration.ok) {
    return registration.json() as Promise<{ access_token: string }>;
  }
  if (registration.status === 409) {
    const login = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(credentials),
    });
    if (login.ok) return login.json() as Promise<{ access_token: string }>;
  }
  throw new Error("Unable to establish a secure API session.");
}

async function token() {
  if (typeof window === "undefined") {
    throw new Error("The authenticated API client is available in the browser.");
  }
  const existing = window.localStorage.getItem(TOKEN_KEY);
  if (existing) return existing;
  const session = await issueLocalSession();
  window.localStorage.setItem(TOKEN_KEY, session.access_token);
  return session.access_token;
}

export async function login(email: string, password: string) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? "Sign-in failed.");
  }
  const session = (await response.json()) as { access_token: string; user: { display_name: string } };
  window.localStorage.setItem(TOKEN_KEY, session.access_token);
  return session;
}

export function logout() {
  window.localStorage.removeItem(TOKEN_KEY);
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const accessToken = await token();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${accessToken}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  let response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (response.status === 401) {
    window.localStorage.removeItem(TOKEN_KEY);
    headers.set("Authorization", `Bearer ${await token()}`);
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  }
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `API request failed (${response.status}).`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function authenticatedBlob(url: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${await token()}`);
  const response = await fetch(url, { ...init, headers });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Download failed (${response.status}).`);
  }
  return response.blob();
}

export async function openCitation(citation: Citation) {
  if (citation.source_type !== "case_document") {
    window.open(citation.url, "_blank", "noopener,noreferrer");
    return;
  }
  const blob = await authenticatedBlob(citation.url);
  const objectUrl = URL.createObjectURL(blob);
  window.open(objectUrl, "_blank", "noopener,noreferrer");
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
}

export const caseApi = {
  list: () => apiRequest<ApiCase[]>("/cases"),
  create: (payload: Omit<ApiCase, "id" | "owner_id" | "status" | "created_at" | "updated_at">) =>
    apiRequest<ApiCase>("/cases", { method: "POST", body: JSON.stringify(payload) }),
  analyze: (caseId: number) =>
    apiRequest<AnalysisResponse>(`/cases/${caseId}/analyze`, { method: "POST" }),
  latestAnalysis: (caseId: number) =>
    apiRequest<AnalysisResponse>(`/cases/${caseId}/analysis/latest`),
  ask: (caseId: number, question: string, inputLanguage = "English", responseLanguage = "English") =>
    apiRequest<AskResponse>(`/cases/${caseId}/ask`, {
      method: "POST",
      body: JSON.stringify({ question, input_language: inputLanguage, language: responseLanguage }),
    }),
  report: (caseId: number) =>
    apiRequest<{
      report_title: string;
      case: ApiCase;
      analysis: AnalysisResult;
      generated_at: string;
      disclaimer: string;
    }>(`/cases/${caseId}/report`),
  reportPdf: (caseId: number) =>
    authenticatedBlob(`${API_BASE_URL}/cases/${caseId}/report?format=pdf`),
  uploadDocument: (caseId: number, file: File) => {
    const body = new FormData();
    body.append("file", file);
    return apiRequest<{ id: number; filename: string; sha256: string; status: string; page_count: number; chunk_count: number }>(
      `/cases/${caseId}/documents`,
      { method: "POST", body },
    );
  },
  documents: (caseId: number) =>
    apiRequest<Array<{ id: number; filename: string; sha256: string; status: string; page_count: number; chunk_count: number; size_bytes: number; embedding_provider?: string | null; embedding_model?: string | null; embedding_revision?: string | null }>>(`/cases/${caseId}/documents`),
  deleteDocument: (caseId: number, documentId: number) =>
    apiRequest<void>(`/cases/${caseId}/documents/${documentId}`, { method: "DELETE" }),
  reindex: (caseId: number) =>
    apiRequest<{ id: number; status: string; embedding_model: string; embedding_revision: string }>(`/cases/${caseId}/reindex`, { method: "POST" }),
  reindexJobs: (caseId: number) =>
    apiRequest<Array<{ id: number; status: string; embedding_model: string; embedding_revision: string; result: Record<string, unknown>; error?: string | null; created_at: string; completed_at?: string | null }>>(`/cases/${caseId}/reindex-jobs`),
  designAround: (caseId: number) =>
    apiRequest<AnalysisResult["design_around"]>(`/cases/${caseId}/design-around`),
  sourceChanges: () =>
    apiRequest<{ snapshots: Array<{ id: number; source_id: string; url: string; status: string; content_sha256?: string | null; http_status?: number | null; change_summary: Record<string, unknown>; checked_at: string }> }>("/sources/changes"),
  requestExpertReview: (caseId: number, reviewType: string, notes?: string) =>
    apiRequest<{ id: number; status: string }>(`/cases/${caseId}/expert-review`, {
      method: "POST",
      body: JSON.stringify({ review_type: reviewType, notes }),
    }),
};
