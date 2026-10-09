"""Retrieval over the language-teaching corpus.

Two backends, one interface:

  * real    - Amazon Titan Text Embeddings V2, cosine similarity
  * mock    - keyword overlap, no AWS account needed (MOCK_BEDROCK=1)

The mock backend is not a stub for the tests' benefit alone. It is the
comparison that shows what embeddings buy you: ask "how far will you tow my
car" of a keyword matcher and it returns whatever shares the most words. Ask
the same of Titan and it returns the document that *means* the same thing.
Keeping both around makes that difference measurable instead of assumed.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPUS_DIR = Path(os.environ.get("CORPUS_DIR", ROOT / "corpus"))
INDEX_PATH = Path(os.environ.get("INDEX_PATH", ROOT / "index.json"))

EMBED_MODEL_ID = os.environ.get("EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Two backends, two scales. Cosine similarity on normalised Titan vectors sits
# in [-1, 1]; keyword overlap is a ratio in [0, 1] that behaves nothing like it.
# One shared threshold would be wrong for at least one of them, so they get
# their own, and the tuning done on one does not silently apply to the other.
MIN_SCORE_REAL = float(os.environ.get("MIN_SCORE", "0.35"))
MIN_SCORE_MOCK = float(os.environ.get("MIN_SCORE_MOCK", "0.08"))

TOP_K = int(os.environ.get("TOP_K", "4"))


def mock_mode() -> bool:
    return os.environ.get("MOCK_BEDROCK", "") not in ("", "0", "false", "False")


def min_score() -> float:
    return MIN_SCORE_MOCK if mock_mode() else MIN_SCORE_REAL


# --------------------------------------------------------------- corpus loading

@dataclass
class Chunk:
    chunk_id: str      # "cefr-a1#2"
    doc_id: str        # "cefr-a1"      <- what a generated card cites
    title: str
    heading: str
    text: str
    meta: dict

    def citation(self) -> str:
        return self.doc_id


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Read the --- block at the top of a corpus file.

    Deliberately not a YAML parser: the corpus only uses scalars and simple
    inline lists, and adding a YAML dependency to read our own files we also
    wrote would be paying for generality nobody asked for.
    """
    if not raw.startswith("---"):
        return {}, raw
    end = raw.find("\n---", 3)
    if end == -1:
        return {}, raw
    block, body = raw[3:end], raw[end + 4:]
    meta: dict = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        else:
            meta[key] = value
    return meta, body


def load_chunks(corpus_dir: Path | None = None) -> list[Chunk]:
    """One chunk per '##' section, so a citation points at a real passage."""
    corpus_dir = Path(corpus_dir or CORPUS_DIR)
    chunks: list[Chunk] = []
    for path in sorted(corpus_dir.glob("*.md")):
        meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
        doc_id = meta.get("id") or path.stem.replace("_", "-")
        title = meta.get("title") or path.stem

        # split on level-2 headings; whatever precedes the first one is the lede
        parts = re.split(r"^##\s+(.+)$", body, flags=re.MULTILINE)
        sections: list[tuple[str, str]] = []
        lede = parts[0].strip()
        lede = re.sub(r"^#\s+.+$", "", lede, flags=re.MULTILINE).strip()
        if lede:
            sections.append(("", lede))
        for i in range(1, len(parts) - 1, 2):
            sections.append((parts[i].strip(), parts[i + 1].strip()))

        for n, (heading, text) in enumerate(sections):
            if not text:
                continue
            chunks.append(Chunk(
                chunk_id=f"{doc_id}#{n}",
                doc_id=doc_id,
                title=title,
                heading=heading,
                text=f"{title}\n{heading}\n{text}".strip(),
                meta=meta,
            ))
    return chunks


# ------------------------------------------------------------------- embeddings

def _bedrock_client():
    import boto3  # imported lazily so mock mode needs no AWS packages configured
    return boto3.client("bedrock-runtime", region_name=AWS_REGION)


def embed(texts: list[str]) -> list[list[float]]:
    """Titan Text Embeddings V2. One call per text - Titan takes a single input."""
    client = _bedrock_client()
    out: list[list[float]] = []
    for text in texts:
        response = client.invoke_model(
            modelId=EMBED_MODEL_ID,
            body=json.dumps({"inputText": text, "normalize": True}),
        )
        out.append(json.loads(response["body"].read())["embedding"])
    return out


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return 0.0 if na == 0 or nb == 0 else dot / (na * nb)


# ---------------------------------------------------------------- mock scoring

_STOP = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "at",
    "is", "are", "was", "be", "it", "that", "this", "with", "as", "by", "from",
    "what", "which", "who", "how", "do", "does", "can", "should", "i", "you",
}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower())
            if len(w) > 2 and w not in _STOP}


def _overlap(query: str, text: str) -> float:
    q, t = _tokens(query), _tokens(text)
    return 0.0 if not q or not t else len(q & t) / len(q)


# ----------------------------------------------------------------------- index

def build_index(corpus_dir: Path | None = None, index_path: Path | None = None) -> dict:
    """Embed the corpus and write it to disk.

    In mock mode no vectors are stored - scoring is done against the text at
    query time - so the same index file works for both backends.
    """
    index_path = Path(index_path or INDEX_PATH)
    chunks = load_chunks(corpus_dir)
    if not chunks:
        raise RuntimeError(f"no corpus documents found in {corpus_dir or CORPUS_DIR}")

    vectors: list[list[float]] | None = None
    if not mock_mode():
        vectors = embed([c.text for c in chunks])

    index = {
        "backend": "mock" if mock_mode() else EMBED_MODEL_ID,
        "chunks": [asdict(c) for c in chunks],
        "vectors": vectors,
    }
    index_path.write_text(json.dumps(index), encoding="utf-8")
    return index


def load_index(index_path: Path | None = None) -> dict:
    index_path = Path(index_path or INDEX_PATH)
    if not index_path.exists():
        raise FileNotFoundError(
            f"no index at {index_path}. Run: python scripts/build_index.py"
        )
    return json.loads(index_path.read_text(encoding="utf-8"))


@dataclass
class Hit:
    chunk_id: str
    doc_id: str
    title: str
    heading: str
    text: str
    score: float


def search(query: str, k: int = TOP_K, index: dict | None = None,
           threshold: float | None = None) -> list[Hit]:
    """Top k chunks above the floor, best first. Empty list is a real answer."""
    index = index or load_index()
    chunks = [Chunk(**c) for c in index["chunks"]]
    floor = min_score() if threshold is None else threshold

    if index.get("vectors"):
        query_vec = embed([query])[0]
        scored = [(_cosine(query_vec, v), c)
                  for v, c in zip(index["vectors"], chunks)]
    else:
        # mock, or an index built in mock mode and queried the same way
        scored = [(_overlap(query, c.text), c) for c in chunks]

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [Hit(c.chunk_id, c.doc_id, c.title, c.heading, c.text, round(s, 4))
            for s, c in scored[:k] if s >= floor]
