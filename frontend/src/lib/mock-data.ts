// src/lib/mock-data.ts
// Mock data layer for IP-SAKTI 360 — Ayurvedic IP, ABS & regulatory intelligence assistant.
// Themed around a fictional case: a herbal stress-management formulation
// (Ashwagandha, Brahmi, Tulsi) targeting the Indian market.

/* ------------------------------------------------------------------ */
/* Interfaces                                                          */
/* ------------------------------------------------------------------ */

export interface Case {
  id: string;
  productDescription: string;
  ingredients: string[];
  jurisdiction: string;
  productType: string;
  createdAt: string;
  updatedAt: string;
  status: "draft" | "analyzing" | "review-needed" | "complete";
}

export interface GenomeNode {
  id: string;
  label: string;
  layer: "traditional" | "evidence" | "regulation" | "ip";
  status: "known" | "inventive" | "needs-evidence" | "uncertain";
  confidence: "High" | "Medium" | "Low";
  description: string;
  sources: string[];
  relationships: string[];
}

export interface EvidenceItem {
  source: string;
  authority: string;
  section: string;
  status: "supports" | "inference" | "uncertain";
  confidence: "High" | "Medium" | "Low";
}

export interface IPRoute {
  name: string;
  status: string;
  relevance: "High" | "Medium" | "Low";
  reason: string;
  evidence: string;
  nextStep: string;
}

export interface RegulatoryStep {
  title: string;
  type: "fact" | "interpretation" | "missing";
  detail: string;
}

export interface RoadmapStep {
  number: number;
  title: string;
  status: "complete" | "in-progress" | "not-started";
  evidence: string;
  blocker: string | null;
  next: string;
}

/* ------------------------------------------------------------------ */
/* Mock Case                                                           */
/* ------------------------------------------------------------------ */

export const MOCK_CASE: Case = {
  id: "case-ip360-0198",
  productDescription:
    "A standardized polyherbal formulation combining Ashwagandha (Withania somnifera) root extract, Brahmi (Bacopa monnieri) whole-plant extract, and Tulsi (Ocimum sanctum) leaf extract, delivered as a film-coated tablet for daily stress management and mental resilience support.",
  ingredients: [
    "Withania somnifera (Ashwagandha) root extract, standardized to 5% withanolides",
    "Bacopa monnieri (Brahmi) whole-plant extract, standardized to 20% bacosides",
    "Ocimum sanctum (Tulsi) leaf extract, standardized to 2% ursolic acid",
  ],
  jurisdiction: "India",
  productType: "Ayurvedic proprietary medicine (nutraceutical adjunct)",
  createdAt: "2026-06-02T09:14:00+05:30",
  updatedAt: "2026-08-21T17:42:00+05:30",
  status: "review-needed",
};

/* ------------------------------------------------------------------ */
/* Genome Nodes (10, across all 4 layers)                              */
/* ------------------------------------------------------------------ */

export const MOCK_GENOME_NODES: GenomeNode[] = [
  {
    id: "gn-01",
    label: "Ashwagandha as a Rasayana for vitality",
    layer: "traditional",
    status: "known",
    confidence: "High",
    description:
      "Withania somnifera root is classically documented as a Rasayana (rejuvenative) used to support strength, vitality, and resistance to stress.",
    sources: ["Charaka Samhita, Chikitsa Sthana 1.4", "TKDL entry AYU-0472"],
    relationships: ["gn-04", "gn-06"],
  },
  {
    id: "gn-02",
    label: "Brahmi for Medhya (cognitive) support",
    layer: "traditional",
    status: "known",
    confidence: "High",
    description:
      "Bacopa monnieri is classified among the Medhya Rasayanas, traditionally used to support memory, concentration, and calm mental function.",
    sources: ["Charaka Samhita, Chikitsa Sthana 1.3", "TKDL entry AYU-0655"],
    relationships: ["gn-05", "gn-07"],
  },
  {
    id: "gn-03",
    label: "Tulsi as an adaptogenic and calming herb",
    layer: "traditional",
    status: "known",
    confidence: "Medium",
    description:
      "Ocimum sanctum has a long record of household and classical use for calming the mind and supporting general resilience, though specific stress-response claims are less codified than for Ashwagandha or Brahmi.",
    sources: ["Sushruta Samhita, Sutra Sthana 38", "TKDL entry AYU-0910"],
    relationships: ["gn-06"],
  },
  {
    id: "gn-04",
    label: "Ashwagandha reduces serum cortisol under chronic stress",
    layer: "evidence",
    status: "known",
    confidence: "Medium",
    description:
      "Randomized controlled trials report statistically significant reductions in serum cortisol and perceived stress scores with standardized root extract at 300–600 mg/day.",
    sources: [
      "Chandrasekhar et al., Indian Journal of Psychological Medicine, 2012",
      "Lopresti et al., Medicine, 2019",
    ],
    relationships: ["gn-01", "gn-08"],
  },
  {
    id: "gn-05",
    label: "Brahmi improves memory-related outcomes in adults",
    layer: "evidence",
    status: "known",
    confidence: "Medium",
    description:
      "Multiple 12-week trials show improved delayed recall and reduced state anxiety with standardized Bacopa extract, though effect sizes are moderate and trial quality is variable.",
    sources: [
      "Stough et al., Psychopharmacology, 2001",
      "Pase et al., Journal of Alternative and Complementary Medicine, 2012",
    ],
    relationships: ["gn-02", "gn-08"],
  },
  {
    id: "gn-06",
    label: "No published trial data on the specific three-herb combination",
    layer: "evidence",
    status: "needs-evidence",
    confidence: "Low",
    description:
      "Individual herbs have supporting trials, but no identified clinical study evaluates Ashwagandha, Brahmi, and Tulsi together at the proposed ratio and dose — this combination-level claim is currently unsupported.",
    sources: ["Internal literature review, IP-SAKTI evidence scan, Aug 2026"],
    relationships: ["gn-01", "gn-02", "gn-03", "gn-09"],
  },
  {
    id: "gn-07",
    label: "Bacoside content variability across suppliers",
    layer: "evidence",
    status: "uncertain",
    confidence: "Low",
    description:
      "Bacoside standardization methods vary between HPLC and spectrophotometric assays across suppliers, creating a traceability gap for the claimed 20% bacoside specification.",
    sources: ["Internal QA note, supplier audit, 2026"],
    relationships: ["gn-02"],
  },
  {
    id: "gn-08",
    label: "AYUSH classification as a proprietary Ayurvedic medicine",
    layer: "regulation",
    status: "known",
    confidence: "High",
    description:
      "The formulation qualifies for classification as a proprietary Ayurvedic medicine under the Drugs and Cosmetics Act, 1940 and Rules, 1945, given its multi-ingredient, non-classical ratio.",
    sources: [
      "Drugs and Cosmetics Rules, 1945, Schedule T",
      "IP India — Guidelines for Examination of Ayush Related Inventions, 2021",
    ],
    relationships: ["gn-04", "gn-05", "gn-10"],
  },
  {
    id: "gn-09",
    label: "Biological Diversity Act clearance for sourced Brahmi",
    layer: "regulation",
    status: "needs-evidence",
    confidence: "Medium",
    description:
      "Wild-harvested Bacopa monnieri sourced from Madhya Pradesh may trigger access and benefit-sharing obligations; state biodiversity board approval has not yet been confirmed on file.",
    sources: ["Biological Diversity Act, 2002", "National Biodiversity Authority, ABS Guidelines, 2014"],
    relationships: ["gn-06", "gn-02"],
  },
  {
    id: "gn-10",
    label: "Process patent opportunity for the tri-herb standardization method",
    layer: "ip",
    status: "inventive",
    confidence: "Medium",
    description:
      "The specific co-extraction and standardization process for combining three actives at a fixed withanolide-bacoside-ursolic acid ratio is not disclosed in identified prior art and may support a process claim.",
    sources: ["IP India patent search, Aug 2026", "TKDL prior-art cross-check, Aug 2026"],
    relationships: ["gn-08", "gn-06"],
  },
];

/* ------------------------------------------------------------------ */
/* Evidence Items (5)                                                   */
/* ------------------------------------------------------------------ */

export const MOCK_EVIDENCE: EvidenceItem[] = [
  {
    source: "Charaka Samhita, Chikitsa Sthana 1.4",
    authority: "Classical Ayurvedic text (TKDL-indexed)",
    section: "Rasayana Adhyaya, verses 30–34",
    status: "supports",
    confidence: "High",
  },
  {
    source: "Chandrasekhar et al., Indian Journal of Psychological Medicine, 2012",
    authority: "Peer-reviewed clinical trial",
    section: "Results, Table 3 — serum cortisol outcomes",
    status: "supports",
    confidence: "Medium",
  },
  {
    source: "TKDL entry AYU-0472",
    authority: "Traditional Knowledge Digital Library",
    section: "Formulation record, Withania somnifera",
    status: "supports",
    confidence: "High",
  },
  {
    source: "Internal literature review, IP-SAKTI evidence scan, Aug 2026",
    authority: "Internal desk research",
    section: "Combination-level efficacy assessment",
    status: "uncertain",
    confidence: "Low",
  },
  {
    source: "IP India — Guidelines for Examination of Ayush Related Inventions, 2021",
    authority: "Office of the Controller General of Patents, Designs and Trade Marks",
    section: "Section 4.3 — Novelty over traditional knowledge",
    status: "inference",
    confidence: "Medium",
  },
];

/* ------------------------------------------------------------------ */
/* IP Routes (5)                                                        */
/* ------------------------------------------------------------------ */

export const MOCK_IP_ROUTES: IPRoute[] = [
  {
    name: "Process Patent",
    status: "Recommended — draft claims in progress",
    relevance: "High",
    reason:
      "The co-extraction and fixed-ratio standardization process for the three actives is not found in TKDL or examined prior art searches.",
    evidence: "TKDL prior-art cross-check (Aug 2026); IP India patent search (Aug 2026)",
    nextStep: "Engage a patent agent to draft process claims and file a provisional specification.",
  },
  {
    name: "Composition Patent",
    status: "Not recommended — weak novelty position",
    relevance: "Low",
    reason:
      "Each individual herb's traditional use for stress and cognitive support is well documented, making a composition-of-matter claim vulnerable to a prior-art rejection.",
    evidence: "Charaka Samhita, Chikitsa Sthana 1.3–1.4; TKDL entries AYU-0472, AYU-0655",
    nextStep: "Do not pursue as a standalone route; fold any protectable elements into the process claim.",
  },
  {
    name: "Trademark",
    status: "Available — recommended for immediate filing",
    relevance: "High",
    reason: "Proposed brand name and logo returned no conflicting marks in the same class on preliminary search.",
    evidence: "Trade Marks Registry preliminary search, Aug 2026",
    nextStep: "File a Class 5 trademark application before public disclosure or sale.",
  },
  {
    name: "Trade Secret (extraction parameters)",
    status: "Viable — pending disclosure review",
    relevance: "Medium",
    reason:
      "Exact temperature, solvent ratio, and sequencing parameters used in co-extraction are not required to be disclosed in a process patent claim if drafted at the appropriate level of generality.",
    evidence: "Internal process documentation, R&D notebook 2026-04",
    nextStep: "Confirm which parameters can remain confidential without weakening the patent's enablement requirement.",
  },
  {
    name: "Geographical Indication",
    status: "Not applicable",
    relevance: "Low",
    reason:
      "The formulation is not tied to a specific registered region of cultivation or a community-linked classical product name, so GI protection does not apply.",
    evidence: "GI Registry classification review, Aug 2026",
    nextStep: "No action required under this route.",
  },
];

/* ------------------------------------------------------------------ */
/* Regulatory Steps (5)                                                 */
/* ------------------------------------------------------------------ */

export const MOCK_REGULATORY_STEPS: RegulatoryStep[] = [
  {
    title: "Product classification",
    type: "fact",
    detail:
      "Classified as a proprietary Ayurvedic medicine under Schedule T of the Drugs and Cosmetics Rules, 1945, since the three-herb ratio does not match a classical formulation listed in the authoritative texts.",
  },
  {
    title: "Manufacturing license requirement",
    type: "fact",
    detail:
      "Requires a manufacturing license for proprietary Ayurvedic medicine from the State Licensing Authority under Rule 154 of the Drugs and Cosmetics Rules, 1945, prior to commercial production.",
  },
  {
    title: "Likely AYUSH Premium Mark eligibility",
    type: "interpretation",
    detail:
      "Given documented sourcing and standardization protocols, the product is likely — though not yet confirmed — to meet the quality criteria for the AYUSH Premium Mark certification scheme.",
  },
  {
    title: "Biological Diversity Act clearance status",
    type: "missing",
    detail:
      "No confirmed record on file of State Biodiversity Board approval for wild-harvested Bacopa monnieri sourced from Madhya Pradesh, as required under the Biological Diversity Act, 2002.",
  },
  {
    title: "Labeling compliance for cortisol/stress claims",
    type: "missing",
    detail:
      "Draft packaging language referencing 'clinically proven stress reduction' has not been matched against Schedule T labeling restrictions or substantiated with combination-specific trial data.",
  },
];

/* ------------------------------------------------------------------ */
/* Roadmap Steps (8)                                                    */
/* ------------------------------------------------------------------ */

export const MOCK_ROADMAP_STEPS: RoadmapStep[] = [
  {
    number: 1,
    title: "Confirm ingredient sourcing and supplier documentation",
    status: "complete",
    evidence: "Supplier certificates of analysis for Ashwagandha, Brahmi, and Tulsi extracts on file.",
    blocker: null,
    next: "Proceed to biodiversity and ABS review.",
  },
  {
    number: 2,
    title: "Biological Diversity Act / ABS clearance for Brahmi sourcing",
    status: "in-progress",
    evidence: "State Biodiversity Board application submitted, Madhya Pradesh, July 2026.",
    blocker: "Awaiting board approval; estimated 8–12 week processing time.",
    next: "Follow up with the Madhya Pradesh State Biodiversity Board for status update.",
  },
  {
    number: 3,
    title: "TKDL and prior-art cross-check",
    status: "complete",
    evidence: "TKDL search across AYU-0472, AYU-0655, and AYU-0910 completed; no conflicting combination formulation found.",
    blocker: null,
    next: "Use findings to support process patent novelty argument.",
  },
  {
    number: 4,
    title: "Combination-level clinical evidence generation",
    status: "not-started",
    evidence: "No trial currently exists evaluating the three-herb combination at the proposed dose.",
    blocker: "No pilot study commissioned yet; budget approval pending.",
    next: "Commission a pilot RCT to support the combined stress-reduction claim before broad marketing.",
  },
  {
    number: 5,
    title: "Draft and file process patent application",
    status: "in-progress",
    evidence: "Provisional claim language drafted covering the co-extraction and standardization method.",
    blocker: "Awaiting final confirmation of trade-secret vs. disclosed parameters.",
    next: "Finalize claim scope with patent agent and file provisional specification.",
  },
  {
    number: 6,
    title: "AYUSH manufacturing license application",
    status: "not-started",
    evidence: "Facility GMP audit scheduled for September 2026.",
    blocker: "License application cannot be submitted until GMP audit is complete.",
    next: "Complete GMP audit and submit Form 25 application to the State Licensing Authority.",
  },
  {
    number: 7,
    title: "Trademark filing",
    status: "not-started",
    evidence: "Preliminary trademark search completed with no conflicts identified.",
    blocker: null,
    next: "File Class 5 trademark application prior to public launch.",
  },
  {
    number: 8,
    title: "Label and claims compliance review",
    status: "not-started",
    evidence: "Draft packaging copy prepared but not yet reviewed against Schedule T restrictions.",
    blocker: "Cannot finalize until combination-level evidence (Step 4) is available or claims are scoped back.",
    next: "Revise claim language to structure/function framing pending clinical data, then submit for legal review.",
  },
];