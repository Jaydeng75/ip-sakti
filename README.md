# IP-SAKTI Sahayak 360

Source-grounded innovation intelligence for Ayurvedic and biological-resource products. The application maintains a persistent Innovation Case across traditional knowledge, scientific evidence, IP strategy, regulatory/ABS review, jurisdiction comparison, adversarial review and reports.

## What is implemented

- Polished Next.js 16, TypeScript and Tailwind interface with the 11 requested navigation modules.
- Seven priority workspaces: Dashboard, Analyze Innovation, Traditional Knowledge graph, Scientific Evidence, IP Strategy, Jurisdiction Compare and Challenge My Innovation.
- Persistent case context shared across modules and a saved-case portfolio.
- FastAPI API with registration/login, Argon2 password hashing, signed JWT sessions, owner isolation, role checks and audit records.
- Hybrid evidence-retrieval and grounded screening engine with explicit confidence, source status, jurisdiction, effective date, limitations and safe abstention.
- Product classification, innovation genome, TK/prior-art graph, evidence separation, multi-route IP strategy, six-step regulatory/ABS flow and India/EU/US/international comparison.
- Split-screen Ask IP-SAKTI experience with clickable official citations and claim-type labels.
- IndicTrans2 multilingual input/output for all 22 scheduled Indian languages, with explicit machine-translation provenance and the authoritative English answer retained.
- Evidence uploads restricted to PDF/TXT/DOCX, format and expansion checked, optionally scanned by ClamAV, stored with SHA-256 integrity metadata, extracted, chunked and indexed.
- Case-document retrieval uses a configurable multilingual embedding provider, PostgreSQL full-text/pgvector candidate prefetch and a configurable reranker. Development retains an explicitly labelled deterministic outage fallback.
- Every indexed chunk records embedding provider, model and revision; every retrieved citation records lexical, semantic and reranker scores plus page/chunk and content-hash lineage.
- Analysis now includes a claim-to-evidence provenance graph and an Innovation Design-Around workspace that converts reviewer objections into testable technical alternatives.
- Case-specific analysis preserves quantities, extract ratios, standardization, dose, release profiles and critical process parameters instead of replacing missing facts with generic advice.
- Live PubMed retrieval discovers studies, then available PMC JATS full text is structurally appraised for design, population, dose, comparator, duration, endpoints, numerical results, adverse events, funding, conflicts and author-reported limitations. Records without retrievable PMC XML remain visibly abstract-only. Credentialed Google Patents BigQuery or EPO OPS retrieval adds patent-family records and available claim text for feature-level overlap screening.
- The TKDL Bridge creates case-specific official-search terms, opens the session-aware TKDL interface and imports authorized PDF/TXT/DOCX results into an exact-passage register with page/chunk locators and SHA-256 lineage. Restricted TKDL content is never represented as publicly scraped or searched.
- Versioned reindex jobs and authoritative-source snapshots support model migrations and legal-change review.
- Human expert-review requests and branded PDF decision records with evidence registers, run/corpus identifiers and report hashes.
- Tamper-evident SHA-256 audit chaining, case-level audit history and administrator integrity verification.
- Alembic-managed schema baseline, controlled production Compose overlay, request rate limits, trusted hosts and browser/API security headers.
- Three pre-analysed demo cases are seeded for the local demo account.
- SQLite for simple local development and PostgreSQL in the supplied Compose stack.
- Backend tests, Python linting, frontend linting and production builds.

## Repository layout

```text
backend/                 FastAPI application, curated source registry and tests
frontend/                Next.js web application
translation-service/     Isolated AI4Bharat IndicTrans2 inference service
docker-compose.yml       Local integrated PostgreSQL + API + web stack
```

The duplicate `backend 2` prototype, committed bytecode, local databases, vector-store state, copied PDF and empty npm/next marker files were removed. There is now one backend entry point: `backend/main.py`.

## Run the complete stack

1. Copy the root environment template and replace its secrets.

   ```bash
   cp .env.example .env
   ```

2. Request access to both gated AI4Bharat models on Hugging Face: [English → Indic](https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M) and [Indic → English](https://huggingface.co/ai4bharat/indictrans2-indic-en-dist-200M). Create a read-only Hugging Face token and set `HF_TOKEN` in `.env`.

3. Start PostgreSQL, IndicTrans2, API and web application.

   ```bash
   docker compose up --build
   ```

4. Open [http://localhost:3000](http://localhost:3000). API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs) in development. The first multilingual request downloads the selected models and can take several minutes; the model cache is persisted in a Docker volume.

The Compose configuration enables demo authentication for local evaluation only. Production startup rejects demo mode, public self-registration, a default/short signing key and disabled malware scanning.

## Run without Docker

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn main:app --reload
```

Frontend, in a second terminal:

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

IndicTrans2, when running without Docker:

```bash
cd translation-service
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export INDICTRANS_HF_TOKEN=hf_your_read_token
uvicorn app:app --host 0.0.0.0 --port 8100
```

Then set `IPSAKTI_TRANSLATION_ENABLED=true` in `backend/.env`. IndicTrans2 checkpoints are substantial; CPU inference is suitable for evaluation and defaults to greedy decoding (`INDICTRANS_GENERATION_BEAMS=1`). An accelerator-backed service can raise beam search up to 5 for quality-sensitive production traffic. For a controlled deployment, replace both `main` revision values with reviewed Hugging Face commit hashes.

## Verification

```bash
cd backend
ruff check .
pytest -q

cd ../frontend
npm run lint
npm run build

cd ../translation-service
pytest -q
```

## API overview

- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- `GET|POST /api/v1/cases`, `GET|PATCH|DELETE /api/v1/cases/{id}`
- `POST /api/v1/cases/{id}/analyze`, `GET /api/v1/cases/{id}/analysis/latest`
- `POST /api/v1/cases/{id}/ask`, `GET /api/v1/cases/{id}/challenge`
- `POST|GET /api/v1/cases/{id}/documents`, authenticated document content and deletion endpoints
- `POST /api/v1/cases/{id}/expert-review`, `GET /api/v1/cases/{id}/report?format=pdf`
- `GET /api/v1/cases/{id}/audit`, `GET /api/v1/admin/audit/integrity`
- `GET /api/v1/sources`, `GET /api/v1/admin/audit`

## Source and decision-safety model

`backend/data/sources.json` is a versioned curated registry of primary law, official regulation/guidance, treaties and official live-data services. It is supplemented at analysis time by PubMed, available PMC full text and a configured Google Patents BigQuery or EPO OPS connector. The engine does not claim comprehensive patent, TKDL, scientific or regulatory clearance. If retrieval does not find relevant support, Ask IP-SAKTI abstains. All screening conclusions require human review.

## Live patent and scientific research

Docker Compose enables external research. PubMed uses NCBI ESearch/EFetch and returns the exact query and source links. For records carrying a PMCID, the backend requests PMC JATS XML and performs a structured full-text appraisal. It stores extracted findings and section locators rather than copying the article. PMC availability and licence terms are article-specific; non-PMC or failed retrievals remain explicitly labelled abstract-only. The reporting-signal screen is not a validated RoB 2 or ROBINS-I assessment. Set `IPSAKTI_NCBI_CONTACT_EMAIL`; an optional `IPSAKTI_NCBI_API_KEY` raises the permitted request rate.

To use the Google Patents public BigQuery tables, enable the BigQuery API and billing on the query project, provide Application Default Credentials through the deployment identity, and set:

```dotenv
IPSAKTI_PATENT_SEARCH_PROVIDER=google_bigquery
IPSAKTI_GOOGLE_CLOUD_PROJECT=your-billing-project
IPSAKTI_BIGQUERY_LOCATION=US
IPSAKTI_BIGQUERY_MAXIMUM_BYTES_BILLED=100000000000
```

The connector uses parameterized SQL, an LRU result cache and a per-query billing cap. Its default query searches extracted top terms and joins worldwide simple-family identifiers while deliberately excluding the costly full-claim column. It reports the source table modification time and links each candidate to Google Patents for claim verification. The result remains a screening set, not novelty or FTO clearance. Google stores public-dataset data, while the configured project pays query-processing charges.

For local Docker development, create `.env.bigquery` from `.env.bigquery.example`, point `GOOGLE_ADC_FILE` to the ADC JSON generated by `gcloud auth application-default login`, and start the provider with:

```bash
docker compose --env-file .env --env-file .env.bigquery -f docker-compose.yml -f docker-compose.bigquery.yml up -d --build backend frontend
```

The credential is mounted read-only under `/run/secrets` and remains excluded from Git.

Register an application for EPO Open Patent Services and set:

```dotenv
IPSAKTI_EPO_OPS_CONSUMER_KEY=...
IPSAKTI_EPO_OPS_CONSUMER_SECRET=...
```

Set `IPSAKTI_PATENT_SEARCH_PROVIDER=auto` to prefer configured BigQuery and otherwise use EPO OPS. Without credentials for either provider, the patent workspace shows `credential required`, preserves a manual search link and makes no claim-level or patent-family assertion. Production startup rejects a deployment without a configured patent provider. TKDL remains an authorized-access dependency: upload legally obtained extracts to get exact passage/page citations, or complete the search with an authorized patent professional.

## Evidence assurance and retrieval

Development defaults to `IPSAKTI_EMBEDDING_PROVIDER=deterministic` so the repository runs offline. This fallback is a feature hash, not a neural embedding and not an accuracy claim. Production startup rejects it.

For production, configure an OpenAI-compatible embeddings endpoint and a reranker endpoint:

```dotenv
IPSAKTI_EMBEDDING_PROVIDER=http
IPSAKTI_EMBEDDING_URL=https://embedding.internal.example/v1
IPSAKTI_EMBEDDING_API_KEY=...
IPSAKTI_EMBEDDING_MODEL=intfloat/multilingual-e5-small
IPSAKTI_EMBEDDING_REVISION=614241f622f53c4eeff9890bdc4f31cfecc418b3
IPSAKTI_EMBEDDING_DIMENSIONS=384
IPSAKTI_EMBEDDING_ALLOW_FALLBACK=false
IPSAKTI_RETRIEVAL_PREFETCH_LIMIT=50
IPSAKTI_RERANKER_PROVIDER=http
IPSAKTI_RERANKER_URL=https://reranker.internal.example/v1
IPSAKTI_RERANKER_API_KEY=...
IPSAKTI_RERANKER_MODEL=BAAI/bge-reranker-v2-m3
IPSAKTI_RERANKER_REVISION=953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e
```

The retrieval sequence is: PostgreSQL lexical and pgvector prefetch → score fusion → neural or explicitly labelled heuristic reranking → evidence-signal/abstention gate → top cited passages. Dense similarity alone cannot force a citation. Run `python evaluation.py` inside the backend environment to produce the starter retrieval report. The included dataset is an engineering smoke set; it must be replaced or supplemented with an expert-labelled bilingual benchmark before publishing an accuracy percentage.

The repository includes a self-hosted Sentence Transformers service. For a fail-closed neural demo, use `docker-compose.neural.yml`: it routes the backend to pinned `intfloat/multilingual-e5-small` embeddings and the pinned `BAAI/bge-reranker-v2-m3` cross-encoder, preloads both models and disables deterministic/heuristic outage fallback.

```bash
docker compose --profile neural --env-file .env --env-file .env.bigquery \
  -f docker-compose.yml -f docker-compose.bigquery.yml -f docker-compose.neural.yml \
  up -d --build retrieval backend frontend
```

The model cache persists in a Docker volume. Protect the internal service with `RETRIEVAL_SERVICE_TOKEN`. After the services are healthy, warm the models and persist the main demo analysis in PostgreSQL:

```bash
docker compose --profile neural --env-file .env --env-file .env.bigquery \
  -f docker-compose.yml -f docker-compose.bigquery.yml -f docker-compose.neural.yml \
  exec backend python scripts/warm_demo.py --case-id 11
```

The warm-up validates the embedding dimensions and neural reranker response, reindexes outdated case documents, and reuses a current persisted run when possible. `--force` creates one fresh external-research run and may incur the configured BigQuery query charge. The stored analysis lets every presentation screen load without calling PubMed, PMC or BigQuery again.

`POST /api/v1/cases/{case_id}/reindex` queues a versioned reindex job. `GET /api/v1/cases/{case_id}/reindex-jobs` exposes its status. Administrators can snapshot curated sources with `POST /api/v1/admin/sources/monitor`; detected changes remain review flags and are never silently treated as updated legal conclusions.

Traditional use is kept explicitly separate from clinically established efficacy. Jurisdictions are not merged into one rule set. Treaty status is described separately from domestic implementation.

## Deployment and demonstration

Use `docker-compose.production.yml` as an overlay only after supplying its required secrets, TLS PostgreSQL URL, exact origins/hosts and approved ClamAV endpoint. Run `alembic upgrade head` as part of each release; the backend container performs this automatically.

See [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) for the five-minute judge flow and [docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md) for implemented controls, deployment requirements and external approval gates.

This repository is a deployable, evidence-grounded decision-support platform. A real legal deployment still depends on approved infrastructure, licensed/authorized data and qualified professional validation; software cannot substitute for those external controls.
