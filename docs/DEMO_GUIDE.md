# Five-minute judge demonstration

## Before the session

1. Run `docker compose up -d --build` and wait until `docker compose ps` shows the API, database and translation service as healthy.
2. Set `INDICTRANS_PRELOAD_MODELS=true` on a host with enough memory, or run one Hindi translation before judging.
3. Open `http://localhost:3000`, then visit **Saved Cases**. The demo account contains three contrasting pre-analysed cases.
4. Keep a short, machine-readable PDF or TXT evidence document ready. Include one distinctive term so retrieval is obvious.

## Judge flow

1. Open **Controlled-release Ashwagandha Platform** and show that the same case follows the user through every module.
2. In **Traditional Knowledge**, explain the distinction between a graph relationship and a definitive prior-art finding. Point out restricted TKDL access.
3. In **Scientific Evidence**, upload the prepared document. The system extracts and indexes it, automatically reruns the case and shows document, page/chunk and SHA-256 lineage.
4. In **Ask IP-SAKTI**, ask about the distinctive term. Open the retrieved case-document citation beside the answer, then show its support status as `user-supplied-unverified`.
5. Ask an unrelated question to demonstrate safe abstention.
6. Switch the question and answer language to Hindi. Show the machine-translation label and authoritative English answer.
7. Open **Challenge My Innovation** and show evidence-linked patent, regulatory, ABS and scientific objections.
8. Open **Reports** and download the PDF. Show the risk matrix, adversarial review, evidence register, corpus/run identifiers, record hash and disclaimer.

## Claims to avoid

- Do not describe the registry as a complete freedom-to-operate or patent-clearance search.
- Do not claim public or unrestricted TKDL access.
- Do not describe traditional use as clinical efficacy.
- Do not describe machine translation as authoritative legal translation.
- Do not describe a user-uploaded document as verified merely because it was retrieved.
