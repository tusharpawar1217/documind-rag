"""Document data model."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, validator


class DocumentStatus(str, Enum):
    """Document processing status."""
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    PENDING = "pending"


class Document(BaseModel):
    """
    Represents a document in the system.
    
    Tracks metadata, processing status, and chunk information.
    """
    
    document_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique document identifier")
    filename: str = Field(..., description="Original filename with .pdf extension")
    file_path: str = Field(..., description="Storage path to the file")
    page_count: int = Field(..., ge=1, description="Total pages in PDF")
    status: DocumentStatus = Field(default=DocumentStatus.PROCESSING, description="Processing status")
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    chunk_count: int = Field(default=0, ge=0, description="Total chunks created")
    file_size: int = Field(..., ge=1, description="Size in bytes")
    user_id: Optional[str] = Field(default=None, description="Owner user ID")
    error_message: Optional[str] = Field(default=None, description="Error details if status is ERROR")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator("document_id")
    def validate_document_id(cls, v):
        """Validate document ID is valid UUID."""
        try:
            UUID(v)
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid UUID format: {v}")
        return v
    
    @validator("filename")
    def validate_filename(cls, v):
        """Validate filename has .pdf extension."""
        if not v.lower().endswith('.pdf'):
            raise ValueError("Filename must have .pdf extension")
        return v
    
    @validator("file_size")
    def validate_file_size(cls, v):
        """Validate file size is within limit."""
        from app.core.config import MAX_FILE_SIZE_BYTES
        if v > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size {v} exceeds maximum {MAX_FILE_SIZE_BYTES} bytes")
        return v
    
    @validator("page_count")
    def validate_page_count(cls, v):
        """Validate page count is positive."""
        if v < 1:
            raise ValueError("page_count must be at least 1")
        return v
    
    class Config:
        """Pydantic config."""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "research_paper.pdf",
                "file_path": "/data/uploads/123e4567-e89b-12d3-a456-426614174000.pdf",
                "page_count": 10,
                "status": "ready",
                "chunk_count": 45,
                "file_size": 2048576,
                "user_id": "user-123",
                "metadata": {
                    "title": "Climate Change Research",
                    "upload_ip": "192.168.1.1"
                }
            }
        }


class DocumentCreate(BaseModel):
    """Schema for creating a new document."""
    
    filename: str = Field(..., min_length=1)
    file_size: int = Field(..., ge=1)
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("filename")
    def validate_filename(cls, v):
        """Validate filename has .pdf extension."""
        if not v.lower().endswith('.pdf'):
            raise ValueError("Filename must have .pdf extension")
        return v


class DocumentUpdate(BaseModel):
    """Schema for updating document fields."""
    
    status: Optional[DocumentStatus] = None
    page_count: Optional[int] = Field(default=None, ge=1)
    chunk_count: Optional[int] = Field(default=None, ge=0)
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentResponse(BaseModel):
    """Schema for document API responses."""
    
    document_id: str
    filename: str
    page_count: int
    status: str
    upload_date: datetime
    chunk_count: int
    file_size: int
    user_id: Optional[str] = None
    error_message: Optional[str] = None
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "research_paper.pdf",
                "page_count": 10,
                "status": "ready",
                "upload_date": "2024-01-15T10:30:00Z",
                "chunk_count": 45,
                "file_size": 2048576,
                "user_id": "user-123"
            }
        }
