"""The ship gate. Every check here must actually catch its failure.

A guardrail suite that only tests the happy path proves nothing: the whole
point is what gets rejected. So each test breaks exactly one thing on a deck
that otherwise passes, and asserts the reason comes back readable.
"""
import copy

import pytest

import guardrails


def check(deck, code="es", stage="survival", level="A1"):
    return guardrails.check_deck(deck, code, stage, level)


def test_a_good_deck_passes(good_deck):
    r = check(good_deck)
    assert r.ok, r.errors


# --------------------------------------------------------------- identity

def test_wrong_language_code_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    d["code"] = "fr"
    r = check(d)
    assert not r.ok
    assert any("asked for" in e for e in r.errors)


def test_wrong_stage_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    d["stage"] = "everyday"
    assert not check(d).ok


def test_wrong_level_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    d["level"] = "B2"
    assert not check(d).ok


def test_invented_stage_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    d["stage"] = "beginner"
    assert not check(d, stage="beginner").ok


def test_invented_level_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    d["level"] = "A0"
    assert not check(d, level="A0").ok


def test_invented_kind_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    d["kind"] = "phrases"
    assert not check(d).ok


# ------------------------------------------- the never-null rule (Lugha bug 18)

@pytest.mark.parametrize("field", ["name", "stage_name", "why"])
def test_empty_title_fields_are_caught(good_deck, field):
    d = copy.deepcopy(good_deck)
    d[field] = ""
    r = check(d)
    assert not r.ok
    assert any("null" in e or field in e for e in r.errors)


def test_missing_deck_field_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    del d["level"]
    r = check(d)
    assert not r.ok
    assert any("missing deck field" in e for e in r.errors)


# ------------------------------------------------- a generator cannot self-certify

def test_reviewed_true_is_rejected(good_deck):
    d = copy.deepcopy(good_deck)
    d["reviewed"] = True
    r = check(d)
    assert not r.ok
    assert any("reviewed" in e for e in r.errors)


def test_reviewed_missing_is_rejected(good_deck):
    d = copy.deepcopy(good_deck)
    del d["reviewed"]
    assert not check(d).ok


# ------------------------------------------------------------------ deck size

def test_too_few_cards_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    d["cards"] = d["cards"][:3]
    r = check(d)
    assert not r.ok
    assert any("finishable" in e for e in r.errors)


def test_too_many_cards_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    card = d["cards"][0]
    d["cards"] = [dict(card, front=f"palabra{i}") for i in range(40)]
    assert not check(d).ok


# ------------------------------------------------------------------- cards

def test_duplicate_front_is_caught(good_deck):
    # progress is keyed on "<deck id>::<front>", so duplicates share one record
    d = copy.deepcopy(good_deck)
    d["cards"][1]["front"] = d["cards"][0]["front"]
    r = check(d)
    assert not r.ok
    assert any("duplicate" in e for e in r.errors)


def test_english_front_is_caught_for_a_non_english_language(good_deck):
    d = copy.deepcopy(good_deck)
    d["cards"][0]["front"] = "Good morning"
    r = check(d)
    assert not r.ok
    assert any("English" in e for e in r.errors)


def test_front_equal_to_back_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    d["cards"][0]["front"] = d["cards"][0]["back"]
    assert not check(d).ok


def test_empty_pron_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    d["cards"][0]["pron"] = ""
    r = check(d)
    assert not r.ok
    assert any("pron" in e for e in r.errors)


def test_empty_back_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    d["cards"][0]["back"] = ""
    assert not check(d).ok


def test_missing_card_field_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    del d["cards"][0]["note"]
    r = check(d)
    assert not r.ok
    assert any("missing field note" in e for e in r.errors)


# --------------------------------------------------------------- citations

def test_missing_cites_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    d["cards"][0]["cites"] = []
    r = check(d)
    assert not r.ok
    assert any("cites" in e for e in r.errors)


def test_invented_citation_is_caught(good_deck):
    d = copy.deepcopy(good_deck)
    d["cards"][0]["cites"] = ["cefr-a9", "made-up-doc"]
    r = check(d)
    assert not r.ok
    assert any("unknown passage" in e for e in r.errors)


def test_real_citations_are_accepted(good_deck):
    d = copy.deepcopy(good_deck)
    d["cards"][0]["cites"] = ["cefr-a1", "lugha-ladder"]
    assert check(d).ok


# ------------------------------------------------------------------- script

def test_japanese_must_be_in_japanese_script():
    deck = {
        "name": "Japanese", "code": "ja", "stage": "survival",
        "stage_name": "Survival Japanese", "why": "Day one in Tokyo.",
        "level": "N5", "kind": "vocab", "reviewed": False, "source": "oso-cloud",
        "cards": [
            {"front": "konnichiwa", "pron": "konnichiwa", "back": "Hello",
             "recall": True, "neg": False, "note": "", "cites": ["jlpt-n5"]}
        ] * 1 + [
            {"front": f"word{i}", "pron": "x", "back": "y", "recall": True,
             "neg": False, "note": "", "cites": ["jlpt-n5"]}
            for i in range(11)
        ],
    }
    r = guardrails.check_deck(deck, "ja", "survival", "N5")
    assert not r.ok
    assert any("script" in e for e in r.errors)


def test_japanese_in_kana_passes_the_script_check():
    cards = [
        {"front": f, "pron": p, "back": b, "recall": True, "neg": False,
         "note": "", "cites": ["jlpt-n5"]}
        for f, p, b in [
            ("こんにちは", "konnichiwa", "Hello"),
            ("おはようございます", "ohayou gozaimasu", "Good morning"),
            ("こんばんは", "konbanwa", "Good evening"),
            ("ありがとう", "arigatou", "Thank you"),
            ("すみません", "sumimasen", "Excuse me"),
            ("おねがいします", "onegaishimasu", "Please"),
            ("わかりません", "wakarimasen", "I don't understand"),
            ("はい", "hai", "Yes"),
            ("いいえ", "iie", "No"),
            ("みず", "mizu", "Water"),
            ("トイレはどこですか", "toire wa doko desu ka", "Where is the toilet?"),
            ("たすけて", "tasukete", "Help"),
        ]
    ]
    deck = {
        "name": "Japanese", "code": "ja", "stage": "survival",
        "stage_name": "Survival Japanese", "why": "Day one in Tokyo.",
        "level": "N5", "kind": "vocab", "reviewed": False,
        "source": "oso-cloud", "cards": cards,
    }
    r = guardrails.check_deck(deck, "ja", "survival", "N5")
    assert r.ok, r.errors


def test_latin_script_languages_are_warned_not_trusted(good_deck):
    # the honest limit: we cannot prove Spanish is Spanish by codepoint
    r = check(good_deck)
    assert r.ok
    assert any("Latin alphabet" in w for w in r.warnings)


def test_a_language_with_no_script_rule_is_warned():
    cards = [
        {"front": f"wòd{i}", "pron": "x", "back": f"word {i}", "recall": True,
         "neg": False, "note": "", "cites": ["cefr-a1"]}
        for i in range(12)
    ]
    deck = {
        "name": "Wolof", "code": "wo", "stage": "survival",
        "stage_name": "Survival Wolof", "why": "First phrases.",
        "level": "A1", "kind": "vocab", "reviewed": False,
        "source": "oso-cloud", "cards": cards,
    }
    r = guardrails.check_deck(deck, "wo", "survival", "A1")
    assert r.ok, r.errors
    assert any("not verified" in w for w in r.warnings)


# ------------------------------------------------------------------- answers

def test_ungrounded_answer_must_admit_it():
    r = guardrails.check_answer(
        {"answer": "Probably about twenty.", "sources": [], "grounded": False})
    assert not r.ok


def test_ungrounded_answer_may_not_cite():
    r = guardrails.check_answer(
        {"answer": "I don't know.", "sources": ["cefr-a1"], "grounded": False})
    assert not r.ok


def test_proper_refusal_passes():
    r = guardrails.check_answer(
        {"answer": "I don't know.", "sources": [], "grounded": False})
    assert r.ok, r.errors


def test_grounded_answer_must_cite_something():
    r = guardrails.check_answer(
        {"answer": "Twelve to twenty-four cards.", "sources": [],
         "grounded": True})
    assert not r.ok


def test_grounded_answer_may_not_invent_a_source():
    r = guardrails.check_answer(
        {"answer": "Twelve to twenty-four.", "sources": ["cefr-z9"],
         "grounded": True})
    assert not r.ok
    assert any("unknown passage" in e for e in r.errors)


def test_empty_answer_is_caught():
    assert not guardrails.check_answer(
        {"answer": "", "sources": [], "grounded": True}).ok
