FROM runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04
LABEL org.opencontainers.image.source="https://github.com/Yassine-64/docparse"
ENV PYTHONUNBUFFERED=1 TFID_MODEL=yifeihu/TF-ID-base HF_HOME=/app/.hf
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# bake the model weights so cold starts do not download them
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('yifeihu/TF-ID-base')"
COPY inference.py handler.py server.py .
CMD ["python", "-u", "handler.py"]
