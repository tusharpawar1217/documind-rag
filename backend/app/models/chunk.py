"""Document chunk data model."""

from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, validator


class DocumentChunk(BaseModel):
    """
    Represents a chunk of document content with metadata and embedding.
    
    A chunk can be text, table (Markdown), or image summary.
    """
    
    chunk_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique chunk identifier")
    document_id: str = Field(..., description="Parent document UUID")
    content: str = Field(..., min_length=1, description="Text content, Markdown table, or image summary")
    chunk_type: str = Field(..., description="Type: text, table, or image")
    page_number: int = Field(..., ge=1, description="Page number for citation")
    chunk_index: int = Field(..., ge=0, description="Sequential index within document")
    embedding: Optional[List[float]] = Field(default=None, description="768-dimensional vector")
    token_count: int = Field(default=0, ge=0, description="Number of tokens in content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator("chunk_type")
    def validate_chunk_type(cls, v):
        """Validate chunk type is one of the allowed values."""
        allowed_types = {"text", "table", "image"}
        if v not in allowed_types:
            raise ValueError(f"chunk_type must be one of {allowed_types}, got {v}")
        return v
    
    @validator("chunk_id", "document_id")
    def validate_uuid_format(cls, v):
        """Validate UUID format."""
        try:
            UUID(v)
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid UUID format: {v}")
        return v
    
    @validator("embedding")
    def validate_embedding_dimension(cls, v):
        """Validate embedding has exactly 768 dimensions if provided."""
        if v is not None and len(v) != 768:
            raise ValueError(f"Embedding must have 768 dimensions, got {len(v)}")
        return v
    
    @validator("embedding")
    def validate_embedding_values(cls, v):
        """Validate embedding contains only finite values."""
        if v is not None:
            import math
            for val in v:
                if not math.isfinite(val):
                    raise ValueError("Embedding contains NaN or Infinity values")
        return v
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "chunk_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "content": "Climate change is causing significant impacts worldwide.",
                "chunk_type": "text",
                "page_number": 5,
                "chunk_index": 0,
                "token_count": 9,
                "metadata": {
                    "document_name": "climate_report.pdf",
                    "total_pages": 50
                }
            }
        }


class ChunkCreate(BaseModel):
    """Schema for creating a new chunk."""
    
    document_id: str
    content: str = Field(..., min_length=1)
    chunk_type: str
    page_number: int = Field(..., ge=1)
    chunk_index: int = Field(..., ge=0)
    token_count: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("chunk_type")
    def validate_chunk_type(cls, v):
        """Validate chunk type."""
        allowed_types = {"text", "table", "image"}
        if v not in allowed_types:
            raise ValueError(f"chunk_type must be one of {allowed_types}")
        return v
