FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04
LABEL org.opencontainers.image.source="https://github.com/Yassine-64/docparse"
ENV PYTHONUNBUFFERED=1 OCR_LANGS=en,fr
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# bake the detector + recognizer weights so cold starts do not download them
RUN python -c "import easyocr; easyocr.Reader(['en','fr'], gpu=False)"
COPY inference.py handler.py server.py .
# RunPod serverless (default). For a pod: docker run ... uvicorn server:app --host 0.0.0.0 --port 8001
CMD ["python", "-u", "handler.py"]
