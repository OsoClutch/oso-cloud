---
id: method-spaced-repetition
title: Spaced repetition and the Mastery Gate
framework: method
topic: scheduling
source: Ebbinghaus (1885) on forgetting; Leitner (1972) box system; Wozniak's SM-2 (SuperMemo, 1987)
source_url: https://en.wikipedia.org/wiki/Spaced_repetition
note: Our own summary, plus how Lugha implements it.
---

# Spaced repetition, and why Lugha schedules the way it does

Memory for an isolated fact decays quickly and then more slowly. Reviewing just
before the point of forgetting resets the curve and flattens it, so each correct
recall buys a longer interval than the one before. That is the whole mechanism:
**recall, not re-reading**, and **spacing, not volume**.

## What this means for card design

- A card must be **recallable**, which means it has exactly one answer. A card
  with two acceptable answers teaches the scheduler nothing, because a miss
  cannot be interpreted.
- Effortful recall is the point. A card that can be answered from the prompt's
  shape, without knowing the language, is wasted.
- Cards should be small. If a card can be missed for two different reasons, it
  is two cards.

## How Lugha implements it

Lugha uses fixed intervals in days: `[0, 1, 3, 7, 14]`. A correct answer moves a
card up one step; a miss resets it to step 0, unlocks it, and makes it due the
same day.

On top of that sits the **Mastery Gate**: a card only locks when it is answered
correctly on a **different day** from the day it was first answered correctly.
Same-day repeats are short-term memory and do not count as learning. This is why
a learner cannot finish a stage in one sitting, by design.

A third verdict matters as much as right and wrong: **unclear**. When the
recogniser cannot make out what was said, Lugha records nothing at all. A
microphone failure must never be charged to the learner.

## Consequence for generated decks

- Deck size should be small enough to finish a round: **12–24 cards** is the
  useful range. A 60-card deck produces a queue nobody completes.
- Every card needs a stable front, because progress is keyed on
  `"<deck id>::<front>"`. Changing a card's front field silently creates a new
  card and abandons its history.
