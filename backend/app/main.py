"""FastAPI application entry point."""

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.core.security import get_current_user
from app.models import QueryRequest, QueryResponse, DocumentResponse
from app.services import (
    qdrant_service,
    ingestion_service,
    hybrid_search_engine,
    response_generator,
)
from app.utils.validators import file_validator, query_validator

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DocuMind RAG System",
    description="Multi-Document Intelligence System with Precise Page Citations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Setup rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting DocuMind RAG System...")
    
    try:
        # Initialize Qdrant collection
        qdrant_service.initialize_collection()
        logger.info("Qdrant collection initialized")
        
        # Health check Gemini API
        if not gemini_client.health_check():
            logger.warning("Gemini API health check failed")
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down DocuMind RAG System...")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "DocuMind RAG System",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns system status and service availability.
    """
    qdrant_healthy = qdrant_service.health_check()
    gemini_healthy = gemini_client.health_check()
    
    return {
        "status": "healthy" if (qdrant_healthy and gemini_healthy) else "degraded",
        "services": {
            "qdrant": "up" if qdrant_healthy else "down",
            "gemini": "up" if gemini_healthy else "down",
        }
    }


@app.post("/api/upload")
@limiter.limit(f"{settings.rate_limit_uploads_per_hour}/hour")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """
    Upload and process PDF document.
    
    Args:
        file: PDF file upload
        user_id: Authenticated user ID
        
    Returns:
        Upload status and document details
    """
    try:
        # Read file content
        file_content = await file.read()
        
        # Validate file type
        is_valid, error = file_validator.validate_file_type(
            file_content,
            file.filename
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        # Validate file size
        is_valid, error = file_validator.validate_file_size(len(file_content))
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        # Malware scan
        is_safe, error = file_validator.scan_for_malware(file_content)
        if not is_safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error or "File failed security scan"
            )
        
        # Process document
        logger.info(f"Processing upload: {file.filename} for user {user_id}")
        result = await ingestion_service.ingest_document(
            file_content=file_content,
            filename=file.filename,
            user_id=user_id,
            metadata={"upload_filename": file.filename}
        )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Document processing failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@app.post("/api/query", response_model=QueryResponse)
@limiter.limit(f"{settings.rate_limit_queries_per_hour}/hour")
async def query_documents(
    request: QueryRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Query documents and get answer with citations.
    
    Args:
        request: Query request with parameters
        user_id: Authenticated user ID
        
    Returns:
        Answer with precise page citations
    """
    try:
        # Validate and sanitize query
        is_valid, error = query_validator.validate_query(request.query)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        sanitized_query = query_validator.sanitize_query(request.query)
        
        logger.info(f"Processing query for user {user_id}")
        
        # Step 1: Hybrid search
        search_results = hybrid_search_engine.search(
            query=sanitized_query,
            top_k=settings.top_k_search,
            rerank_top_n=request.top_k,
            document_ids=request.document_ids,
            user_id=user_id,
        )
        
        # Step 2: Generate answer with citations
        response = response_generator.generate_answer(
            query=sanitized_query,
            search_results=search_results
        )
        
        # Filter by confidence if specified
        if request.min_confidence > 0 and response.confidence < request.min_confidence:
            return QueryResponse(
                answer="No high-confidence answer found. Please try refining your query.",
                citations=[],
                confidence=response.confidence,
                processing_time=response.processing_time,
                sources_used=0
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )


@app.get("/api/documents")
async def list_documents(user_id: str = Depends(get_current_user)):
    """
    List all documents for authenticated user.
    
    Args:
        user_id: Authenticated user ID
        
    Returns:
        List of user's documents
    """
    # TODO: Implement document metadata storage and retrieval
    # For now, return placeholder
    return {
        "documents": [],
        "total": 0
    }


@app.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Delete a document and its chunks.
    
    Args:
        document_id: Document UUID
        user_id: Authenticated user ID
        
    Returns:
        Deletion confirmation
    """
    try:
        # TODO: Verify document ownership before deletion
        
        success = ingestion_service.delete_document(document_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return {
            "status": "success",
            "message": f"Document {document_id} deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deletion failed: {str(e)}"
        )


@app.get("/api/documents/{document_id}/status")
async def get_document_status(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Check document processing status.
    
    Args:
        document_id: Document UUID
        user_id: Authenticated user ID
        
    Returns:
        Document status
    """
    # TODO: Implement document status tracking
    return {
        "document_id": document_id,
        "status": "ready"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
