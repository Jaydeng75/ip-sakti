# Production readiness and operating boundary

## Implemented controls

- Argon2 passwords, signed expiring JWTs, owner isolation and administrator role checks.
- Production startup rejects demo mode, self-registration, weak signing keys, SQLite and disabled malware scanning.
- Exact CORS origins, trusted hosts, request limits, browser/API security headers and generic server errors.
- PDF/TXT/DOCX validation, compressed-file expansion protection, optional fail-closed ClamAV scanning and SHA-256 integrity records.
- Text extraction, page-aware chunking, hybrid lexical/vector retrieval and protected case-document citations.
- Safe abstention, explicit claim/support types, confidence, limitations and mandatory human-review flags.
- Alembic schema versioning, PostgreSQL support, non-root containers and health checks.
- Tamper-evident audit chaining and administrator integrity verification.
- IndicTrans2 model revisions pinned to reviewed commits, dual-direction caching, optional startup preload and machine-translation provenance.
- PDF decision records with evidence lineage, corpus/run identity and deterministic record hashes.

## Required deployment controls

These are environment responsibilities and cannot be completed by repository code alone:

- Terminate TLS at an approved ingress/WAF and enforce distributed rate limits there.
- Store secrets in a managed secret service; never place tokens in Git or client-side variables.
- Use a TLS-enabled managed PostgreSQL service with point-in-time recovery, encrypted backups and tested restoration.
- Replace the local evidence volume with approved encrypted object storage or a controlled persistent volume, with retention/deletion policy and access logging.
- Connect an approved ClamAV service and keep signatures updated.
- Forward redacted logs, metrics and traces to the organisation's monitoring system with alerts and incident response.
- Configure an approved enterprise identity provider/MFA flow. The included local login is suitable for controlled pilots, not organisation-wide identity governance.
- Run dependency/container scanning, SBOM generation, signed images and protected CI/CD environments.

The complete GitHub Actions definition is stored at `docs/github-actions-ci.template.yml`. Copy it to `.github/workflows/ci.yml` using a GitHub credential with the `workflow` scope; the current repository OAuth credential cannot modify workflow files.

## Data and professional approval gates

- Obtain licences or API authorization for patent databases and scientific full text.
- Use TKDL only through authorized access. The application deliberately makes no unrestricted-access claim.
- Snapshot, version and legally review every official-source corpus update.
- Validate retrieval recall, citation correctness, abstention, terminology and translations against a bilingual expert test set.
- Obtain patent, regulatory, ABS, privacy/security and scientific approval before relying on results for filings or market entry.

Until these external gates are signed off, deploy the platform as decision-support software with the included disclaimer—not as an automated legal opinion.
