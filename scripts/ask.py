#!/usr/bin/env python3
"""Ask the corpus one question and show what was retrieved, with scores.

  python scripts/ask.py "what should a Spanish beginner learn first?"

Run it once with MOCK_BEDROCK=1 and once without, on the same question. The
scores and the documents that come back are the whole argument for embeddings.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bedrock  # noqa: E402
import guardrails  # noqa: E402
import rag  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    question = " ".join(argv[1:])

    index = rag.load_index()
    hits = rag.search(question, index=index)

    print(f"backend   : {index['backend']}")
    print(f"floor     : {rag.min_score()}")
    print(f"question  : {question}\n")

    if not hits:
        print("retrieved : nothing above the floor")
    else:
        print("retrieved :")
        for h in hits:
            print(f"   {h.score:>7.4f}  {h.doc_id:<30} {h.heading}")

    result = bedrock.answer(question, hits)
    report = guardrails.check_answer(result)

    print(f"\nanswer    : {result['answer']}")
    print(f"sources   : {', '.join(result['sources']) or '-'}")
    print(f"grounded  : {result['grounded']}")
    print(f"checks    : {report.summary()}")
    for e in report.errors:
        print(f"   ERROR {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
