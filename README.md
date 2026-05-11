# Cloudants Vision API

Open-source image analysis API built on [NudeNet](https://github.com/notAI-tech/NudeNet). Self-host it in under 5 minutes with Docker.

> **Scope:** This API detects nudity and explicit content. It does **not** detect violence, drugs, or other non-nudity NSFW categories.

## APIs

| Endpoint | Description | Key fields returned |
|---|---|---|
| `POST /v1/nsfw` | Is this image explicit? | `is_nsfw: bool` |
| `POST /v1/nudity` | Nudity with confidence score | `is_nude: bool`, `nudity_score: float (0–1)`, `detected_regions: []` |
| `POST /v1/face` | Face presence + explicit check | `is_face: bool`, `is_nsfw: bool` |
| `POST /v1/detections` | Full NudeNet output | `detections: []` (class, score, bounding box per region) |

Each endpoint also has a `/upload` variant for direct file upload (no URL needed).

Interactive API docs auto-generated at **`http://localhost:8000/docs`** when running.

---

## Quickstart — Docker (recommended)

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO
cd YOUR_REPO

cp .env.example .env   # edit if needed

docker compose up --build
```

API is live at `http://localhost:8000`. The NudeNet model weights (~95MB) are baked into the image at build time, so the first request is fast.

---

## Quickstart — local Python

**Requires Python 3.9+**

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO
cd YOUR_REPO

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env

uvicorn app.main:app --reload
```

---

## Configuration

Copy `.env.example` to `.env`:

| Variable | Default | Description |
|---|---|---|
| `API_KEY` | *(empty)* | Require `X-API-Key` header on every request. Leave empty for open/local use. |
| `MAX_IMAGES_PER_REQUEST` | `10` | Max URLs allowed in a single request body |
| `WORKERS` | `4` | Thread pool size for model inference |
| `THRESHOLD_BREAST` | `0.30` | Min confidence to flag `FEMALE_BREAST_EXPOSED` |
| `THRESHOLD_GENITALIA` | `0.30` | Min confidence to flag female/male genitalia |
| `THRESHOLD_BUTTOCKS` | `0.40` | Min confidence to flag `BUTTOCKS_EXPOSED` |
| `THRESHOLD_ANUS` | `0.45` | Min confidence to flag `ANUS_EXPOSED` |

---

## Usage

### Check a URL

```bash
curl -X POST http://localhost:8000/v1/nsfw \
  -H "Content-Type: application/json" \
  -d '{"image_urls": ["https://example.com/photo.jpg"]}'
```

```json
[{"image_url": "https://example.com/photo.jpg", "is_nsfw": false, "error": null}]
```

### Upload a file directly

```bash
curl -X POST http://localhost:8000/v1/nsfw/upload \
  -F "file=@/path/to/image.jpg"
```

### Batch (multiple images in one call)

```bash
curl -X POST http://localhost:8000/v1/nudity \
  -H "Content-Type: application/json" \
  -d '{"image_urls": ["https://example.com/a.jpg", "https://example.com/b.jpg"]}'
```

```json
[
  {"image_url": "...a.jpg", "is_nude": false, "nudity_score": 0.0, "detected_regions": null},
  {"image_url": "...b.jpg", "is_nude": true,  "nudity_score": 0.87, "detected_regions": ["FEMALE_BREAST_EXPOSED"]}
]
```

### With API key

```bash
curl -X POST http://localhost:8000/v1/nsfw \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"image_urls": ["https://example.com/photo.jpg"]}'
```

---

## Response formats

### `/v1/nsfw`
```json
{"image_url": "...", "is_nsfw": true, "error": null}
```

### `/v1/nudity`
```json
{
  "image_url": "...",
  "is_nude": true,
  "nudity_score": 0.87,
  "detected_regions": ["FEMALE_BREAST_EXPOSED"],
  "error": null
}
```
`nudity_score` is the highest single detection confidence (0.0–1.0). It is **not** a sum — it is always a valid probability.

### `/v1/face`
```json
{"image_url": "...", "is_face": true, "is_nsfw": false, "error": null}
```

### `/v1/detections` (raw output)
```json
{
  "image_url": "...",
  "detections": [
    {"class": "FACE_FEMALE",            "score": 0.97, "box": [x, y, w, h]},
    {"class": "FEMALE_BREAST_COVERED",  "score": 0.85, "box": [x, y, w, h]}
  ],
  "error": null
}
```

### Error handling
Failed images return an `error` string instead of crashing the whole request. A batch of 5 images where 1 fails still returns 5 results.

---

## Detection thresholds

Thresholds control the minimum NudeNet confidence score required before an image is flagged. All thresholds are configurable via `.env` — no code changes needed.

| Class | Default | Env var |
|---|---|---|
| `FEMALE_BREAST_EXPOSED` | `0.30` | `THRESHOLD_BREAST` |
| `FEMALE_GENITALIA_EXPOSED` | `0.30` | `THRESHOLD_GENITALIA` |
| `MALE_GENITALIA_EXPOSED` | `0.30` | `THRESHOLD_GENITALIA` |
| `BUTTOCKS_EXPOSED` | `0.40` | `THRESHOLD_BUTTOCKS` |
| `ANUS_EXPOSED` | `0.45` | `THRESHOLD_ANUS` |

**Tuning guidance:**
- NudeNet scores on real-world photos typically fall in the `0.30–0.55` range — lower than you might expect
- Lower thresholds = more sensitive (catches more, higher false-positive risk)
- Higher thresholds = more strict (fewer false positives, may miss edge cases)
- Bikini/swimwear photos where everything is *covered* will never be flagged regardless of threshold — the model distinguishes `EXPOSED` vs `COVERED` classes

**Note:** This API flags *nudity* (exposed body parts), not *revealing clothing*. Swimwear, lingerie, and similar content where sensitive areas remain covered will return `is_nsfw: false` by design.

---

## All detectable classes

The underlying NudeNet model can return any of these in `/v1/detections`:

`FEMALE_BREAST_EXPOSED` · `FEMALE_BREAST_COVERED` · `FEMALE_GENITALIA_EXPOSED` · `FEMALE_GENITALIA_COVERED` · `MALE_GENITALIA_EXPOSED` · `BUTTOCKS_EXPOSED` · `BUTTOCKS_COVERED` · `ANUS_EXPOSED` · `ANUS_COVERED` · `FACE_FEMALE` · `FACE_MALE` · `FEET_EXPOSED` · `ARMPITS_EXPOSED` · `BELLY_EXPOSED` · `BELLY_COVERED`

---

## Running tests

```bash
pip install pytest httpx
pytest tests/ -v
```

---

## License

MIT
