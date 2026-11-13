import os
from pathlib import Path

# Prefer local cached models to eliminate remote HF hub network delays
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Project Root Directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Project Root
    project_root: Path = PROJECT_ROOT
    PROJECT_ROOT: Path = PROJECT_ROOT

    # Groq Cloud Configuration
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    groq_api_base: str = "https://api.groq.com/openai/v1"

    # Main API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # Stand-in Model Service Configuration
    standin_url: str = Field(default="http://127.0.0.1:8001", alias="STANDIN_URL")
    standin_port: int = Field(default=8001, alias="STANDIN_PORT")

    # Paths
    papers_dir: Path = PROJECT_ROOT / "papers"
    raw_papers_dir: Path = PROJECT_ROOT / "papers" / "raw"
    processed_papers_dir: Path = PROJECT_ROOT / "papers" / "processed"
    metadata_file: Path = PROJECT_ROOT / "papers" / "metadata.json"
    
    experiments_dir: Path = PROJECT_ROOT / "experiments"
    calibration_dir: Path = PROJECT_ROOT / "experiments" / "calibration"
    outputs_dir: Path = PROJECT_ROOT / "outputs"
    writeup_dir: Path = PROJECT_ROOT / "writeup"

    # Embedding & Retrieval Defaults
    embedding_model_name: str = "all-MiniLM-L6-v2"
    cross_encoder_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Resilience & Traffic Controls
    default_max_concurrency: int = Field(default=5, alias="DEFAULT_MAX_CONCURRENCY")
    default_queue_capacity: int = Field(default=20, alias="DEFAULT_QUEUE_CAPACITY")
    default_request_timeout: float = Field(default=25.0, alias="DEFAULT_REQUEST_TIMEOUT_SECONDS")
    default_rpm_budget: int = Field(default=30, alias="DEFAULT_RPM_BUDGET")
    default_daily_request_budget: int = Field(default=1000, alias="DEFAULT_DAILY_REQUEST_BUDGET")

settings = Settings()

