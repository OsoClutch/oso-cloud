"""Retrieval: the corpus parses, chunks carry citable ids, and the floor holds."""
from pathlib import Path

import rag

ROOT = Path(__file__).resolve().parent.parent


def test_corpus_loads_and_every_chunk_is_citable():
    chunks = rag.load_chunks()
    assert len(chunks) > 20
    for c in chunks:
        assert c.doc_id, f"{c.chunk_id} has no doc_id to cite"
        assert c.text.strip()
        assert c.chunk_id.startswith(c.doc_id)


def test_doc_ids_are_unique_per_file():
    chunks = rag.load_chunks()
    by_doc = {}
    for c in chunks:
        by_doc.setdefault(c.doc_id, set()).add(c.chunk_id)
    # every doc contributed at least one chunk, and ids do not collide
    assert len(by_doc) >= 16
    all_ids = [c.chunk_id for c in chunks]
    assert len(all_ids) == len(set(all_ids))


def test_frontmatter_is_parsed_including_lists():
    docs = {c.doc_id: c.meta for c in rag.load_chunks()}
    a1 = docs["cefr-a1"]
    assert a1["framework"] == "CEFR"
    assert a1["level"] == "A1"
    assert "survival" in a1["ladder_stages"]


def test_the_output_contract_doc_exists():
    # a generator with no copy of Lugha's deck format produces unusable decks
    assert "lugha-ladder" in {c.doc_id for c in rag.load_chunks()}


def test_offtopic_question_retrieves_nothing(index):
    assert rag.search("who won the game last night?", index=index) == []


def test_floor_is_enforced(index):
    q = "how many cards belong in a beginner survival deck"
    wide = rag.search(q, k=50, index=index, threshold=0.0)
    narrow = rag.search(q, k=50, index=index, threshold=0.4)
    impossible = rag.search(q, k=50, index=index, threshold=1.01)

    assert len(wide) > len(narrow) > 0
    assert impossible == []
    for h in narrow:
        assert h.score >= 0.4


def test_results_are_ordered_best_first(index):
    hits = rag.search("how big should a deck be", index=index, threshold=0.0)
    assert hits == sorted(hits, key=lambda h: h.score, reverse=True)


def test_index_round_trips(tmp_path):
    path = tmp_path / "idx.json"
    built = rag.build_index(index_path=path)
    loaded = rag.load_index(path)
    assert loaded["backend"] == built["backend"]
    assert len(loaded["chunks"]) == len(built["chunks"])


def test_missing_index_says_what_to_run(tmp_path):
    try:
        rag.load_index(tmp_path / "nope.json")
    except FileNotFoundError as e:
        assert "build_index" in str(e)
    else:
        raise AssertionError("a missing index must raise")
