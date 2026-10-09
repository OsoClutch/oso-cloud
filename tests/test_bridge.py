"""The bridge into Lugha: the safeguards, and the deck-id contract.

Lugha is a separate repo, so these tests restate its rules rather than import
them. Both rules are load-bearing and both are cited to the line they come from.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import guardrails
import to_lugha_deck as bridge


# --- Lugha engine.py:180, restated:
#     d["stage"] = STAGE_OF_DECK.get(did, d.get("stage") or "everyday")
#     with did = basename[:-5].split("_", 1)[-1]
STAGE_OF_DECK = {
    "kana": "sounds", "katakana": "sounds",
    "survival": "survival",
    "particles": "structure", "n5_gram_1": "structure", "n5_gram_2": "structure",
    "core": "everyday", "n5_vocab_1": "everyday", "n5_vocab_2": "everyday",
    "n5_kanji_1": "realtalk", "n5_kanji_2": "realtalk",
}


def lugha_stage_for(filename: str, file_stage: str) -> str:
    did = filename[:-5].split("_", 1)[-1]
    return STAGE_OF_DECK.get(did, file_stage or "everyday")


def test_every_generated_filename_lands_on_its_own_stage():
    """The reason no engine change is needed.

    A generated deck sets "stage" itself. For each of the five stages, the
    filename we choose must resolve to that same stage under Lugha's rule -
    either because the id is absent from STAGE_OF_DECK and the file's own field
    wins, or because the id happens to map to the same place.
    """
    for stage in guardrails.STAGES:
        name = f"es_{stage}.json"
        assert lugha_stage_for(name, stage) == stage, (
            f"{name} would load as {lugha_stage_for(name, stage)!r}, not {stage!r}")


def test_a_deck_with_no_stage_field_falls_back_to_everyday():
    # this is exactly why the fifteen legacy decks show the wrong stage
    assert lugha_stage_for("spanish.json", "") == "everyday"


def test_writing_a_new_file_is_allowed(tmp_path):
    ok, why = bridge.safe_to_write(tmp_path / "es_survival.json")
    assert ok and why == ""


def test_a_generated_file_may_be_overwritten(tmp_path):
    target = tmp_path / "es_survival.json"
    target.write_text(json.dumps({"source": "oso-cloud", "cards": []}))
    ok, _ = bridge.safe_to_write(target)
    assert ok


def test_a_handwritten_deck_is_never_overwritten(tmp_path):
    """The safeguard protecting Lugha's eleven Japanese decks."""
    target = tmp_path / "jp_survival.json"
    target.write_text(json.dumps(
        {"name": "Japanese", "code": "ja", "level": "N5", "cards": []}))
    ok, why = bridge.safe_to_write(target)
    assert not ok
    assert "hand-written" in why


def test_unreadable_json_is_never_overwritten(tmp_path):
    target = tmp_path / "es_survival.json"
    target.write_text("{ this is not json")
    ok, why = bridge.safe_to_write(target)
    assert not ok
    assert "refusing" in why


def test_known_words_only_reads_the_requested_language(tmp_path):
    (tmp_path / "es_survival.json").write_text(json.dumps({
        "code": "es", "cards": [{"front": "Hola"}, {"front": "Gracias"}]}))
    (tmp_path / "fr_survival.json").write_text(json.dumps({
        "code": "fr", "cards": [{"front": "Bonjour"}]}))

    words = bridge.known_words("es", tmp_path)
    assert set(words) == {"Hola", "Gracias"}


def test_known_words_survives_a_broken_deck_file(tmp_path):
    (tmp_path / "ok.json").write_text(json.dumps({
        "code": "es", "cards": [{"front": "Hola"}]}))
    (tmp_path / "broken.json").write_text("{ nope")
    assert bridge.known_words("es", tmp_path) == ["Hola"]


def test_known_words_on_a_missing_directory_is_empty(tmp_path):
    assert bridge.known_words("es", tmp_path / "nothing-here") == []
