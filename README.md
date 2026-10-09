# Oso Cloud

A curriculum engine for [Lugha](#what-lugha-is). It builds flashcard decks for
any language from language-teaching reference material — CEFR, JLPT, and
method — using retrieval-augmented generation on Amazon Bedrock, and every card
it produces cites the passage it came from.

Decks it generates are plain JSON files that drop straight into Lugha, which
runs entirely offline on a Raspberry Pi. **Bedrock is never in Lugha's
runtime.** It runs here, at authoring time; the only thing that crosses over is
a file.

---

## The problem

Lugha offers 16 languages. Measured on the actual device:

| Language | Decks | Level tag | Cards |
|---|---|---|---|
| Japanese | 11, across all five ladder stages | `N5` | 267 |
| Spanish, French, German, Dutch, Greek, Haitian Creole, Nigerian Pidgin, … | **1 each** | **none** | **18 each** |

So it teaches one language and gestures at fifteen others. Writing 11 decks ×
15 languages by hand was never going to happen, and a deck with no level and no
stage can't be placed on a learning ladder at all.

## The approach

Retrieval over a corpus of **how languages are actually taught**, not over
vocabulary lists:

- **Level frameworks** — CEFR A1–C2, JLPT N5–N1: what a learner at each band can
  do, how much vocabulary and grammar that implies, and which of Lugha's five
  stages the band touches.
- **Teaching method** — spaced repetition and why the Mastery Gate works the way
  it does, comprehensible input and i+1, high-frequency-first selection and why
  survival vocabulary is chosen differently, minimal pairs and the sounds stage.
- **The output contract** — Lugha's five-stage ladder and exact deck schema, so
  a generated deck loads on the device instead of needing a code change.

Every corpus document is **our own summary with a citation and a link**. No CEFR,
JLPT or ACTFL descriptor text is reproduced — that text is copyrighted and this
repository is public.

## Pipeline

```
question / deck request
        │
        ▼
   rag.py ──── Titan Text Embeddings V2 ──── corpus/*.md  (16 docs, 55 chunks)
        │      cosine similarity, MIN_SCORE floor
        │      nothing above the floor → "I don't know"
        ▼
 bedrock.py ── Claude Haiku, Bedrock Converse API
        │      grounded only in retrieved passages
        ▼
guardrails.py  schema · script · citations · duplicates · size · reviewed=false
        │      a deck that fails is never written
        ▼
scripts/to_lugha_deck.py ──→ <code>_<stage>.json ──→ Lugha, offline
```

## Run it without an AWS account

Mock mode swaps embeddings for keyword overlap and generation for a fixed sample
deck. The whole pipeline, the API and all 72 tests run offline.

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
export MOCK_BEDROCK=1
python scripts/build_index.py
python -m pytest -q
python scripts/to_lugha_deck.py --lang es --name Spanish --stage survival --level A1
```

## Run it against Bedrock

```bash
cp .env.example .env     # then paste your model id in — see the comment there
unset MOCK_BEDROCK
python scripts/build_index.py
python scripts/ask.py "how many cards should one deck have, and why?"
uvicorn main:app --port 8000
```

### Why mock mode is kept around

It isn't only a test fixture. Ask both backends the same question and the
difference between keyword matching and embeddings stops being a claim:

```
$ MOCK_BEDROCK=1 python scripts/ask.py "how big should a deck be?"
   0.5000  jlpt-n1                      Turning N1 into cards
   0.5000  jlpt-n3                      Turning N3 into cards
   0.5000  jlpt-n5                      Scope
   0.5000  lugha-ladder
```

Two things are wrong here, and both are the point. The passage that actually
answers the question — "12–24 cards per deck", in `method-spaced-repetition` —
is not in the list at all, because it never uses the word "big". And every
result is tied at exactly `0.5000`: the query has two content words, each
document matched one of them, so keyword overlap cannot rank them and the order
is arbitrary. Embeddings score on meaning, which both ranks and discriminates.
Run it both ways and keep the screenshots.

## Tests

```bash
MOCK_BEDROCK=1 python -m pytest -q      # 72 tests, no AWS, no network
```

| Suite | What it covers |
|---|---|
| `test_rag.py` | Corpus parses, every chunk is citable, the score floor holds, off-topic retrieves nothing |
| `test_guardrails.py` | 34 tests, each breaking exactly one thing on a deck that otherwise passes |
| `test_api.py` | Both endpoints, including that a rejected deck is returned *with* its reasons |
| `test_bridge.py` | The deck-id contract with Lugha, and the two write safeguards |
| `test_injection.py` | The half of injection testing that runs offline |
| `test_evalconfig.py` | The promptfoo suite is well-formed and still covers all three behaviours |

Guardrails are tested by what they **reject**: wrong language code, invented
citation, duplicate card front, English where the target language belongs,
romaji where kana belongs, an empty title, a deck that marks itself reviewed.

### What the tests do not prove

In mock mode Claude is never called, so nothing here says anything about model
output. That is `promptfooconfig.yaml` — 12 cases covering grounding, refusal
and injection resistance — which needs a live Bedrock-backed server and runs
from the **Bedrock Eval** workflow, manually, because it costs money.

Pass rate: _not yet measured — the eval has not been run against live Bedrock._

## Honest limits

- **A passing eval does not mean a good deck.** It means well-formed, in the
  right script, and traceable to a cited passage. It cannot judge whether the
  Greek is good Greek.
- Every generated deck therefore ships `"reviewed": false`. Only a speaker of
  the language can flip that, and the generator is explicitly told it is not
  qualified to.
- **The script check can't verify Latin-script languages.** Spanish and English
  share codepoints, so for those the check only catches output that is plainly
  English, and the deck gets a warning saying so.
- Non-English card content in this repo was produced by a model and reviewed by
  nobody. Treat it that way.

## What Lugha is

An offline spoken-language tutor on a Raspberry Pi 5 with a 7" touchscreen:
flashcards answered out loud, graded by local Whisper, scheduled by spaced
repetition with a Mastery Gate, plus free conversation through a local LLM. No
paid API and no internet in the normal path, so that a kid with an $80 Pi and no
money gets the whole tutor. That constraint is why Bedrock lives in this
repository and not that one.

## Layout

```
corpus/           16 reference documents, each with a citable id
rag.py            retrieval: Titan embeddings, or keyword overlap in mock mode
bedrock.py        generation: Claude via the Bedrock Converse API
guardrails.py     what is allowed to ship
main.py           FastAPI: POST /lesson, POST /deck, GET /health
scripts/          build_index.py · ask.py · to_lugha_deck.py
tests/            72 tests, offline
promptfooconfig.yaml   the live-model eval suite
```
