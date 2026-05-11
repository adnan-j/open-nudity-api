import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

DETECTIONS_NSFW = [
    {"class": "FEMALE_BREAST_EXPOSED", "score": 0.95, "box": [10, 20, 100, 150]},
    {"class": "FEMALE_GENITALIA_EXPOSED", "score": 0.82, "box": [30, 50, 80, 120]},
]
DETECTIONS_SAFE = [
    {"class": "FACE_FEMALE", "score": 0.98, "box": [10, 10, 50, 50]},
    {"class": "BELLY_EXPOSED", "score": 0.70, "box": [20, 60, 60, 100]},
]
DETECTIONS_FACE_AND_COVERED = [
    {"class": "FACE_MALE", "score": 0.97, "box": [5, 5, 45, 45]},
    {"class": "FEMALE_BREAST_COVERED", "score": 0.85, "box": [20, 50, 70, 100]},
]


# ── Health ──────────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ── NSFW Detection ───────────────────────────────────────────────────────────

@patch("app.routes.nsfw.detect_from_url", new_callable=AsyncMock, return_value=DETECTIONS_NSFW)
def test_nsfw_true(_):
    r = client.post("/v1/nsfw", json={"image_urls": ["https://example.com/image.jpg"]})
    assert r.status_code == 200
    assert r.json()[0]["is_nsfw"] is True


@patch("app.routes.nsfw.detect_from_url", new_callable=AsyncMock, return_value=DETECTIONS_SAFE)
def test_nsfw_false(_):
    r = client.post("/v1/nsfw", json={"image_urls": ["https://example.com/safe.jpg"]})
    assert r.status_code == 200
    assert r.json()[0]["is_nsfw"] is False


# ── Nudity Detection ─────────────────────────────────────────────────────────

@patch("app.routes.nudity.detect_from_url", new_callable=AsyncMock, return_value=DETECTIONS_NSFW)
def test_nudity_score_is_normalized(_):
    r = client.post("/v1/nudity", json={"image_urls": ["https://example.com/image.jpg"]})
    assert r.status_code == 200
    data = r.json()[0]
    assert data["is_nude"] is True
    assert 0.0 <= data["nudity_score"] <= 1.0  # must be normalized
    assert "FEMALE_BREAST_EXPOSED" in data["detected_regions"]


@patch("app.routes.nudity.detect_from_url", new_callable=AsyncMock, return_value=DETECTIONS_SAFE)
def test_nudity_safe_image(_):
    r = client.post("/v1/nudity", json={"image_urls": ["https://example.com/safe.jpg"]})
    assert r.status_code == 200
    data = r.json()[0]
    assert data["is_nude"] is False
    assert data["nudity_score"] == 0.0
    assert data["detected_regions"] is None


# ── Face Detection ───────────────────────────────────────────────────────────

@patch("app.routes.face.detect_from_url", new_callable=AsyncMock, return_value=DETECTIONS_FACE_AND_COVERED)
def test_face_detected_not_nsfw(_):
    r = client.post("/v1/face", json={"image_urls": ["https://example.com/face.jpg"]})
    assert r.status_code == 200
    data = r.json()[0]
    assert data["is_face"] is True
    assert data["is_nsfw"] is False


@patch("app.routes.face.detect_from_url", new_callable=AsyncMock, return_value=DETECTIONS_NSFW)
def test_face_nsfw(_):
    r = client.post("/v1/face", json={"image_urls": ["https://example.com/nsfw.jpg"]})
    assert r.status_code == 200
    data = r.json()[0]
    assert data["is_nsfw"] is True


# ── Raw Detections ───────────────────────────────────────────────────────────

@patch("app.routes.properties.detect_from_url", new_callable=AsyncMock, return_value=DETECTIONS_SAFE)
def test_raw_detections(_):
    r = client.post("/v1/detections", json={"image_urls": ["https://example.com/img.jpg"]})
    assert r.status_code == 200
    data = r.json()[0]
    assert "detections" in data
    assert len(data["detections"]) == len(DETECTIONS_SAFE)


# ── Validation ───────────────────────────────────────────────────────────────

def test_empty_urls():
    r = client.post("/v1/nsfw", json={"image_urls": []})
    assert r.status_code == 422


def test_invalid_url():
    r = client.post("/v1/nsfw", json={"image_urls": ["not-a-url"]})
    assert r.status_code == 422


def test_batch_multiple_urls():
    with patch("app.routes.nsfw.detect_from_url", new_callable=AsyncMock, return_value=DETECTIONS_SAFE):
        r = client.post("/v1/nsfw", json={
            "image_urls": [
                "https://example.com/a.jpg",
                "https://example.com/b.jpg",
                "https://example.com/c.jpg",
            ]
        })
    assert r.status_code == 200
    assert len(r.json()) == 3
