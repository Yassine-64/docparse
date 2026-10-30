# Model workers

Two GPU-friendly FastAPI services the core talks to over HTTP. Both accept `{"image_base64": "..."}`.

| worker | endpoint | returns | env var in docparse |
|---|---|---|---|
| `easyocr/` | `POST /ocr` | `{results:[{bbox:[[x,y]×4], text, confidence}], full_text}` | `DOCPARSE_OCR_WORKER_URL` |
| `tfid/` | `POST /detect` | `{detections:[{bbox:[x0,y0,x1,y1], label}]}` | `DOCPARSE_LAYOUT_WORKER_URL` |

Run locally: `docker compose --profile gpu up`. On RunPod serverless, deploy the same images and set
`DOCPARSE_RUNPOD_API_KEY` + `DOCPARSE_RUNPOD_OCR_ENDPOINT` / `DOCPARSE_RUNPOD_LAYOUT_ENDPOINT` instead.
Without any worker, docparse falls back to Tesseract for OCR and skips layout detection.
