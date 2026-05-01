"""Build the Phase 2 FAISS index from local regulatory source documents."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import faiss
import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.preprocessing.dataset import PHASE_ROOT
from src.rag.embedder import DocumentEmbedder
from src.rag.retriever import FAISSRetriever

DOCUMENTS_DIR = PHASE_ROOT / "rag" / "documents"
INDEX_PATH = PHASE_ROOT / "rag" / "faiss_index.bin"
METADATA_PATH = PHASE_ROOT / "rag" / "metadata.json"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


def _load_text_document(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_section_id(content: str) -> str:
    match = re.search(r"(Section\s+[0-9.]+\s*-\s*[^\n]+)", content)
    return match.group(1) if match else "General"


def _regulation_type_from_name(path: Path) -> str:
    lowered = path.stem.lower()
    if "basel" in lowered:
        return "Basel"
    if "sebi" in lowered or "nbfc" in lowered:
        return "NBFC Prudential"
    return "RBI"


def _chunk_text(text: str) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    words: list[str] = []
    chunks: list[str] = []

    for paragraph in paragraphs:
        paragraph_words = paragraph.split()
        if words and len(words) + len(paragraph_words) > CHUNK_SIZE:
            chunks.append(" ".join(words))
            words = words[-CHUNK_OVERLAP:]
        words.extend(paragraph_words)

    if words:
        chunks.append(" ".join(words))

    return chunks


def build_index() -> tuple[int, int]:
    """Chunk the regulatory docs, embed them, and persist FAISS artifacts."""
    metadata: list[dict[str, object]] = []
    chunk_texts: list[str] = []

    for document_path in sorted(DOCUMENTS_DIR.glob("*")):
        if document_path.suffix.lower() != ".txt":
            continue

        content = _load_text_document(document_path)
        for chunk_number, chunk in enumerate(_chunk_text(content)):
            metadata.append(
                {
                    "chunk_id": f"{document_path.stem}-{chunk_number}",
                    "content": chunk,
                    "source_name": document_path.stem.replace("_", " ").title(),
                    "section_id": _extract_section_id(chunk),
                    "regulation_type": _regulation_type_from_name(document_path),
                }
            )
            chunk_texts.append(chunk)

    embedder = DocumentEmbedder()
    embeddings = embedder.embed(chunk_texts)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.asarray(embeddings, dtype="float32"))

    faiss.write_index(index, str(INDEX_PATH))
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))
    return len(chunk_texts), index.ntotal


if __name__ == "__main__":
    total_chunks, index_size = build_index()
    retriever = FAISSRetriever()
    results = retriever.query("credit default probability assessment", top_k=3, min_score=0.2)
    assert len(results) >= 1, "Index built but retrieval returned 0 results"
    assert results[0]["score"] > 0.2, f"Low similarity score: {results[0]['score']}"
    print(f"FAISS index built: {total_chunks} chunks, index size={index_size}")
    print(f"Smoke test top hit: {results[0]['source_name']} ({results[0]['score']})")
