# Three-minute judge demonstration

## Before the session

1. Start the stack with the neural and configured patent-provider overlays described in `README.md`.
2. Run `python scripts/warm_demo.py --case-id <main-case-id>` inside the backend container. Confirm it reports `demo_ready`, the two pinned neural models, at least one PMC full-text appraisal and cached patent records.
3. Set `INDICTRANS_PRELOAD_MODELS=true` on a host with enough memory, or run one Hindi translation before judging.
4. Open `http://localhost:3000`, then visit **Saved Cases** and select the warmed case.
5. Keep a short, machine-readable PDF or TXT evidence document ready. Include one distinctive term so retrieval is obvious.

## Judge flow

1. **0:00–0:25 — Problem and case:** Open the warmed case and show its ingredient quantities, extraction ratio, release profile and manufacturing parameters.
2. **0:25–0:55 — Defensible novelty:** Show the Innovation Genome, patent-family candidates and feature-level overlap boundaries. State that this is screening, not FTO clearance.
3. **0:55–1:25 — TK and science:** Show the TKDL Bridge from official query to authorized-result import and exact locator, then the PMC full-text/abstract-only counts, dose, comparator, endpoints, numerical results, safety and appraisal signals.
4. **1:25–1:55 — Adversarial intelligence:** Open **Challenge My Innovation**, switch reviewers, then show the fact-linked **Design Around** alternatives.
5. **1:55–2:25 — Grounded multilingual answer:** Ask one prepared question, open its evidence citation, then switch the response to Hindi while retaining authoritative English.
6. **2:25–2:50 — Decision record:** Open the jurisdiction comparison and generated report with corpus/run identifiers, evidence register, record hash and disclaimer.
7. **2:50–3:00 — Close:** “IP-SAKTI converts an Ayurvedic idea into a traceable IP, evidence, ABS and market-entry decision workspace—without presenting traditional use or AI inference as legal or clinical fact.”

## Claims to avoid

- Do not describe the registry as a complete freedom-to-operate or patent-clearance search.
- Do not claim public or unrestricted TKDL access.
- Do not describe traditional use as clinical efficacy.
- Do not describe machine translation as authoritative legal translation.
- Do not describe a user-uploaded document as verified merely because it was retrieved.
