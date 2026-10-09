#!/usr/bin/env python3
"""Build the retrieval index over corpus/.

  MOCK_BEDROCK=1 python scripts/build_index.py   # no AWS, no embeddings
  python scripts/build_index.py                  # Titan embeddings
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rag  # noqa: E402


def main() -> int:
    index = rag.build_index()
    chunks = index["chunks"]
    docs = sorted({c["doc_id"] for c in chunks})
    print(f"backend : {index['backend']}")
    print(f"docs    : {len(docs)}")
    print(f"chunks  : {len(chunks)}")
    print(f"vectors : {'none (mock mode)' if not index['vectors'] else len(index['vectors'])}")
    print(f"written : {rag.INDEX_PATH}")
    if not index["vectors"]:
        print("\nMock index. Scoring is keyword overlap, not meaning.")
        print("Unset MOCK_BEDROCK and re-run once Bedrock access is live.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
