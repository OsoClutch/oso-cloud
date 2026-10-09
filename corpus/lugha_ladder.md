---
id: lugha-ladder
title: Lugha's five-stage ladder and deck format
framework: lugha
topic: output-contract
source: Lugha CLAUDE.md sections 6.2 and 10; engine.py STAGES and load_decks
note: The output contract. A generated deck that does not match this does not load.
---

# Lugha's ladder, and the exact deck format

Every language in Lugha climbs the **same five stages**. Only the content
changes. The stage ids are fixed strings:

| Stage id | Label | What it is for |
|---|---|---|
| `sounds` | SOUNDS | The alphabet of the mouth: the script, or the sounds that differ from the learner's own language. |
| `survival` | SURVIVAL | Enough to not be stuck. Chosen by situation, not corpus frequency. |
| `structure` | STRUCTURE | How sentences hold together: particles, word order, the patterns with slots. |
| `everyday` | EVERYDAY | The words of an ordinary day, chosen by frequency, concrete before abstract. |
| `realtalk` | REAL TALK | Speed, contraction, slang, and being understood by someone not slowing down. |

A CEFR or JLPT band is **not** a stage. The band is the difficulty; the stage is
the kind of content. A1 Spanish has all five stages; so does A2. Generate one
deck per (language, stage, band).

## The deck file

One JSON object per file, named `<code>_<stage>.json` — for example
`es_survival.json`. The filename matters: Lugha derives the deck id from the
part after the first underscore, and progress is keyed on
`"<deck id>::<front>"`, so a filename change orphans a learner's history.

```json
{
  "name": "Spanish",
  "code": "es",
  "stage": "survival",
  "stage_name": "Survival Spanish",
  "why": "The phrases you will use in your first hour off the plane.",
  "level": "A1",
  "kind": "vocab",
  "reviewed": false,
  "source": "oso-cloud",
  "cards": [
    {
      "front": "¿Dónde está el baño?",
      "pron": "DON-deh es-TAH el BAH-nyo",
      "back": "Where is the bathroom?",
      "recall": true,
      "neg": false,
      "note": "The single most useful question in any language.",
      "cites": ["cefr-a1", "method-high-frequency-first"]
    }
  ]
}
```

### Field rules

- `code` — two-letter language code. Must match the language requested.
- `stage` — one of the five ids above, written explicitly. Lugha falls back to
  `everyday` when it is missing, which is why the fifteen untagged legacy decks
  show the wrong stage.
- `stage_name` — the human title shown on screen. **Never null and never
  empty**: a missing title once rendered as "Everyday · null" on the device.
- `level` — the band: `A1`–`C2`, or `N5`–`N1` for Japanese.
- `kind` — `vocab`, `kana`, `katakana`, `grammar`, or `kanji`.
- `why` — one plain sentence a learner would accept as a reason to study this.
- `reviewed` — `false` on anything generated and not yet checked by a human who
  speaks the language. Never set this to `true` from a generator.
- `cites` — the corpus descriptor ids this card was built from. Required.

### Card rules

- `front` — the prompt, **in the target language and its own script**. No
  English. This is what the learner is asked to produce.
- `pron` — pronunciation guide. Required even for Latin-script languages,
  because the speech grader compares pronunciation rather than spelling.
- `back` — the English meaning.
- `recall` — `true` when the learner should say the target language aloud.
- `neg` — `false` unless the card deliberately teaches a negative form.
- `note` — a short usage note, or an empty string. Not a grammar lecture.

### Size

12–24 cards per deck. A round has to be finishable in one sitting, or the
Mastery Gate never closes.

## Worked example

Lugha's own `jp_survival.json` is the model: twenty cards, `stage: "survival"`,
`level: "N5"`, each card a whole phrase with romaji in `pron`, and notes that
say something useful ("Daytime only", "Polite form. Drop gozaimasu with
friends"). Imitate its judgement, not just its shape.
