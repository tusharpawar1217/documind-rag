"""Configuration management using pydantic-settings."""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")

    # Qdrant Configuration
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    qdrant_collection_name: str = Field(default="documind", env="QDRANT_COLLECTION_NAME")
    qdrant_pool_size: int = Field(default=20, env="QDRANT_POOL_SIZE")

    # Redis Configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")

    # Application Settings
    max_file_size_mb: int = Field(default=50, env="MAX_FILE_SIZE_MB")
    similarity_threshold: float = Field(default=0.75, env="SIMILARITY_THRESHOLD")
    max_chunk_size: int = Field(default=512, env="MAX_CHUNK_SIZE")
    top_k_search: int = Field(default=20, env="TOP_K_SEARCH")
    rerank_top_n: int = Field(default=5, env="RERANK_TOP_N")
    embedding_batch_size: int = Field(default=32, env="EMBEDDING_BATCH_SIZE")
    embedding_dimension: int = Field(default=768)

    # Security
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")

    # Storage
    upload_dir: Path = Field(default=Path("./data/uploads"), env="UPLOAD_DIR")
    vector_storage_dir: Path = Field(default=Path("./data/vectors"), env="VECTOR_STORAGE_DIR")

    # Rate Limiting
    rate_limit_uploads_per_hour: int = Field(default=10, env="RATE_LIMIT_UPLOADS_PER_HOUR")
    rate_limit_queries_per_hour: int = Field(default=100, env="RATE_LIMIT_QUERIES_PER_HOUR")
    rate_limit_global_per_minute: int = Field(default=1000, env="RATE_LIMIT_GLOBAL_PER_MINUTE")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Path = Field(default=Path("./logs/app.log"), env="LOG_FILE")

    # Performance
    worker_processes: int = Field(default=4, env="WORKER_PROCESSES")

    # Models
    reranker_model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    spacy_model: str = Field(default="en_core_web_sm")

    # BM25 Parameters
    bm25_k1: float = Field(default=1.5)
    bm25_b: float = Field(default=0.75)

    # HNSW Index Parameters
    hnsw_ef_construct: int = Field(default=128)
    hnsw_m: int = Field(default=16)

    @validator("similarity_threshold")
    def validate_similarity_threshold(cls, v):
        """Validate similarity threshold is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        return v

    @validator("max_chunk_size")
    def validate_max_chunk_size(cls, v):
        """Validate max chunk size is positive."""
        if v <= 0:
            raise ValueError("max_chunk_size must be positive")
        return v

    @validator("upload_dir", "vector_storage_dir", "log_file")
    def create_directories(cls, v):
        """Create directories if they don't exist."""
        if isinstance(v, Path):
            v.parent.mkdir(parents=True, exist_ok=True)
            if v.suffix:  # It's a file
                v.parent.mkdir(parents=True, exist_ok=True)
            else:  # It's a directory
                v.mkdir(parents=True, exist_ok=True)
        return v

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Constants
MAX_FILE_SIZE_BYTES = settings.max_file_size_mb * 1024 * 1024
MAX_QUERY_LENGTH = 500
COSINE_DISTANCE = "Cosine"
PDF_MIME_TYPE = "application/pdf"
PDF_MAGIC_BYTES = b"%PDF"
