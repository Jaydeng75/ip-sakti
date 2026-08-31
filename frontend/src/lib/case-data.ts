export interface Case {
  id: string;
  backendId?: number;
  title?: string;
  productDescription: string;
  ingredients: string[];
  jurisdiction: string;
  productType: string;
  createdAt: string;
  updatedAt: string;
  status:
    | "draft"
    | "analyzing"
    | "review-needed"
    | "complete"
    | "analyzed"
    | "review_requested"
    | "archived";
}

export const DEFAULT_CASE: Case = {
  id: "no-active-case",
  title: "No active innovation case",
  productDescription: "Create an innovation analysis to establish shared case context.",
  ingredients: [],
  jurisdiction: "No market selected",
  productType: "Classification pending",
  createdAt: new Date(0).toISOString(),
  updatedAt: new Date(0).toISOString(),
  status: "draft",
};

export const EXAMPLE_CASE = {
  productDescription:
    "A standardized polyherbal formulation combining Ashwagandha (Withania somnifera) root extract, Brahmi (Bacopa monnieri) whole-plant extract, and Tulsi (Ocimum sanctum) leaf extract, delivered as a film-coated tablet for daily stress management and mental resilience support.",
  ingredients: [
    "Withania somnifera (Ashwagandha) root extract, standardized to 5% withanolides",
    "Bacopa monnieri (Brahmi) whole-plant extract, standardized to 20% bacosides",
    "Ocimum sanctum (Tulsi) leaf extract, standardized to 2% ursolic acid",
  ],
};
