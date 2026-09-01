export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const TOKEN_KEY = "ip-sakti-token";
const DEVICE_KEY = "ip-sakti-device-credentials";

type ApiErrorPayload = {
  detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>;
};

function apiErrorMessage(payload: ApiErrorPayload | null, fallback: string) {
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) {
    const messages = payload.detail.map((item) => item.msg).filter(Boolean);
    if (messages.length) return messages.join(" ");
  }
  return fallback;
}

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
  source_type?: "official" | "case_document" | "scientific_literature";
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
  display_value?: string;
  score_is_probability?: boolean;
  primary_finding?: string;
  positive_signals?: string[];
  negative_signals?: string[];
  missing_evidence?: string[];
  what_changes_score?: string[];
  finding?: string;
  why?: string;
  evidence_basis?: string[];
  fix?: string;
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
    status?: string;
    candidate_pathways?: string[];
    decision_factors?: string[];
    citations: Citation[];
  };
  decision_brief: {
    strongest_protectable_element: string;
    highest_tk_risk: string;
    largest_scientific_gap: string;
    regulatory_status: string;
    abs_status: string;
    most_important_next_step: string;
    known: string[];
    not_established: string[];
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
    readiness_score?: number;
    match_counts?: Record<string, number>;
    evidence_layers?: Record<string, string>;
    gaps: string[];
    citations: Citation[];
    study_matrix?: ScientificStudyCollection;
    traditional_knowledge_records?: TraditionalKnowledgeRecord[];
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
      basis?: string;
      claim_type: "inference";
      requires_human_review: boolean;
      citations: Citation[];
    }>;
    reviewer_inputs: Record<string, string[]>;
    notice: string;
  };
  case_specific_analysis: {
    input_completeness: {
      score: number;
      supplied_count: number;
      required_count: number;
      status: string;
      supplied: Array<CaseFact & { value: string }>;
      missing: CaseFact[];
    };
    technical_features: TechnicalFeature[];
    novelty_claim_chart: NoveltyChartRow[];
    patent_landscape: PatentLandscape;
    traditional_knowledge: {
      status: string;
      records: TraditionalKnowledgeRecord[];
      query: string;
      search_url: string;
      authorized_search_required: boolean;
      access_scope?: string;
      integration_mode?: string;
      supported_imports?: string[];
      limitation: string;
    };
    scientific_studies: ScientificStudyCollection;
    technical_advisory: {
      feature_assessments: Array<{
        id: string;
        feature: string;
        submitted_value: string;
        status: string;
        status_label: string;
        why: string;
        evidence_basis: string[];
        advisory: string;
      }>;
      inventive_step: {
        level: string;
        finding: string;
        weakest_element: string;
        reasoning: string[];
        how_to_strengthen: string[];
      };
      differentiation_advisor: { current: string; problem: string; ways_to_strengthen: string[] };
      change_scenarios: Array<{
        change: string;
        impacts: Array<{ area: string; direction: string; reason: string }>;
      }>;
      scientific_advisor: { supported: string; not_supported: string[]; best_next_study: string };
      classification_resolver: { why_unresolved: string; questions: string[] };
      strength_actions: Array<{
        rank: number;
        title: string;
        impact: string;
        why: string;
        what_to_test: string[];
        deliverable: string;
        strengthens: string[];
      }>;
      notice: string;
    };
    specific_recommendations: Array<{
      title: string;
      basis: string;
      action: string;
      decision_output: string;
    }>;
    data_requests: Array<{ field: string; question: string; blocks: string }>;
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

type CaseFact = { key: string; label: string; request: string; blocks: string };

type TechnicalFeature = {
  id: string;
  feature: string;
  submitted_value: string;
  status: string;
  evidence_required: string;
  decision_areas: string;
};

type ClaimOverlap = {
  publication_number?: string | null;
  family_id?: string | null;
  claim?: string | null;
  matched_terms: string[];
  claim_excerpt: string;
  url?: string | null;
  source?: string | null;
};

type NoveltyChartRow = TechnicalFeature & {
  reason: string;
  claim_overlaps: ClaimOverlap[];
};

type PatentRecord = {
  publication_number: string;
  docdb?: string;
  family_id?: string | null;
  title: string;
  claims: Array<{ claim: string; text: string }>;
  url: string;
  source: string;
};

type PatentLandscape = {
  status: string;
  provider: string;
  query: string;
  records: PatentRecord[];
  family_count: number;
  search_url: string;
  limitation?: string;
  coverage_note?: string;
  dataset_modified_at?: string | null;
  bytes_billed?: number | null;
};

type TraditionalKnowledgeRecord = {
  source_title: string;
  formulation: string;
  exact_passage: string;
  locator?: string | null;
  content_sha256?: string | null;
  matched_ingredients: string[];
  citation: Citation;
  source_status: string;
};

type ScientificStudy = {
  pmid?: string | null;
  pmcid?: string | null;
  title: string;
  journal: string;
  publication_date: string;
  doi?: string | null;
  url: string;
  population: string;
  dose: string;
  endpoints: string;
  limitations: string;
  abstract_excerpt: string;
  full_text_url?: string | null;
  appraisal_status?: string;
  study_type?: string;
  appraisal_framework?: string;
  study_design?: string;
  comparator?: string;
  duration?: string;
  numerical_results?: string;
  adverse_events?: string;
  funding?: string;
  conflicts?: string;
  license?: string | null;
  risk_of_bias?: {
    rating: string;
    present_signals: string[];
    missing_signals: string[];
    notice: string;
  } | null;
  section_locators?: Record<string, string | null>;
  locator?: string | null;
  source_status: string;
  evidence_role?: "direct_product" | "ingredient_clinical" | "delivery_system" | "excluded_irrelevant";
  match_score?: number;
  match_profile?: {
    ingredient: boolean;
    population: boolean;
    endpoint: boolean;
    dose: boolean;
    standardization: boolean;
    formulation: boolean;
    endpoint_hits: string[];
    formulation_hits: string[];
    quality: string;
  };
};

type ScientificStudyCollection = {
  status: string;
  provider?: string;
  query: string;
  records: ScientificStudy[];
  search_url: string;
  uploaded_record_count?: number;
  live_record_count?: number;
  full_text_appraised_count?: number;
  abstract_only_count?: number;
  notice?: string;
  match_counts?: Record<string, number>;
  evidence_layers?: Record<string, string>;
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
  confidence_label: string;
  confidence_basis: string;
  intent: string;
  evidence_summary: Record<string, number> | null;
  methodology: string[];
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
    const payload = (await response.json().catch(() => null)) as ApiErrorPayload | null;
    throw new Error(apiErrorMessage(payload, "Sign-in failed."));
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
    const payload = (await response.json().catch(() => null)) as ApiErrorPayload | null;
    throw new Error(apiErrorMessage(payload, `API request failed (${response.status}).`));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function authenticatedBlob(url: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${await token()}`);
  const response = await fetch(url, { ...init, headers });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ApiErrorPayload | null;
    throw new Error(apiErrorMessage(payload, `Download failed (${response.status}).`));
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
