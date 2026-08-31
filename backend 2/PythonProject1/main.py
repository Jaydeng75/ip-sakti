import re
import warnings
import pypdf
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)

warnings.filterwarnings("ignore")


def extract_and_clean_pdf(pdf_path: str) -> str:
    reader = pypdf.PdfReader(pdf_path)
    full_text = []
    for page in reader.pages:
        text = page.extract_text()
        if not text:
            continue
        full_text.append(text)
    combined = "\n".join(full_text)


    schedule_idx = combined.upper().find("THE SCHEDULE")
    if schedule_idx != -1:
        combined = combined[:schedule_idx]

    lines = combined.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^Page\s+\d+", stripped, re.IGNORECASE) or re.match(r"^\d+\s*$", stripped):
            continue
        if "THE PATENTS ACT, 1970" in stripped.upper() and len(stripped) < 40:
            continue
        if re.search(r"\.{4,}", stripped) or stripped.startswith("SECTIONS"):
            continue
        if re.match(r"^\d+[A-Z]?\.\s*(Subs\.|Sub-section|Omitted|Ins\.|w\.e\.f|ibid)", stripped, re.IGNORECASE):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


ROMAN = {"i","ii","iii","iv","v","vi","vii","viii","ix","x","xi","xii"}

def chunk_by_statutory_sections(cleaned_text: str):
    sec_pattern = r'\n\s*(?=(\d+[A-Z]?)\.\s+)'
    raw_sections = re.split(sec_pattern, cleaned_text)
    structured_chunks = []

    if len(raw_sections) > 1:
        i = 1
        while i < len(raw_sections):
            sec_num = raw_sections[i].strip()
            sec_body = raw_sections[i + 1].strip() if (i + 1) < len(raw_sections) else ""

            # only split at clause markers that start a line
            clauses = re.split(r'\n\s*(?=\(([a-z]{1,2})\)\s+)', sec_body)

            if len(clauses) > 1:
                main_title = clauses[0].replace('\n', ' ').strip()
                structured_chunks.append({
                    "section_number": f"Section {sec_num}",
                    "text": f"Section {sec_num}. {main_title}\n{sec_body}"
                })

                c_idx = 1
                prev_letter = None
                while c_idx < len(clauses):
                    c_letter = clauses[c_idx].strip().lower()
                    c_content = clauses[c_idx + 1].strip() if (c_idx + 1) < len(clauses) else ""

                    if c_letter in ROMAN:
                        # nested illustration — fold into previous clause instead of
                        # treating it as a new top-level one
                        if structured_chunks and structured_chunks[-1]["section_number"] == f"Section {sec_num}({prev_letter})":
                            structured_chunks[-1]["text"] += f" ({c_letter}) {c_content}"
                        c_idx += 2
                        continue

                    target_label = f"Section {sec_num}({c_letter})"
                    combined_text = f"{target_label} [{main_title}]: ({c_letter}) {c_content}"
                    structured_chunks.append({"section_number": target_label, "text": combined_text})
                    prev_letter = c_letter
                    c_idx += 2
            else:
                structured_chunks.append({
                    "section_number": f"Section {sec_num}",
                    "text": f"Section {sec_num}. {sec_body}"
                })
            i += 2

    return structured_chunks


if __name__ == "__main__":
    pdf_path = "patentsact.pdf"
    collection_name = "indian_patents_act"

    print("Extracting and cleaning PDF...")
    cleaned_text = extract_and_clean_pdf(pdf_path)

    print("Chunking document with statutory hierarchy...")
    chunks = chunk_by_statutory_sections(cleaned_text)
    print(f"Successfully extracted {len(chunks)} statutory chunks!\n")

    print("Loading Sentence Transformer embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    client = QdrantClient(path="./qdrant_db")

    try:
        if client.collection_exists(collection_name):
            client.delete_collection(collection_name)

        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

        print("Embedding chunks and upserting to Qdrant...")
        points = []
        for idx, chunk in enumerate(chunks):
            vector = model.encode(chunk["text"]).tolist()
            points.append(
                PointStruct(
                    id=idx,
                    vector=vector,
                    payload={
                        "section_number": chunk["section_number"],
                        "text": chunk["text"]
                    }
                )
            )

        client.upsert(collection_name=collection_name, points=points)
        print("Successfully indexed all chunks into Qdrant!\n")

        queries = [
            "What inventions cannot be patented in India?",
            "Section 3d novelty standards and efficacy"
        ]

        for query_text in queries:
            print(f"==========================================")
            print(f"QUERY: '{query_text}'")
            print(f"==========================================")

            query_vector = model.encode(query_text).tolist()
            query_filter = None

            # Detect specific section reference patterns (e.g., "3d", "3(d)", "Section 3d")
            match = re.search(r'(?:section\s*)?(\d+)\s*\(?([a-z])\)?', query_text, re.IGNORECASE)
            if match and ("3" in query_text or "section" in query_text.lower()):
                sec_num = match.group(1)
                clause_let = match.group(2).lower()
                target_section = f"Section {sec_num}({clause_let})"

                query_filter = Filter(
                    should=[
                        FieldCondition(key="section_number", match=MatchValue(value=target_section)),
                        FieldCondition(key="section_number", match=MatchValue(value=f"Section {sec_num}"))
                    ]
                )

            search_response = client.query_points(
                collection_name=collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=3
            )

            for rank, result in enumerate(search_response.points, 1):
                print(f"\n[Result #{rank}] Score: {result.score:.4f}")
                print(f"Section: {result.payload['section_number']}")
                print(f"Content:\n{result.payload['text'][:300]}...\n")

    finally:
        client.close()