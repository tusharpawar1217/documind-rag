"""
Test Server - Simplified server to test PDF upload functionality.
"""

import os
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
import pymupdf  # PyMuPDF
import io

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="DocuMind RAG Test", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
documents = []
chunks_store = []


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


class QueryResponse(BaseModel):
    query: str
    results: List[dict]
    response: Optional[str] = None
    total_results: int


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "DocuMind RAG Test"
    }


@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a PDF document with page-level tracking."""
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        content = await file.read()
        
        # Extract text from PDF using PyMuPDF with page tracking
        pdf_document = pymupdf.open(stream=content, filetype="pdf")
        
        # Get page count before processing
        num_pages = len(pdf_document)
        
        all_text = ""
        page_texts = []  # Store text per page
        chunk_index = 0
        
        # Process each page separately
        for page_num in range(num_pages):
            page = pdf_document[page_num]
            page_text = page.get_text()
            
            # Store page text for reference
            page_texts.append({
                "page_num": page_num + 1,
                "text": page_text,
                "char_count": len(page_text)
            })
            
            all_text += page_text + "\n\n"
            
            # Smart chunking: Split page into paragraphs/sections
            paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip() and len(p.strip()) > 50]
            
            # If no good paragraphs, split by sentences
            if not paragraphs and page_text.strip():
                sentences = [s.strip() + '.' for s in page_text.split('.') if len(s.strip()) > 20]
                # Group sentences into chunks of ~500 chars
                chunk_text = ""
                for sentence in sentences:
                    if len(chunk_text) + len(sentence) < 500:
                        chunk_text += " " + sentence
                    else:
                        if chunk_text:
                            paragraphs.append(chunk_text.strip())
                        chunk_text = sentence
                if chunk_text:
                    paragraphs.append(chunk_text.strip())
            
            # Store chunks with page information
            for para_idx, chunk_text in enumerate(paragraphs):
                # Calculate position on page (beginning, middle, end)
                position_pct = (para_idx + 1) / len(paragraphs) if paragraphs else 0
                if position_pct < 0.33:
                    position = "top"
                elif position_pct < 0.67:
                    position = "middle"
                else:
                    position = "bottom"
                
                chunks_store.append({
                    "chunk_id": f"{len(documents)}_page{page_num+1}_chunk{para_idx}",
                    "document_id": f"doc_{len(documents)}",
                    "document_name": file.filename,
                    "content": chunk_text,
                    "chunk_index": chunk_index,
                    "page_number": page_num + 1,
                    "position_on_page": position,
                    "paragraph_index": para_idx,
                    "char_length": len(chunk_text),
                    "page_total_chunks": len(paragraphs)
                })
                chunk_index += 1
        
        pdf_document.close()
        
        # Store document info
        doc_id = f"doc_{len(documents)}"
        doc_info = {
            "id": doc_id,
            "filename": file.filename,
            "size": len(content),
            "num_pages": num_pages,
            "num_chunks": chunk_index,
            "text_length": len(all_text),
            "pages_info": page_texts
        }
        documents.append(doc_info)
        
        return {
            "status": "success",
            "message": f"Document uploaded and processed successfully. Extracted {num_pages} pages and {chunk_index} chunks.",
            "document": {
                "id": doc_id,
                "filename": file.filename,
                "size": len(content),
                "num_pages": num_pages,
                "num_chunks": chunk_index
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/api/v1/search/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Search documents with page-level accuracy and source citations."""
    try:
        query_lower = request.query.lower()
        
        # Enhanced keyword search with relevance scoring
        results = []
        for chunk in chunks_store:
            content_lower = chunk['content'].lower()
            
            # Calculate relevance score
            score = 0.0
            query_words = query_lower.split()
            content_words = content_lower.split()
            
            # Exact phrase match (highest score)
            if query_lower in content_lower:
                score = 0.95
            else:
                # Word overlap scoring
                matching_words = sum(1 for word in query_words if word in content_words)
                if matching_words > 0:
                    score = (matching_words / len(query_words)) * 0.8
            
            if score > 0:
                results.append({
                    "content": chunk['content'],
                    "score": score,
                    "metadata": {
                        "document_id": chunk['document_id'],
                        "document_name": chunk['document_name'],
                        "page_number": chunk['page_number'],
                        "position_on_page": chunk.get('position_on_page', 'unknown'),
                        "chunk_index": chunk['chunk_index'],
                        "char_length": chunk['char_length']
                    }
                })
        
        # Sort by score (highest first)
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # Limit to top_k
        top_results = results[:request.top_k]
        
        # Generate enhanced response with page citations
        response_text = None
        if top_results:
            # Build context with page numbers
            context_parts = []
            page_refs = set()
            
            for idx, result in enumerate(top_results[:3], 1):
                page_num = result['metadata']['page_number']
                position = result['metadata']['position_on_page']
                doc_name = result['metadata']['document_name']
                content_preview = result['content'][:300] + "..." if len(result['content']) > 300 else result['content']
                
                context_parts.append(
                    f"[Source {idx}: {doc_name}, Page {page_num} ({position})]\n{content_preview}"
                )
                page_refs.add((doc_name, page_num))
            
            # Generate response
            response_text = f"Based on your question: '{request.query}'\n\n"
            response_text += "I found relevant information in the following locations:\n\n"
            
            for idx, part in enumerate(context_parts, 1):
                response_text += f"{part}\n\n"
            
            # Add summary
            if len(page_refs) == 1:
                doc, page = list(page_refs)[0]
                response_text += f"\n📄 **Source**: {doc}, Page {page}\n"
            else:
                response_text += f"\n📄 **Sources**: Found across {len(page_refs)} pages:\n"
                for doc, page in sorted(page_refs, key=lambda x: x[1]):
                    response_text += f"   • {doc}, Page {page}\n"
            
            response_text += f"\n💡 **Tip**: Review these specific pages in your PDF for complete details."
            
        else:
            response_text = f"No relevant information found for: '{request.query}'\n\n"
            response_text += "Try:\n"
            response_text += "• Using different keywords\n"
            response_text += "• Making your question more specific\n"
            response_text += "• Checking if the document contains this information"
        
        return QueryResponse(
            query=request.query,
            results=top_results,
            response=response_text,
            total_results=len(results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/documents")
async def list_documents():
    """List all uploaded documents."""
    return {
        "documents": documents,
        "total": len(documents)
    }


@app.get("/api/v1/documents/stats")
async def get_statistics():
    """Get document statistics."""
    total_size = sum(doc['size'] for doc in documents)
    total_chunks = len(chunks_store)
    
    return {
        "total_documents": len(documents),
        "total_chunks": total_chunks,
        "total_size": total_size
    }


@app.delete("/api/v1/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document."""
    global documents, chunks_store
    
    # Remove from documents
    documents = [d for d in documents if d['id'] != document_id]
    
    # Remove chunks
    chunks_store = [c for c in chunks_store if c['document_id'] != document_id]
    
    return {"status": "success", "message": "Document deleted"}


if __name__ == "__main__":
    print("🚀 Starting DocuMind RAG Test Server...")
    print("📍 Server will run on http://localhost:8000")
    print("📚 Upload PDFs at http://localhost:8000/api/v1/documents/upload")
    print("🔍 Query at http://localhost:8000/api/v1/search/query")
    
    uvicorn.run(
        "test_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
