from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from docparse.application.dto import OcrMode
from docparse.application.quality import QualityThresholds


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DOCPARSE_", env_file=".env", env_nested_delimiter="__", extra="ignore"
    )

    ocr_mode: OcrMode = OcrMode.AUTO
    min_chars_per_page: int = 50
    quality: QualityThresholds = Field(default_factory=QualityThresholds)

    tesseract_langs: str = "eng+fra"
    tesseract_cmd: str | None = None

    mistral_api_key: str | None = None
    mistral_ocr_model: str = "mistral-ocr-latest"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5-5"

    ocr_worker_url: str | None = Field(default=None, description="EasyOCR worker base URL")
    layout_worker_url: str | None = Field(default=None, description="TF-ID worker base URL")
    runpod_api_key: str | None = None
    runpod_ocr_endpoint: str | None = None
    runpod_layout_endpoint: str | None = None

    api_key: str | None = Field(default=None, description="Bearer token for the HTTP API when set")
    max_upload_mb: int = 50
    log_level: str = "INFO"
