"""The HTTP surface, through the real app."""
import copy

from fastapi.testclient import TestClient

import bedrock
import main


def client(index):
    main._index = index          # the app loads lazily; hand it the mock index
    return TestClient(main.app)


def test_health_reports_mock_mode(index):
    body = client(index).get("/health").json()
    assert body["ok"] is True
    assert body["mock"] is True
    assert body["model"] is None          # no Bedrock model configured in tests


def test_deck_endpoint_accepts_a_good_deck(index):
    r = client(index).post("/deck", json={
        "language": "Spanish", "code": "es",
        "stage": "survival", "level": "A1"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "accepted", body["checks"]
    assert body["deck"]["reviewed"] is False
    assert 12 <= len(body["deck"]["cards"]) <= 24
    assert body["retrieved"], "a deck must say what it was built from"


def test_deck_endpoint_rejects_and_explains(index, monkeypatch):
    real = bedrock.generate_deck          # capture before patching, or recurse

    def bad(*a, **k):
        d = copy.deepcopy(real(*a, **k))
        d["cards"][0]["cites"] = ["not-a-real-passage"]
        return d

    monkeypatch.setattr(bedrock, "generate_deck", bad)
    body = client(index).post("/deck", json={
        "language": "Spanish", "code": "es",
        "stage": "survival", "level": "A1"}).json()

    assert body["status"] == "rejected"
    assert any("unknown passage" in e for e in body["checks"]["errors"])
    # the bad deck is still returned, so a human can see what was wrong with it
    assert body["deck"] is not None


def test_deck_endpoint_validates_its_inputs(index):
    c = client(index)
    assert c.post("/deck", json={"language": "Spanish", "code": "es",
                                 "stage": "survival"}).status_code == 422
    assert c.post("/deck", json={"language": "", "code": "es",
                                 "stage": "survival",
                                 "level": "A1"}).status_code == 422


def test_lesson_endpoint_answers_and_cites(index):
    body = client(index).post("/lesson", json={
        "question": "how big should a deck be?"}).json()
    assert body["grounded"] is True
    assert body["sources"]
    assert body["checks"]["ok"], body["checks"]


def test_lesson_endpoint_refuses_offtopic(index):
    body = client(index).post("/lesson", json={
        "question": "who won the game last night?"}).json()
    assert body["answer"].lower().startswith("i don't know")
    assert body["grounded"] is False
    assert body["sources"] == []
    assert body["retrieved"] == []
    assert body["checks"]["ok"], "refusing is correct behaviour, not a failure"


def test_lesson_endpoint_rejects_an_empty_question(index):
    assert client(index).post("/lesson",
                              json={"question": ""}).status_code == 422
