# Model workers

Two GPU services the core calls over HTTP. Both take `{"image_base64": "..."}` and run either as a
**RunPod serverless** worker (default `CMD`, `handler.py`) or as a plain FastAPI pod (`server.py`).

| worker | model | serverless output | pod endpoint | docparse env |
|---|---|---|---|---|
| `easyocr/` | EasyOCR en+fr | `{results:[{bbox:[[x,y]×4], text, confidence}], full_text}` | `POST /ocr` | `DOCPARSE_RUNPOD_OCR_ENDPOINT` / `DOCPARSE_OCR_WORKER_URL` |
| `tfid/` | yifeihu/TF-ID-base | `{detections:[{bbox:[x0,y0,x1,y1], label}]}` | `POST /detect` | `DOCPARSE_RUNPOD_LAYOUT_ENDPOINT` / `DOCPARSE_LAYOUT_WORKER_URL` |

Model weights are baked into the images, so serverless cold starts do not download anything.

## Images

Built by [`.github/workflows/workers.yml`](../.github/workflows/workers.yml) on every push that
touches `workers/**` and published to GHCR:

- `ghcr.io/yassine-64/docparse-easyocr:latest`
- `ghcr.io/yassine-64/docparse-tfid:latest`

(First publish: make both packages public in GitHub → Packages so RunPod can pull them without
credentials, or add a registry credential on RunPod.)

## RunPod serverless

```bash
RUNPOD_API_KEY=rpa_... uv run python workers/deploy_runpod.py   # creates templates + endpoints, prints .env lines
```

Then in `.env`:

```
DOCPARSE_RUNPOD_API_KEY=rpa_...
DOCPARSE_RUNPOD_OCR_ENDPOINT=<id>
DOCPARSE_RUNPOD_LAYOUT_ENDPOINT=<id>
```

`docparse` now routes scanned pages to EasyOCR on RunPod and `--layout` to TF-ID on RunPod. The
transport calls `/runsync` and falls back to polling `/status` for long jobs
(`infrastructure/http/transports.py`). Workers scale to zero when idle (`workersMin: 0`).

Manual alternative: RunPod console → Serverless → New Endpoint → container image above, 15–20 GB
container disk, any 16–24 GB GPU.

## Local GPU box / pod

```bash
docker run --gpus all -p 8001:8001 ghcr.io/yassine-64/docparse-easyocr uvicorn server:app --host 0.0.0.0 --port 8001
docker run --gpus all -p 8002:8002 ghcr.io/yassine-64/docparse-tfid    uvicorn server:app --host 0.0.0.0 --port 8002
```

and set `DOCPARSE_OCR_WORKER_URL=http://localhost:8001`, `DOCPARSE_LAYOUT_WORKER_URL=http://localhost:8002`.
Or `docker compose -f docker/docker-compose.yml --profile gpu up`.
