# IP-SAKTI Sahayak 360

Source-grounded innovation intelligence for Ayurvedic and biological-resource products. The application maintains a persistent Innovation Case across traditional knowledge, scientific evidence, IP strategy, regulatory/ABS review, jurisdiction comparison, adversarial review and reports.

## What is implemented

- Polished Next.js 16, TypeScript and Tailwind interface with the 11 requested navigation modules.
- Seven priority workspaces: Dashboard, Analyze Innovation, Traditional Knowledge graph, Scientific Evidence, IP Strategy, Jurisdiction Compare and Challenge My Innovation.
- Persistent case context shared across modules and a saved-case portfolio.
- FastAPI API with registration/login, Argon2 password hashing, signed JWT sessions, owner isolation, role checks and audit records.
- Deterministic grounded screening engine with explicit confidence, source status, jurisdiction, effective date, limitations and safe abstention.
- Product classification, innovation genome, TK/prior-art graph, evidence separation, multi-route IP strategy, six-step regulatory/ABS flow and India/EU/US/international comparison.
- Split-screen Ask IP-SAKTI experience with clickable official citations and claim-type labels.
- IndicTrans2 multilingual input/output for all 22 scheduled Indian languages, with explicit machine-translation provenance and the authoritative English answer retained.
- Evidence uploads restricted to PDF/TXT/DOCX, size checked, PDF signature checked and stored with SHA-256 integrity metadata.
- Human expert-review requests and structured case-report exports.
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

The Compose configuration enables demo authentication for local evaluation only. Production startup rejects demo mode and a default/short signing key.

## Run without Docker

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
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
- `POST|GET /api/v1/cases/{id}/documents`
- `POST /api/v1/cases/{id}/expert-review`, `GET /api/v1/cases/{id}/report`
- `GET /api/v1/sources`, `GET /api/v1/admin/audit`

## Source and decision-safety model

`backend/data/sources.json` is a versioned curated registry of primary law, official regulation/guidance and treaty sources. The engine does not claim that this small registry is a comprehensive patent, TKDL, scientific-literature or regulatory corpus. If retrieval does not find relevant support, Ask IP-SAKTI abstains. All screening conclusions require human review.

Traditional use is kept explicitly separate from clinically established efficacy. Jurisdictions are not merged into one rule set. Treaty status is described separately from domestic implementation.

## Production deployment checklist

- Set `IPSAKTI_ENVIRONMENT=production`, a random `IPSAKTI_SECRET_KEY`, PostgreSQL TLS credentials and the exact allowed origin list.
- Keep `IPSAKTI_DEMO_MODE=false`; connect enterprise identity/SSO if public self-registration is inappropriate.
- Put the API behind TLS, a WAF/API gateway, rate limiting and centralized secret management.
- Use object storage with malware scanning and retention policies for uploaded evidence.
- Add managed database backups, schema migration automation, log redaction, monitoring and alerting.
- Replace/extend the curated registry with licensed patent, TKDL-authorized, legal and scientific corpora; add document-level ingestion, chunk lineage and retrieval evaluation.
- Run IndicTrans2 behind an authenticated private service, pin reviewed model revisions, monitor latency/memory and validate legal terminology with bilingual experts. Translations must remain labelled as machine-generated rather than authoritative legal text.
- Have qualified patent, regulatory, ABS and scientific experts approve the corpus, rules and disclaimers before real decisions or filings.

This repository is a production-oriented engineering baseline and decision-support prototype. It is not, by itself, a legally complete production service or professional advice.
