"""Configuración centralizada con pydantic-settings."""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Rutas absolutas ancladas al layout del repo, para no depender del CWD.
# Estructura: <repo>/backend/app/core/config.py
#   parents[2] == <repo>/backend
#   parents[3] == <repo>
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):

    openai_api_key: str = ""
    openai_base_url: Optional[str] = None
    llm_model: str = "gpt-4o-mini"

    embedding_model: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    docs_dir: str = "./docs"
    chroma_dir: str = "./data/chroma_db"
    collection_name: str = "soporte_docs"

    chunk_size: int = 400
    chunk_overlap: int = 80

    top_k: int = 4
    confidence_threshold: float = 0.65
    minimum_score: float = 0.60

    host: str = "0.0.0.0"
    port: int = 8000

    log_level: str = "INFO"
    log_json: bool = False

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("docs_dir", "chroma_dir", mode="after")
    @classmethod
    def _resolve_relative_to_backend(cls, v: str) -> str:
        """Rutas relativas se resuelven contra <repo>/backend, no contra el CWD."""
        p = Path(v)
        if not p.is_absolute():
            p = (_BACKEND_DIR / p).resolve()
        return str(p)


@lru_cache
def get_settings() -> Settings:
    return Settings()
