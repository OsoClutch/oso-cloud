"""The promptfoo config is checked here so a broken eval suite fails CI.

promptfoo itself needs node and a live Bedrock-backed server, so it does not
run on every push. That makes it easy for this file to rot unnoticed - which is
exactly what these checks are for. They verify shape and coverage, never that
the model passes.
"""
from pathlib import Path

import yaml

import guardrails
import rag

CONFIG = Path(__file__).resolve().parent.parent / "promptfooconfig.yaml"


def config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def test_config_parses():
    cfg = config()
    assert cfg["description"]
    assert cfg["providers"]
    assert cfg["tests"]


def test_every_assertion_declares_a_type():
    for test in config()["tests"]:
        for assertion in test.get("assert", []):
            assert "type" in assertion, test["description"]


def test_every_test_has_a_description_and_a_question():
    for test in config()["tests"]:
        assert test.get("description")
        assert test["vars"]["question"].strip()


def test_the_three_behaviours_that_matter_are_all_covered():
    """Grounding, refusal and injection each need real coverage, not one token case."""
    metrics: dict[str, int] = {}
    for test in config()["tests"]:
        for assertion in test.get("assert", []):
            m = assertion.get("metric")
            if m:
                metrics[m] = metrics.get(m, 0) + 1

    assert metrics.get("cites-the-right-passage", 0) >= 2
    assert metrics.get("refuses-what-it-does-not-know", 0) >= 2
    assert metrics.get("resists-injection", 0) >= 3


def test_default_assertions_apply_to_every_test():
    # the two rules no test may opt out of: cite when grounded, pass own checks
    body = yaml.safe_dump(config()["defaultTest"])
    assert "sources" in body
    assert "checks" in body


def test_expected_passage_ids_actually_exist():
    """An eval asserting a citation that no corpus doc provides can never pass."""
    known = {c.doc_id for c in rag.load_chunks()}
    raw = CONFIG.read_text(encoding="utf-8")
    for quoted in ("method-spaced-repetition", "method-high-frequency-first",
                   "jlpt-n5"):
        assert quoted in raw, f"{quoted} is no longer asserted anywhere"
        assert quoted in known, f"{quoted} is asserted but not in the corpus"


def test_provider_points_at_the_lesson_endpoint():
    provider = config()["providers"][0]
    assert provider["config"]["url"].endswith("/lesson")
    assert provider["config"]["method"] == "POST"


def test_stage_and_level_vocabularies_have_not_drifted():
    # if these change, the corpus and the eval both need revisiting
    assert guardrails.STAGES == ("sounds", "survival", "structure",
                                 "everyday", "realtalk")
    assert guardrails.CEFR[0] == "A1" and guardrails.JLPT[0] == "N5"
