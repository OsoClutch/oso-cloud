"""What is allowed to ship.

Generation proposes; this disposes. Every check here is a thing that would
either break Lugha on the device or quietly teach somebody wrong, and each one
returns a reason a human can read rather than a boolean.

The honest limit is stated once, here, because it governs the whole project:
these checks prove a deck is *well-formed, in the right script, and traceable to
a cited passage*. They cannot prove the Greek is good Greek. Nothing in this
file should ever be read as a claim about teaching quality - that is what the
reviewed flag is for, and only a speaker of the language can flip it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from rag import load_chunks

STAGES = ("sounds", "survival", "structure", "everyday", "realtalk")
CEFR = ("A1", "A2", "B1", "B2", "C1", "C2")
JLPT = ("N5", "N4", "N3", "N2", "N1")

MIN_CARDS, MAX_CARDS = 12, 24

CARD_FIELDS = ("front", "pron", "back", "recall", "neg", "note", "cites")
DECK_FIELDS = ("name", "code", "stage", "stage_name", "why", "level", "kind",
               "reviewed", "source", "cards")

KINDS = ("vocab", "kana", "katakana", "grammar", "kanji")

# Languages whose script we can actually verify. A Latin-script language cannot
# be told from English by codepoint, so those get the weaker English check below
# and an explicit warning rather than a false sense of coverage.
SCRIPT_RANGES = {
    "ja": ("HIRAGANA", "KATAKANA", "CJK"),
    "zh": ("CJK",),
    "ko": ("HANGUL",),
    "ru": ("CYRILLIC",),
    "el": ("GREEK",),
    "ar": ("ARABIC",),
    "hi": ("DEVANAGARI",),
}

LATIN_SCRIPT = {"en", "es", "fr", "de", "nl", "pt", "it", "tr", "vi", "ht",
                "pcm", "sw"}

# Common English words, used only to catch a front field that is plainly English
# for a language that is not. Not a language identifier - a tripwire.
_ENGLISH = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "at",
    "is", "are", "was", "were", "be", "been", "it", "this", "that", "with",
    "as", "by", "from", "i", "you", "he", "she", "we", "they", "my", "your",
    "hello", "goodbye", "please", "thank", "thanks", "yes", "no", "excuse",
    "me", "sorry", "where", "what", "when", "how", "who", "why", "which",
    "do", "does", "did", "can", "could", "would", "should", "have", "has",
    "good", "morning", "evening", "night", "water", "help", "much", "cost",
    "speak", "english", "understand", "bathroom", "slower", "day",
}


def _scripts_in(text: str) -> set[str]:
    out = set()
    for ch in text:
        if not ch.isalpha():
            continue
        try:
            name = unicodedata.name(ch)
        except ValueError:
            continue
        for key in ("HIRAGANA", "KATAKANA", "CJK", "HANGUL", "CYRILLIC",
                    "GREEK", "ARABIC", "DEVANAGARI", "LATIN"):
            if name.startswith(key) or f" {key} " in f" {name} ":
                out.add(key)
    return out


def _looks_english(text: str) -> bool:
    words = re.findall(r"[A-Za-z']+", text.lower())
    if not words:
        return False
    return all(w in _ENGLISH for w in words)


@dataclass
class Report:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def summary(self) -> str:
        if self.ok and not self.warnings:
            return "PASS"
        if self.ok:
            return f"PASS with {len(self.warnings)} warning(s)"
        return f"FAIL ({len(self.errors)} error(s))"


def known_doc_ids(corpus_dir: Path | None = None) -> set[str]:
    return {c.doc_id for c in load_chunks(corpus_dir)}


def check_deck(deck: dict, want_code: str, want_stage: str, want_level: str,
               corpus_dir: Path | None = None) -> Report:
    """Everything that has to be true before a deck touches the device."""
    r = Report()

    if not isinstance(deck, dict):
        r.fail("deck is not a JSON object")
        return r

    for f in DECK_FIELDS:
        if f not in deck:
            r.fail(f"missing deck field: {f}")
    if not r.ok:
        return r

    # --- identity: it must be the deck that was asked for
    code = str(deck.get("code") or "").lower()
    if code != want_code.lower():
        r.fail(f"code is {code!r}, asked for {want_code!r}")
    if deck.get("stage") != want_stage:
        r.fail(f"stage is {deck.get('stage')!r}, asked for {want_stage!r}")
    if deck.get("level") != want_level:
        r.fail(f"level is {deck.get('level')!r}, asked for {want_level!r}")

    if deck.get("stage") not in STAGES:
        r.fail(f"stage {deck.get('stage')!r} is not one of {STAGES}")
    if deck.get("level") not in CEFR + JLPT:
        r.fail(f"level {deck.get('level')!r} is not a CEFR or JLPT band")
    if deck.get("kind") not in KINDS:
        r.fail(f"kind {deck.get('kind')!r} is not one of {KINDS}")

    # --- the never-null rule. 'Everyday · null' shipped to the real screen once.
    for f in ("name", "stage_name", "why"):
        if not str(deck.get(f) or "").strip():
            r.fail(f"{f} is empty - it would render as null on the device")

    # --- a generator may not vouch for its own output
    if deck.get("reviewed") is not False:
        r.fail("reviewed must be false on generated output")
    if deck.get("source") != "oso-cloud":
        r.warn(f"source is {deck.get('source')!r}, expected 'oso-cloud'")

    cards = deck.get("cards")
    if not isinstance(cards, list):
        r.fail("cards is not a list")
        return r

    if not (MIN_CARDS <= len(cards) <= MAX_CARDS):
        r.fail(f"{len(cards)} cards, needs {MIN_CARDS}-{MAX_CARDS} "
               "so a round is finishable in one sitting")

    known = known_doc_ids(corpus_dir)
    want_scripts = SCRIPT_RANGES.get(code)
    seen_fronts: set[str] = set()

    for i, c in enumerate(cards):
        where = f"card {i}"
        if not isinstance(c, dict):
            r.fail(f"{where} is not an object")
            continue

        for f in CARD_FIELDS:
            if f not in c:
                r.fail(f"{where}: missing field {f}")
        front = str(c.get("front") or "").strip()
        back = str(c.get("back") or "").strip()
        pron = str(c.get("pron") or "").strip()

        if not front:
            r.fail(f"{where}: front is empty")
            continue
        if not back:
            r.fail(f"{where} ({front!r}): back is empty")
        if not pron:
            r.fail(f"{where} ({front!r}): pron is empty - the grader compares "
                   "pronunciation, not spelling")

        # progress is keyed on "<deck id>::<front>", so a duplicate front is
        # two cards sharing one record: the second can never be learned
        key = front.casefold()
        if key in seen_fronts:
            r.fail(f"{where}: duplicate front {front!r} - progress is keyed on "
                   "front, so duplicates collide")
        seen_fronts.add(key)

        # --- script / language
        if want_scripts:
            found = _scripts_in(front)
            if not found & set(want_scripts):
                r.fail(f"{where} ({front!r}): not in {code} script "
                       f"(expected one of {want_scripts}, found {found or 'none'})")
        elif code in LATIN_SCRIPT and code != "en":
            if _looks_english(front):
                r.fail(f"{where}: front {front!r} is English - front must be "
                       f"the {code} the learner has to produce")

        if front.casefold() == back.casefold():
            r.fail(f"{where}: front and back are identical ({front!r})")

        # --- citations must point at passages that exist
        cites = c.get("cites")
        if not isinstance(cites, list) or not cites:
            r.fail(f"{where} ({front!r}): no cites")
        else:
            unknown = [x for x in cites if x not in known]
            if unknown:
                r.fail(f"{where} ({front!r}): cites unknown passage(s) "
                       f"{unknown} - invented citations are worse than none")

    if code in LATIN_SCRIPT and code != "en":
        r.warn(f"{code} uses the Latin alphabet, so the script check cannot "
               "prove the language - only that it is not plainly English. "
               "A speaker has to review this deck.")
    if code not in SCRIPT_RANGES and code not in LATIN_SCRIPT:
        r.warn(f"no script rule for {code!r}; script was not verified")

    return r


def check_answer(result: dict, corpus_dir: Path | None = None) -> Report:
    """A grounded answer must cite real passages, or admit it does not know."""
    r = Report()
    text = str(result.get("answer") or "").strip()

    if not text:
        r.fail("empty answer")
        return r

    if not result.get("grounded"):
        if not text.lower().startswith("i don't know"):
            r.fail("ungrounded answers must say \"I don't know.\"")
        if result.get("sources"):
            r.fail("an ungrounded answer must not cite sources")
        return r

    known = known_doc_ids(corpus_dir)
    sources = result.get("sources") or []
    if not sources:
        r.fail("grounded answer cites nothing")
    unknown = [s for s in sources if s not in known]
    if unknown:
        r.fail(f"cites unknown passage(s) {unknown}")
    return r
