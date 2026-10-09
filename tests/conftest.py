import os
import sys
from pathlib import Path

# Mock mode before anything imports rag/bedrock, so no test can reach AWS.
os.environ["MOCK_BEDROCK"] = "1"
os.environ.pop("BEDROCK_MODEL_ID", None)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

import bedrock  # noqa: E402
import rag  # noqa: E402


@pytest.fixture(scope="session")
def index():
    """One mock index over the real corpus, shared by the suite."""
    return rag.build_index(index_path=ROOT / "index.json")


@pytest.fixture
def good_deck(index):
    """A deck that should pass every check - the baseline for the bad ones."""
    hits = rag.search("survival phrases for a beginner", index=index)
    return bedrock.generate_deck("Spanish", "es", "survival", "A1", hits)
