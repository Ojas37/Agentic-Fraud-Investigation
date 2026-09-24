"""
agent/config.py — Centralised configuration loaded from environment variables.
All other modules should import from here rather than calling os.getenv directly.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings  # pydantic v2

# Load .env from the project root (two levels up from this file)
_root = Path(__file__).resolve().parents[1]
load_dotenv(_root / ".env")


class Settings(BaseSettings):
    # ── TigerGraph ──────────────────────────────────────────────────────────
    tg_host: str = Field(..., env="TG_HOST")
    tg_username: str = Field("tigergraph", env="TG_USERNAME")
    tg_password: str = Field(..., env="TG_PASSWORD")
    tg_graph_name: str = Field("FraudGraph", env="TG_GRAPH_NAME")
    tg_secret: str = Field("", env="TG_SECRET")
    tg_token: str = Field("", env="TG_TOKEN")

    # ── LLM ─────────────────────────────────────────────────────────────────
    llm_provider: str = Field("groq", env="LLM_PROVIDER")
    llm_api_key: str = Field(..., env="LLM_API_KEY")
    llm_model: str = Field("openai/gpt-oss-120b", env="LLM_MODEL")

    # ── Embeddings ───────────────────────────────────────────────────────────
    embedding_model: str = Field("text-embedding-3-small", env="EMBEDDING_MODEL")
    embedding_provider: str = Field("openai", env="EMBEDDING_PROVIDER")
    embedding_api_key: str = Field("", env="EMBEDDING_API_KEY")

    # ── MCP ──────────────────────────────────────────────────────────────────
    mcp_server_url: str = Field("http://localhost:8000", env="MCP_SERVER_URL")
    mcp_log_level: str = Field("INFO", env="MCP_LOG_LEVEL")

    # ── Paths ─────────────────────────────────────────────────────────────────
    cases_output_dir: Path = Field(Path("cases/"), env="CASES_OUTPUT_DIR")
    data_raw_dir: Path = Field(Path("data/raw/"), env="DATA_RAW_DIR")
    data_processed_dir: Path = Field(Path("data/processed/"), env="DATA_PROCESSED_DIR")

    # ── Application ───────────────────────────────────────────────────────────
    log_level: str = Field("INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton. Call this everywhere."""
    return Settings()
