---
id: jlpt-n5
title: JLPT N5 — the entry level
framework: JLPT
level: N5
language: ja
cefr_approx: A1
ladder_stages: [sounds, survival, structure]
source: Japan Foundation / JEES, Japanese-Language Proficiency Test level summaries
source_url: https://www.jlpt.jp/e/about/levelsummary.html
note: Our own summary of the N5 band. No official descriptor text is reproduced.
---

# JLPT N5

N5 is the first of the five JLPT levels. It assumes a learner who can read and
understand basic Japanese written in hiragana, katakana, and a small set of
basic kanji, and who can follow short, slow conversations about everyday
situations.

## Scope

- **Scripts:** hiragana and katakana in full. These come before everything else
  — a learner who cannot read the syllabary cannot study anything that uses it.
- **Kanji:** roughly 100 characters, the concrete everyday ones — numbers, days,
  people, directions, big and small, go and come.
- **Vocabulary:** roughly 800 words.
- **Grammar:** the polite present and past (です / ます forms); the core
  particles は, が, を, に, で, と, も, の; adjective types and their negatives;
  これ / それ / あれ; basic counters; simple questions with か.
- **Listening:** short classroom and daily-life exchanges spoken slowly.

## How N5 maps onto Lugha's ladder

| Lugha stage | N5 content |
|---|---|
| `sounds` | hiragana, then katakana — one card per character, answered out loud |
| `survival` | greetings, please and thank you, excuse me, numbers, asking where something is |
| `structure` | the core particles, です/ます, question formation |
| `everyday` | the N5 vocabulary sets and the concrete kanji |
| `realtalk` | the remaining kanji and faster everyday phrasing |

This mapping is the one Lugha's existing eleven Japanese decks already use, and
it is the worked example a generator should imitate for other languages.

## Turning N5 into cards

- Syllabary cards are **one character, one sound**. The answer is spoken, so the
  card's value is the sound, not the shape.
- Keep the spoken answer short. Whisper hears single syllables poorly, so a card
  whose answer is one mora is already at the limit of what a recogniser can
  grade.
- Give every vocabulary card a pronunciation field in romaji as well as the
  native script, because the grader compares in romaji space.
