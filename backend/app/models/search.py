"""Search result and query data models."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator


class SearchResult(BaseModel):
    """
    Represents a search result with relevance scores.
    
    Contains multiple score types: semantic, BM25, rerank, and final combined.
    """
    
    chunk_id: str = Field(..., description="Chunk UUID")
    document_id: str = Field(..., description="Document UUID")
    content: str = Field(..., description="Chunk content")
    chunk_type: str = Field(..., description="Type: text, table, or image")
    page_number: int = Field(..., ge=1, description="Page number for citation")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Semantic similarity score")
    bm25_score: float = Field(default=0.0, ge=0.0, description="Keyword matching score")
    rerank_score: float = Field(default=0.0, description="Cross-encoder score")
    final_score: float = Field(..., ge=0.0, description="Combined weighted score")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("chunk_type")
    def validate_chunk_type(cls, v):
        """Validate chunk type."""
        allowed_types = {"text", "table", "image"}
        if v not in allowed_types:
            raise ValueError(f"chunk_type must be one of {allowed_types}")
        return v
    
    @validator("relevance_score", "bm25_score")
    def validate_score_range(cls, v):
        """Validate scores are in valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {v}")
        return v
    
    @validator("final_score")
    def validate_final_score(cls, v):
        """Validate final score is non-negative."""
        if v < 0.0:
            raise ValueError(f"Final score must be non-negative, got {v}")
        return v
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "chunk_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "content": "Climate change is causing significant impacts...",
                "chunk_type": "text",
                "page_number": 5,
                "relevance_score": 0.92,
                "bm25_score": 0.85,
                "rerank_score": 0.88,
                "final_score": 0.89,
                "metadata": {
                    "document_name": "climate_report.pdf"
                }
            }
        }


class Citation(BaseModel):
    """Citation with page number and source information."""
    
    page_number: int = Field(..., ge=1, description="Page number")
    document_id: str = Field(..., description="Document UUID")
    document_name: str = Field(..., description="Document filename")
    content: str = Field(..., description="Content snippet from source")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    
    @validator("page_number")
    def validate_page_number(cls, v):
        """Validate page number is positive."""
        if v < 1:
            raise ValueError("page_number must be at least 1")
        return v
    
    @validator("content")
    def truncate_content(cls, v):
        """Truncate content to reasonable length for display."""
        max_length = 200
        if len(v) > max_length:
            return v[:max_length] + "..."
        return v
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "page_number": 5,
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "document_name": "climate_report.pdf",
                "content": "Rising temperatures are melting polar ice caps...",
                "relevance_score": 0.92
            }
        }


class QueryRequest(BaseModel):
    """Request schema for document query."""
    
    query: str = Field(..., min_length=1, max_length=500, description="User query")
    document_ids: Optional[list[str]] = Field(default=None, description="Filter by specific documents")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results")
    include_metadata: bool = Field(default=True, description="Include metadata in response")
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum confidence threshold")
    
    @validator("query")
    def validate_query(cls, v):
        """Validate and sanitize query."""
        # Strip whitespace
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v
    
    @validator("document_ids")
    def validate_document_ids(cls, v):
        """Validate document IDs are valid UUIDs."""
        if v:
            from uuid import UUID
            for doc_id in v:
                try:
                    UUID(doc_id)
                except (ValueError, AttributeError):
                    raise ValueError(f"Invalid document UUID: {doc_id}")
        return v
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "query": "What are the key findings about climate change?",
                "document_ids": ["123e4567-e89b-12d3-a456-426614174000"],
                "top_k": 5,
                "include_metadata": True,
                "min_confidence": 0.7
            }
        }


class QueryResponse(BaseModel):
    """Response schema for document query."""
    
    answer: str = Field(..., description="Generated answer")
    citations: list[Citation] = Field(..., description="Page citations")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    processing_time: float = Field(..., ge=0.0, description="Processing time in milliseconds")
    sources_used: int = Field(..., ge=0, description="Number of chunks used")
    
    @validator("confidence")
    def validate_confidence(cls, v):
        """Validate confidence is in valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {v}")
        return v
    
    @validator("answer")
    def validate_answer_not_empty(cls, v):
        """Validate answer is not empty."""
        if not v.strip():
            raise ValueError("Answer cannot be empty")
        return v
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "answer": "The key findings indicate that climate change is causing...",
                "citations": [
                    {
                        "page_number": 5,
                        "document_id": "123e4567-e89b-12d3-a456-426614174000",
                        "document_name": "climate_report.pdf",
                        "content": "Rising temperatures are melting...",
                        "relevance_score": 0.92
                    }
                ],
                "confidence": 0.87,
                "processing_time": 1450.5,
                "sources_used": 5
            }
        }
