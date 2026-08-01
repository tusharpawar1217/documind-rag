"""
API Routes - FastAPI endpoints for the RAG system.

This module defines all HTTP endpoints for document upload, search, and management.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Import RAG components
from src.ingestion.loader import document_loader
from src.chunking.chunker import semantic_chunker
from src.embeddings.embedder import embedder
from src.vectordb.vector_store import vector_store
from src.retrieval.retriever import HybridRetriever
from src.llm.llm_client import llm_client
from src.prompts.prompt_templates import prompts
from src.utils.helpers import get_logger

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=config['app']['name'],
    version=config['app']['version'],
    description="RAG-based Multi-Document Intelligence System"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize retriever
retriever = HybridRetriever(vector_store, embedder)


# Request/Response Models
class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    hybrid_alpha: Optional[float] = 0.5
    generate_response: Optional[bool] = True
    temperature: Optional[float] = 0.7


class QueryResponse(BaseModel):
    query: str
    results: List[dict]
    response: Optional[str] = None
    total_results: int


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": config['app']['version'],
        "service": config['app']['name']
    }


# Document upload endpoint
@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document.
    
    Args:
        file: PDF file to upload
        
    Returns:
        Processing status and document metadata
    """
    try:
        # Read file content
        content = await file.read()
        
        # Validate document
        is_valid, error = document_loader.validate_document(content, file.filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error)
        
        # TODO: Save file, extract text, chunk, embed, and store
        # This is a simplified version - full implementation in app/services/ingestion_service.py
        
        return {
            "status": "success",
            "message": "Document uploaded and processing started",
            "filename": file.filename,
            "size": len(content)
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Search/Query endpoint
@app.post("/api/v1/search/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Search documents and generate AI response.
    
    Args:
        request: Query request with search parameters
        
    Returns:
        Search results and generated response
    """
    try:
        # Retrieve relevant chunks
        results = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            alpha=request.hybrid_alpha
        )
        
        response_text = None
        if request.generate_response and results:
            # Build context from results
            context = "\n\n".join([
                f"[Source: {r['metadata'].get('document_name', 'Unknown')}]\n{r['content']}"
                for r in results[:5]
            ])
            
            # Generate response using LLM
            prompt = prompts.get_rag_prompt(context, request.query)
            response_text = llm_client.generate(
                prompt=prompt,
                temperature=request.temperature,
                system_instruction=prompts.get_system_prompt()
            )
        
        return QueryResponse(
            query=request.query,
            results=results,
            response=response_text,
            total_results=len(results)
        )
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# List documents endpoint
@app.get("/api/v1/documents")
async def list_documents():
    """
    List all uploaded documents.
    
    Returns:
        List of document metadata
    """
    # TODO: Implement document listing from storage/database
    return {"documents": [], "total": 0}


# Get document statistics
@app.get("/api/v1/documents/stats")
async def get_statistics():
    """
    Get document statistics.
    
    Returns:
        Statistics about uploaded documents
    """
    # TODO: Implement statistics calculation
    return {
        "total_documents": 0,
        "total_chunks": 0,
        "total_size": 0
    }


# Delete document endpoint
@app.delete("/api/v1/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and all its chunks.
    
    Args:
        document_id: Document ID to delete
        
    Returns:
        Deletion status
    """
    try:
        # Delete from vector store
        vector_store.delete_by_filter({"document_id": document_id})
        
        return {"status": "success", "message": "Document deleted"}
        
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
