import io
import json
import struct
import wave

from backend.config import DATA

DQ = json.loads((DATA / "demo_questions.json").read_text(encoding="utf-8"))
KEYS = {"transcript", "language", "fault_id", "confidence", "answer", "video", "audio", "handoff", "ticket_id",
        "sources", "providers_used", "timings", "request_id"}


def wav(seconds=1.0, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(struct.pack("<h", 0) * int(seconds * rate))
    return buf.getvalue()


def test_health_and_metrics(client):
    assert client.get("/health").json()["status"] == "ok"
    assert "requests" in client.get("/metrics").json()


def test_ask_response_shape_and_four_telugu_questions(client):
    for f in DQ["faults"]:
        r = client.post("/api/ask", data={"text": f["te"], "session_id": "shape"})
        assert r.status_code == 200
        body = r.json()
        assert KEYS <= set(body)
        assert body["fault_id"] == f["fault_id"] and body["language"] == "te" and not body["handoff"]
        assert body["video"]["url"].endswith(".mp4") and body["video"]["start_seconds"] > 0
        assert set(body["answer"]) == {"spoken_text", "steps", "safety_note", "video_chapter_to_watch"}
        assert 1 <= len(body["answer"]["steps"]) <= 6 and body["answer"]["safety_note"]
        assert body["audio"]["b64"] and {u["service"] for u in body["providers_used"]} >= {"llm", "tts"}


def test_voice_path_mock_stt(client):
    r = client.post("/api/ask", data={"language": "te", "session_id": "voice"}, files={"audio": ("a.wav", wav(), "audio/wav")}).json()
    assert r["transcript"] == DQ["faults"][0]["te"] and r["fault_id"] == "upper_thread_breaking"
    assert r["providers_used"][0]["service"] == "stt" and "stt" in r["timings"]


def test_mock_vision_filename_hints(client):
    for name, fault in [("needle.jpg", "needle_breaking"), ("bird_nest.png", "thread_nesting"),
                        ("outline_gap.jpg", "design_misalignment"), ("thread_snap.jpg", "upper_thread_breaking")]:
        r = client.post("/api/ask", data={"session_id": "v"}, files={"media": (name, b"\xff\xd8\xff fake", "image/jpeg")}).json()
        assert r["fault_id"] == fault, name


def test_unknown_media_becomes_handoff(client):
    r = client.post("/api/ask", data={"session_id": "u"}, files={"media": ("IMG_0001.jpg", b"\xff\xd8\xff", "image/jpeg")}).json()
    assert r["handoff"] and r["ticket_id"]


def test_media_and_text_disagree_handoff(client):
    r = client.post("/api/ask", data={"text": DQ["faults"][0]["en"], "session_id": "d"},
                    files={"media": ("needle.jpg", b"\xff\xd8\xff", "image/jpeg")}).json()
    assert r["handoff"]


def test_unrelated_question_handoff(client):
    r = client.post("/api/ask", data={"text": "What is the weather in Hyderabad today?", "session_id": "w"}).json()
    assert r["handoff"] and r["ticket_id"] and r["video"] is None


def test_human_request_handoff(client):
    r = client.post("/api/ask", data={"text": "I want to talk to a human please", "session_id": "h"}).json()
    assert r["handoff"] and "human" in r["fusion_reason"]


def test_two_not_solved_creates_ticket(client):
    client.post("/api/ask", data={"text": DQ["faults"][1]["en"], "session_id": "ns"})
    assert client.post("/api/feedback", json={"session_id": "ns", "solved": False}).json()["ticket_id"] is None
    tid = client.post("/api/feedback", json={"session_id": "ns", "solved": False}).json()["ticket_id"]
    assert tid
    tickets = client.get("/admin/tickets", headers={"X-Admin-Token": "test-token"}).json()
    t = next(t for t in tickets if t["id"] == tid)
    assert t["reason"] == "not solved twice" and t["fault_id"] == "needle_breaking" and len(t["summary"].splitlines()) <= 3


def test_upload_limits(client):
    big_audio = wav(seconds=31)
    assert client.post("/api/ask", data={"session_id": "l"}, files={"audio": ("a.wav", big_audio, "audio/wav")}).status_code == 413
    big_img = b"\xff" * (5 * 1024 * 1024 + 1)
    assert client.post("/api/ask", data={"session_id": "l"}, files={"media": ("x.jpg", big_img, "image/jpeg")}).status_code == 413
    assert client.post("/api/ask", data={"text": "a" * 1001, "session_id": "l"}).status_code == 413
    assert client.post("/api/ask", data={"session_id": "l"}, files={"media": ("x.pdf", b"%PDF", "application/pdf")}).status_code == 400
    assert client.post("/api/ask", data={"session_id": "l"}).status_code == 400


def test_admin_requires_token(client):
    assert client.get("/admin/tickets").status_code == 401
    assert client.get("/admin/usage", headers={"X-Admin-Token": "test-token"}).status_code == 200
    assert client.get("/admin/unanswered", headers={"X-Admin-Token": "test-token"}).status_code == 200
    assert "providers" in client.get("/admin/providers", headers={"X-Admin-Token": "test-token"}).json()


def test_products_and_demo_questions(client):
    assert len(client.get("/api/products").json()["products"]) == 10
    assert len(client.get("/api/demo-questions").json()["faults"]) == 4
