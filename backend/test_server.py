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
import uuid
from datetime import datetime
import google.generativeai as genai
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import tempfile

# Import the new Unlimited-OCR service
try:
    from app.services.unlimited_ocr import unlimited_ocr_service
    UNLIMITED_OCR_AVAILABLE = True
    print("✅ Unlimited-OCR service imported successfully")
except Exception as e:
    UNLIMITED_OCR_AVAILABLE = False
    print(f"⚠️ Unlimited-OCR not available: {e}")
    print("📝 Falling back to PyMuPDF extraction")

# Load environment variables
load_dotenv()

# Initialize Gemini for LLM responses and embeddings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    llm_model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini LLM initialized")
    print("✅ Embedding model ready (text-embedding-004)")
else:
    llm_model = None
    print("⚠️ Gemini API key not found - chat will use simple responses")

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
chunk_embeddings = []  # Store embeddings for semantic search
chat_history = []  # Store conversation history
chat_sessions = {}  # Store chat history per session


def generate_embedding(text: str) -> List[float]:
    """Generate embedding using Gemini's text-embedding-004 model."""
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def classify_chunk_type(text: str, page_num: int) -> str:
    """Classify chunk as front-matter, content, or references."""
    text_lower = text.lower()
    
    # Front-matter detection
    front_matter_indicators = [
        'bonafide certificate', 'certificate of approval',
        'acknowledgement', 'acknowledgment',
        'table of contents', 'list of figures', 'list of tables',
        'declaration', 'this is to certify',
        'under my supervision', 'declare that'
    ]
    
    for indicator in front_matter_indicators:
        if indicator in text_lower:
            return 'front_matter'
    
    # References/Bibliography detection
    references_indicators = [
        'bibliography', 'references', 'works cited',
        '[1]', '[2]', '[3]',  # Numbered references
    ]
    
    # Check if page has heavy reference patterns
    if any(indicator in text_lower for indicator in references_indicators):
        # Also check for reference-like patterns
        if text.count('[') > 3 or text.count('doi:') > 2:
            return 'references'
    
    # Abstract/Introduction detection (high priority content)
    high_priority_indicators = [
        'abstract', 'introduction', 'chapter 1',
        'this thesis', 'this research', 'this work presents',
        'main contribution', 'key contribution'
    ]
    
    if any(indicator in text_lower[:200] for indicator in high_priority_indicators):
        return 'high_priority_content'
    
    # Regular content
    return 'content'


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    use_chat_history: Optional[bool] = True
    session_id: Optional[str] = "default"


class QueryResponse(BaseModel):
    query: str
    enhanced_query: Optional[str] = None
    results: List[dict]
    response: Optional[str] = None
    total_results: int
    chat_history_used: bool = False


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    query_type: Optional[str] = None


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    top_k: Optional[int] = 5
    use_history: Optional[bool] = True


class ChatResponse(BaseModel):
    response: str
    session_id: str
    sources: List[dict]
    conversation_history: List[ChatMessage]


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "DocuMind RAG Test"
    }


def enhance_user_prompt(raw_query: str, chat_context: List[dict] = None) -> dict:
    """
    Enhance and reformulate user queries for better search results.
    
    Transforms casual/raw queries into precise, searchable queries.
    Uses chat history for context-aware enhancement.
    """
    # Clean the query
    query = raw_query.strip()
    
    # Detect query type
    query_lower = query.lower()
    query_type = "general"
    
    if any(word in query_lower for word in ["what", "explain", "describe", "tell me about"]):
        query_type = "explanation"
    elif any(word in query_lower for word in ["how", "steps", "process", "way to"]):
        query_type = "how-to"
    elif any(word in query_lower for word in ["why", "reason", "because"]):
        query_type = "reasoning"
    elif any(word in query_lower for word in ["when", "date", "time"]):
        query_type = "temporal"
    elif any(word in query_lower for word in ["who", "author", "person"]):
        query_type = "entity"
    elif any(word in query_lower for word in ["where", "location", "place"]):
        query_type = "location"
    elif any(word in query_lower for word in ["list", "enumerate", "show me all"]):
        query_type = "enumeration"
    elif "?" not in query and len(query.split()) < 5:
        query_type = "keyword"
    
    # Extract key terms
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                  "have", "has", "had", "do", "does", "did", "will", "would", "could",
                  "should", "may", "might", "can", "about", "from", "with", "this", "that"}
    
    words = query_lower.replace("?", "").replace(",", "").split()
    key_terms = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Build enhanced query
    enhanced_query = query
    search_keywords = " ".join(key_terms[:5])  # Top 5 key terms
    
    # Add context from previous conversation
    context_hint = ""
    if chat_context and len(chat_context) > 0:
        last_user_msg = next((msg for msg in reversed(chat_context) if msg['role'] == 'user'), None)
        if last_user_msg and last_user_msg['content'].lower() != query_lower:
            # User is following up - add context
            context_hint = f" (following up on: {last_user_msg['content'][:50]}...)"
    
    return {
        "original": raw_query,
        "enhanced": enhanced_query,
        "search_keywords": search_keywords,
        "key_terms": key_terms,
        "query_type": query_type,
        "context_hint": context_hint
    }


def get_chat_history(session_id: str, limit: int = 5) -> List[dict]:
    """Get recent chat history for a session."""
    session_history = [msg for msg in chat_history if msg.get('session_id') == session_id]
    return session_history[-limit:] if session_history else []


def save_to_chat_history(session_id: str, role: str, content: str, query_info: dict = None):
    """Save message to chat history."""
    from datetime import datetime
    
    message = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "query_type": query_info.get('query_type') if query_info else None,
        "key_terms": query_info.get('key_terms') if query_info else None
    }
    chat_history.append(message)
    
    # Keep only last 100 messages per session to avoid memory issues
    session_messages = [msg for msg in chat_history if msg['session_id'] == session_id]
    if len(session_messages) > 100:
        # Remove oldest messages
        oldest = session_messages[0]
        chat_history.remove(oldest)


@app.get("/api/v1/chat/history")
async def get_history(session_id: str = "default", limit: int = 20):
    """Get chat history for a session."""
    history = get_chat_history(session_id, limit)
    return {
        "session_id": session_id,
        "messages": history,
        "total": len(history)
    }


@app.delete("/api/v1/chat/history")
async def clear_history(session_id: str = "default"):
    """Clear chat history for a session."""
    global chat_history
    chat_history = [msg for msg in chat_history if msg.get('session_id') != session_id]
    return {"status": "success", "message": f"History cleared for session {session_id}"}


@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a PDF document with advanced OCR extraction."""
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        content = await file.read()
        
        # Save temporary file for OCR processing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Use intelligent extraction with Unlimited-OCR
            if UNLIMITED_OCR_AVAILABLE:
                print("🔍 Using Unlimited-OCR for advanced extraction...")
                extracted_text = unlimited_ocr_service.intelligent_extract(tmp_file_path)
                extraction_method = "Unlimited-OCR (Advanced)"
            else:
                print("📄 Using PyMuPDF fallback extraction...")
                # Fallback to PyMuPDF
                pdf_document = pymupdf.open(stream=content, filetype="pdf")
                extracted_text = ""
                for page in pdf_document:
                    extracted_text += page.get_text() + "\n\n"
                pdf_document.close()
                extraction_method = "PyMuPDF (Fallback)"
            
            print(f"✅ Extracted {len(extracted_text)} characters using {extraction_method}")
            
            # Get page count for metadata
            pdf_document = pymupdf.open(stream=content, filetype="pdf")
            num_pages = len(pdf_document)
            pdf_document.close()
            
            # Parse extracted text into structured pages
            # Split by page markers if present, otherwise use intelligent chunking
            page_texts = []
            if "--- Page" in extracted_text:
                # OCR result has page markers
                page_sections = extracted_text.split("--- Page")[1:]  # Skip first empty split
                for i, section in enumerate(page_sections):
                    # Extract page number and text
                    lines = section.strip().split('\n', 1)
                    page_text = lines[1] if len(lines) > 1 else section.strip()
                    page_texts.append({
                        "page_num": i + 1,
                        "text": page_text,
                        "char_count": len(page_text)
                    })
            else:
                # Estimate pages by content length
                estimated_page_length = len(extracted_text) // max(num_pages, 1)
                current_pos = 0
                
                for page_num in range(num_pages):
                    start_pos = current_pos
                    end_pos = min(current_pos + estimated_page_length, len(extracted_text))
                    
                    # Try to break at natural boundaries
                    if end_pos < len(extracted_text):
                        # Look for paragraph break within next 200 chars
                        search_end = min(end_pos + 200, len(extracted_text))
                        para_break = extracted_text.find('\n\n', end_pos, search_end)
                        if para_break > 0:
                            end_pos = para_break
                    
                    page_text = extracted_text[start_pos:end_pos].strip()
                    page_texts.append({
                        "page_num": page_num + 1,
                        "text": page_text,
                        "char_count": len(page_text)
                    })
                    current_pos = end_pos
        
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        
        all_text = extracted_text
        chunk_index = 0
        
        # IMPROVED CHUNKING: Process all pages with overlapping chunks
        chunk_size = 800  # Target chunk size in characters
        chunk_overlap = 150  # Overlap between chunks for context continuity
        
        for page_data in page_texts:
            page_num = page_data["page_num"] - 1  # 0-indexed for processing
            page_text = page_data["text"]
            
            if not page_text.strip():
                continue
            
            # Split into chunks with overlap
            paragraphs = []
            
            # First, try paragraph boundaries
            raw_paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
            
            if raw_paragraphs:
                # Process each paragraph
                for para in raw_paragraphs:
                    # If paragraph is small enough, keep it as is
                    if len(para) <= chunk_size:
                        if len(para) > 100:  # Only keep substantial paragraphs
                            paragraphs.append(para)
                    else:
                        # Split large paragraph by sentences
                        import re
                        sentences = re.split(r'(?<=[.!?])\s+', para)
                        
                        current_chunk = ""
                        for sentence in sentences:
                            # Add sentence to current chunk if it fits
                            if len(current_chunk) + len(sentence) <= chunk_size:
                                current_chunk += " " + sentence if current_chunk else sentence
                            else:
                                # Save current chunk and start new one with overlap
                                if current_chunk:
                                    paragraphs.append(current_chunk.strip())
                                    
                                    # Create overlap from end of previous chunk
                                    words = current_chunk.split()
                                    overlap_words = []
                                    overlap_len = 0
                                    for word in reversed(words):
                                        if overlap_len + len(word) < chunk_overlap:
                                            overlap_words.insert(0, word)
                                            overlap_len += len(word) + 1
                                        else:
                                            break
                                    
                                    current_chunk = " ".join(overlap_words) + " " + sentence
                                else:
                                    current_chunk = sentence
                        
                        # Add last chunk
                        if current_chunk and len(current_chunk.strip()) > 100:
                            paragraphs.append(current_chunk.strip())
            
            # Fallback to word-based splitting if no good paragraphs
            if not paragraphs and page_text.strip():
                words = page_text.split()
                current_chunk = []
                current_length = 0
                
                for word in words:
                    current_chunk.append(word)
                    current_length += len(word) + 1
                    
                    if current_length >= chunk_size:
                        chunk_text = " ".join(current_chunk)
                        if len(chunk_text) > 100:
                            paragraphs.append(chunk_text)
                        
                        # Keep overlap
                        overlap_words = current_chunk[-20:] if len(current_chunk) > 20 else current_chunk
                        current_chunk = overlap_words
                        current_length = sum(len(w) + 1 for w in overlap_words)
                
                # Add final chunk
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    if len(chunk_text) > 100:
                        paragraphs.append(chunk_text)
            
            # Store chunks with page information, embeddings, and classification
            for para_idx, chunk_text in enumerate(paragraphs):
                # Calculate position on page
                position_pct = (para_idx + 1) / len(paragraphs) if paragraphs else 0
                if position_pct < 0.33:
                    position = "top"
                elif position_pct < 0.67:
                    position = "middle"
                else:
                    position = "bottom"
                
                # Classify chunk type
                chunk_type = classify_chunk_type(chunk_text, page_num + 1)
                
                # Generate embedding for semantic search
                embedding = generate_embedding(chunk_text)
                
                chunk_data = {
                    "chunk_id": f"{len(documents)}_page{page_num+1}_chunk{para_idx}",
                    "document_id": f"doc_{len(documents)}",
                    "document_name": file.filename,
                    "content": chunk_text,
                    "chunk_index": chunk_index,
                    "page_number": page_num + 1,
                    "position_on_page": position,
                    "paragraph_index": para_idx,
                    "char_length": len(chunk_text),
                    "page_total_chunks": len(paragraphs),
                    "chunk_type": chunk_type,
                    "extraction_method": extraction_method  # NEW: Track how content was extracted
                }
                
                chunks_store.append(chunk_data)
                
                if embedding:
                    chunk_embeddings.append(embedding)
                else:
                    # Fallback: zero vector if embedding fails
                    chunk_embeddings.append([0.0] * 768)
                
                chunk_index += 1
        
        # Count chunk types for stats
        chunk_types_count = {}
        extraction_methods_count = {}
        for chunk in chunks_store[len(chunks_store) - chunk_index:]:
            ctype = chunk.get('chunk_type', 'content')
            chunk_types_count[ctype] = chunk_types_count.get(ctype, 0) + 1
            
            method = chunk.get('extraction_method', 'Unknown')
            extraction_methods_count[method] = extraction_methods_count.get(method, 0) + 1
        
        print(f"✅ Generated {chunk_index} embeddings using {extraction_method}")
        print(f"📊 Chunk types: {chunk_types_count}")
        
        # Store document info
        doc_id = f"doc_{len(documents)}"
        doc_info = {
            "id": doc_id,
            "filename": file.filename,
            "size": len(content),
            "num_pages": num_pages,
            "num_chunks": chunk_index,
            "text_length": len(all_text),
            "pages_info": page_texts,
            "chunk_types": chunk_types_count,
            "extraction_method": extraction_method
        }
        documents.append(doc_info)
        
        return {
            "status": "success",
            "message": f"Document uploaded and processed with {extraction_method}. Extracted {num_pages} pages and {chunk_index} chunks with embeddings.",
            "document": {
                "id": doc_id,
                "filename": file.filename,
                "size": len(content),
                "num_pages": num_pages,
                "num_chunks": chunk_index,
                "chunk_types": chunk_types_count,
                "extraction_method": extraction_method
            }
        }
        
    except Exception as e:
        # Clean up temporary file on error
        try:
            if 'tmp_file_path' in locals():
                os.unlink(tmp_file_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


def semantic_search(query: str, top_k: int = 5, exclude_types: List[str] = None) -> List[dict]:
    """
    Semantic search using embeddings and cosine similarity.
    Returns ranked chunks based on semantic meaning, not keyword matching.
    FALLBACK: If embeddings fail, use keyword search.
    """
    if not chunks_store:
        return []
    
    if exclude_types is None:
        exclude_types = ['front_matter', 'references']  # Default: exclude boilerplate
    
    # Generate query embedding
    query_embedding = generate_embedding(query)
    if not query_embedding:
        print("⚠️ Failed to generate query embedding, falling back to keyword search")
        return keyword_search_fallback(query, top_k, exclude_types)
    
    # Continue with semantic search only if embeddings are available
    if not chunk_embeddings:
        print("⚠️ No chunk embeddings available, falling back to keyword search")
        return keyword_search_fallback(query, top_k, exclude_types)
    
    # Filter chunks by type
    valid_indices = []
    valid_chunks = []
    
    for idx, chunk in enumerate(chunks_store):
        chunk_type = chunk.get('chunk_type', 'content')
        if chunk_type not in exclude_types:
            valid_indices.append(idx)
            valid_chunks.append(chunk)
    
    if not valid_chunks:
        print("⚠️ No valid chunks after filtering")
        return []
    
    # Get embeddings for valid chunks
    valid_embeddings = [chunk_embeddings[idx] for idx in valid_indices]
    
    # Calculate cosine similarity
    query_emb_array = np.array(query_embedding).reshape(1, -1)
    chunk_emb_array = np.array(valid_embeddings)
    
    similarities = cosine_similarity(query_emb_array, chunk_emb_array)[0]
    
    # Create results with scores
    results = []
    for idx, (chunk, score) in enumerate(zip(valid_chunks, similarities)):
        results.append({
            "content": chunk['content'],
            "score": float(score),
            "metadata": {
                "document_id": chunk['document_id'],
                "document_name": chunk['document_name'],
                "page_number": chunk['page_number'],
                "position_on_page": chunk.get('position_on_page', 'unknown'),
                "chunk_index": chunk['chunk_index'],
                "char_length": chunk['char_length'],
                "chunk_type": chunk.get('chunk_type', 'content')
            }
        })
    
    # Sort by score (highest first)
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results[:top_k]


def keyword_search_fallback(query: str, top_k: int = 5, exclude_types: List[str] = None) -> List[dict]:
    """Keyword search fallback when embeddings fail."""
    print(f"🔍 Using keyword search fallback for: {query}")
    
    if exclude_types is None:
        exclude_types = ['front_matter', 'references']
    
    query_lower = query.lower()
    query_words = [w for w in query_lower.split() if len(w) > 2]
    
    results = []
    
    for chunk in chunks_store:
        chunk_type = chunk.get('chunk_type', 'content')
        if chunk_type in exclude_types:
            continue
            
        content_lower = chunk['content'].lower()
        
        # Calculate relevance score
        score = 0.0
        
        # Exact phrase match
        if query_lower in content_lower:
            score = 0.95
        else:
            # Word matching
            matching_words = sum(1 for word in query_words if word in content_lower)
            if matching_words > 0:
                score = (matching_words / len(query_words)) * 0.85
                
                # Boost for multiple matches
                for word in query_words:
                    if word in content_lower:
                        score += 0.05
        
        if score > 0:
            results.append({
                "content": chunk['content'],
                "score": min(score, 1.0),
                "metadata": {
                    "document_id": chunk['document_id'],
                    "document_name": chunk['document_name'],
                    "page_number": chunk['page_number'],
                    "position_on_page": chunk.get('position_on_page', 'unknown'),
                    "chunk_index": chunk['chunk_index'],
                    "char_length": chunk['char_length'],
                    "chunk_type": chunk.get('chunk_type', 'content')
                }
            })
    
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k]


def _generate_fallback_response(query, context_parts, page_refs, query_enhancement):
    """Generate response without LLM (fallback) - SHOULD NEVER BE USED NOW."""
    print("⚠️ WARNING: Using fallback response - LLM synthesis failed!")
    
    query_type = query_enhancement.get('query_type', 'general')
    
    # Build a structured response without LLM
    if query_type == "explanation":
        response = f"**Understanding: {query}**\n\n"
    elif query_type == "how-to":
        response = f"**How to: {query}**\n\n"
    elif query_type == "enumeration":
        response = f"**List: {query}**\n\n"
    else:
        response = f"**Answer to: {query}**\n\n"
    
    # Add context - but this should NOT be raw chunks with Source labels!
    # Try to at least format them better
    response += "Found relevant information:\n\n"
    for idx, part in enumerate(context_parts, 1):
        # Remove the [Source N:...] label and just show content
        if ']' in part:
            content_only = part.split(']', 1)[1].strip() if ']' in part else part
        else:
            content_only = part
        response += f"{content_only}\n\n"
    
    # Add page summary
    response += "\n" + "─" * 60 + "\n"
    response += "**📚 Sources**\n"
    response += "─" * 60 + "\n\n"
    if len(page_refs) == 1:
        doc, page = list(page_refs)[0]
        response += f"📄 {doc} - Page {page}\n"
    else:
        unique_pages = sorted(set(page for doc, page in page_refs))
        doc_name = list(page_refs)[0][0]
        pages_str = ", ".join(str(p) for p in unique_pages)
        response += f"📄 {doc_name} - Pages {pages_str}\n"
    
    response += f"\n💡 **Note**: This is a fallback response. LLM synthesis failed.\n"
    
    return response


def detect_query_intent(query: str) -> str:
    """Detect if query is asking for overview/summary."""
    query_lower = query.lower()
    
    overview_keywords = [
        'what is this about', 'summarize', 'summary', 'overview',
        'main contribution', 'key contribution', 'what does this',
        'tell me about', 'describe this', 'explain this thesis',
        'what is the research', 'research about'
    ]
    
    for keyword in overview_keywords:
        if keyword in query_lower:
            return 'overview'
    
    return 'specific'


def get_high_priority_chunks() -> List[dict]:
    """Get Abstract/Introduction chunks for overview questions."""
    high_priority = []
    
    for idx, chunk in enumerate(chunks_store):
        if chunk.get('chunk_type') == 'high_priority_content':
            if idx < len(chunk_embeddings):
                high_priority.append({
                    "content": chunk['content'],
                    "score": 1.0,  # Max score for forced inclusion
                    "metadata": {
                        "document_id": chunk['document_id'],
                        "document_name": chunk['document_name'],
                        "page_number": chunk['page_number'],
                        "position_on_page": chunk.get('position_on_page', 'unknown'),
                        "chunk_index": chunk['chunk_index'],
                        "char_length": chunk['char_length'],
                        "chunk_type": chunk.get('chunk_type', 'content')
                    }
                })
    
    return high_priority[:3]  # Top 3 high-priority chunks


def _generate_fallback_response(query, context_parts, page_refs, query_enhancement):
    """Generate response without LLM (fallback)."""
    query_type = query_enhancement['query_type']
    
    if query_type == "explanation":
        response = f"**Understanding: {query}**\n\n"
        response += "Based on the document analysis:\n\n"
    elif query_type == "how-to":
        response += f"**How to: {query}**\n\n"
        response += "Here are the steps/process found:\n\n"
    elif query_type == "enumeration":
        response = f"**List: {query}**\n\n"
        response += "Found the following items:\n\n"
    else:
        response = f"**Answer: {query}**\n\n"
    
    # Add context
    for idx, part in enumerate(context_parts, 1):
        response += f"{part}\n\n"
    
    # Add page summary
    response += "\n" + "─" * 60 + "\n\n"
    if len(page_refs) == 1:
        doc, page = list(page_refs)[0]
        response += f"📄 **Source**: {doc}, Page {page}\n"
    else:
        response += f"📄 **Sources**: Found across {len(page_refs)} pages:\n"
        for doc, page in sorted(page_refs, key=lambda x: x[1]):
            response += f"   • {doc}, Page {page}\n"
    
    response += f"\n💡 **Tip**: Open your PDF for complete details.\n"
    
    return response


@app.post("/api/v1/search/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Search documents with SEMANTIC SEARCH using embeddings."""
    try:
        session_id = request.session_id or "default"
        
        # Get chat history for context
        context_history = get_chat_history(session_id, limit=5) if request.use_chat_history else []
        
        # Enhance the user's raw query
        query_enhancement = enhance_user_prompt(request.query, context_history)
        enhanced_query = query_enhancement['enhanced']
        
        # Save user query to history
        save_to_chat_history(session_id, "user", request.query, query_enhancement)
        
        # Detect query intent (overview vs specific)
        intent = detect_query_intent(request.query)
        
        # SEMANTIC SEARCH using embeddings
        print(f"🔍 Semantic search for: {request.query}")
        print(f"📋 Intent: {intent}")
        
        if intent == 'overview':
            # For overview questions, prioritize Abstract/Introduction
            high_priority = get_high_priority_chunks()
            semantic_results = semantic_search(request.query, top_k=request.top_k - len(high_priority))
            
            # Combine: high priority first, then semantic results
            results = high_priority + semantic_results
            print(f"✅ Retrieved {len(high_priority)} high-priority + {len(semantic_results)} semantic chunks")
        else:
            # Regular semantic search, exclude front-matter and references
            results = semantic_search(request.query, top_k=request.top_k, exclude_types=['front_matter', 'references'])
            print(f"✅ Retrieved {len(results)} chunks via semantic search")
        
        # Deduplicate by chunk_index
        seen_indices = set()
        deduped_results = []
        for result in results:
            idx = result['metadata']['chunk_index']
            if idx not in seen_indices:
                seen_indices.add(idx)
                deduped_results.append(result)
        
        results = deduped_results[:request.top_k]
        
        # Log retrieved chunk types for debugging
        chunk_types_retrieved = [r['metadata'].get('chunk_type', 'unknown') for r in results]
        print(f"📊 Chunk types retrieved: {chunk_types_retrieved}")
        
        # Format results for response
        top_results = results
        
        # Generate context-aware response with page citations
        response_text = None
        if top_results:
            # Build context with page numbers
            context_parts = []
            page_refs = set()
            
            for idx, result in enumerate(top_results[:3], 1):
                page_num = result['metadata']['page_number']
                position = result['metadata']['position_on_page']
                doc_name = result['metadata']['document_name']
                content_preview = result['content'][:400] + "..." if len(result['content']) > 400 else result['content']
                
                context_parts.append(
                    f"[Source {idx}: {doc_name}, Page {page_num} ({position})]\n{content_preview}"
                )
                page_refs.add((doc_name, page_num))
            
            # Build context for LLM
            context_for_llm = "\n\n".join([result['content'] for result in top_results[:3]])
            
            print(f"🤖 Calling LLM synthesis...")
            print(f"📝 Context length: {len(context_for_llm)} chars")
            
            # Use LLM to generate answer - ALWAYS synthesize, no score threshold
            try:
                import google.generativeai as genai
                import os
                from dotenv import load_dotenv
                
                # Load environment
                load_dotenv()
                
                # Configure Gemini
                api_key = os.getenv('GEMINI_API_KEY')
                print(f"🔑 API key present: {bool(api_key)}")
                
                if api_key:
                    genai.configure(api_key=api_key)
                    
                    # Create prompt for LLM
                    # System prompt following your exact specification
                    system_prompt = """You are DocuMind, a research assistant that answers questions using ONLY the provided document excerpts.

Rules:

1. Never output raw chunks, source labels, or "[Source N]" — synthesize a single coherent answer.

2. Write in complete sentences. Never end mid-word or mid-clause.

3. Match answer length to available information:
   - If context is thin (1 short excerpt, tangential to the query), give a brief 2-4 sentence answer and say plainly that the document doesn't cover this in depth.
   - If context is rich (multiple relevant excerpts), give a fuller answer with structure: a short intro sentence, then 2-4 bullet points for key facts, then a closing sentence if needed.

4. Use **bold** only for genuinely key terms (names, numbers, technical terms) — not every noun.

5. Do not invent information not present in the excerpts. If the excerpts don't answer the question, say so directly instead of padding.

6. Do not mention "chunks," "sources," or "excerpts" in the answer text itself — write as if you simply know the document. Citations are added separately after your answer, not by you."""
                    
                    # Query-type specific formatting guidance
                    query_type = query_enhancement['query_type']
                    formatting_hint = ""
                    
                    if query_type == "explanation":
                        formatting_hint = "\nFormat your answer with: **Title**, then clear explanation with key highlights."
                    elif query_type == "how-to":
                        formatting_hint = "\nFormat your answer with: step-by-step instructions or process description."
                    elif query_type == "enumeration":
                        formatting_hint = "\nFormat your answer with: bullet points (•) or numbered list."
                    elif query_type == "reasoning":
                        formatting_hint = "\nFormat your answer with: clear explanation of reasons/causes."
                    else:
                        formatting_hint = "\nFormat your answer with: clear structure, bold emphasis for key terms."
                    
                    # Format prompt exactly as specified
                    user_prompt = f"""Document excerpts:

{context_for_llm}

Question: {request.query}

{formatting_hint}"""
                    
                    # Generate response with optimized settings for synthesis
                    model = genai.GenerativeModel(
                        model_name='gemini-1.5-flash',
                        generation_config={
                            "temperature": 0.3,  # Lower for factual accuracy, minimal creativity
                            "top_p": 0.9,        # Focused sampling
                            "top_k": 30,         # More deterministic
                            "max_output_tokens": 1024,  # Concise but complete answers
                        },
                        system_instruction=system_prompt
                    )
                    
                    llm_response = model.generate_content(user_prompt)
                    llm_answer = llm_response.text.strip()
                    
                    print(f"✅ LLM response received: {len(llm_answer)} chars")
                    
                    # Build final response with clean structure
                    response_text = llm_answer
                    
                    # Add source section at the bottom
                    response_text += "\n\n" + "─" * 60 + "\n"
                    response_text += "**📚 Sources**\n"
                    response_text += "─" * 60 + "\n\n"
                    
                    # Format sources clearly
                    if len(page_refs) == 1:
                        doc, page = list(page_refs)[0]
                        response_text += f"📄 {doc} - Page {page}\n"
                    else:
                        unique_pages = sorted(set(page for doc, page in page_refs))
                        doc_name = list(page_refs)[0][0]
                        if len(unique_pages) <= 3:
                            pages_str = ", ".join(str(p) for p in unique_pages)
                            response_text += f"📄 {doc_name} - Pages {pages_str}\n"
                        else:
                            response_text += f"📄 {doc_name} - Found across {len(unique_pages)} pages\n"
                    
                else:
                    # Fallback if no API key
                    print("⚠️ No API key - using fallback")
                    response_text = _generate_fallback_response(
                        request.query, context_parts, page_refs, query_enhancement
                    )
                    
            except Exception as e:
                print(f"❌ LLM generation error: {e}")
                import traceback
                traceback.print_exc()
                # Fallback to non-LLM response
                response_text = _generate_fallback_response(
                    request.query, context_parts, page_refs, query_enhancement
                )
            
        else:
            response_text = f"**No results found for**: {request.query}\n\n"
            response_text += "**Suggestions**:\n"
            response_text += "• Try different keywords\n"
            response_text += "• Use more specific terms\n"
            response_text += "• Check if your documents contain this information\n"
            
            if query_enhancement['key_terms']:
                response_text += f"\n🔍 I searched for: {', '.join(query_enhancement['key_terms'])}\n"
        
        # Save assistant response to history
        save_to_chat_history(session_id, "assistant", response_text)
        
        return QueryResponse(
            query=request.query,
            enhanced_query=enhanced_query,
            results=top_results,
            response=response_text,
            total_results=len(results),
            chat_history_used=request.use_chat_history and len(context_history) > 0
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_with_documents(request: ChatRequest):
    """
    Chat with your documents using LLM-powered responses.
    Maintains conversation history for context-aware responses.
    """
    try:
        # Generate or use existing session ID
        session_id = request.session_id or str(uuid.uuid4())
        
        # Initialize session if new
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        
        # Add user message to history
        user_message = ChatMessage(
            role="user",
            content=request.message,
            timestamp=datetime.now().isoformat()
        )
        chat_sessions[session_id].append(user_message)
        
        # Search for relevant chunks
        query_lower = request.message.lower()
        relevant_chunks = []
        
        for chunk in chunks_store:
            content_lower = chunk['content'].lower()
            query_words = query_lower.split()
            content_words = content_lower.split()
            
            # Calculate relevance
            score = 0.0
            if query_lower in content_lower:
                score = 0.95
            else:
                matching_words = sum(1 for word in query_words if word in content_words)
                if matching_words > 0:
                    score = (matching_words / len(query_words)) * 0.8
            
            if score > 0:
                relevant_chunks.append({
                    "content": chunk['content'],
                    "score": score,
                    "page": chunk['page_number'],
                    "doc_name": chunk['document_name'],
                    "position": chunk.get('position_on_page', 'unknown')
                })
        
        # Sort by score and get top K
        relevant_chunks.sort(key=lambda x: x['score'], reverse=True)
        top_chunks = relevant_chunks[:request.top_k]
        
        # Generate LLM response
        if llm_model and top_chunks:
            # Build context from retrieved chunks
            context = "\n\n".join([
                f"[Page {c['page']}, {c['doc_name']}]\n{c['content']}"
                for c in top_chunks[:3]
            ])
            
            # Build conversation history for context
            history_context = ""
            if request.use_history and len(chat_sessions[session_id]) > 1:
                recent_history = chat_sessions[session_id][-6:-1]  # Last 3 exchanges
                history_context = "\n\nPrevious conversation:\n"
                for msg in recent_history:
                    history_context += f"{msg.role.upper()}: {msg.content}\n"
            
            # Create prompt using DocuMind system prompt
            system_instruction = """You are DocuMind, a research assistant that answers questions using ONLY the provided document excerpts.

Rules:

1. Never output raw chunks, source labels, or "[Source N]" — synthesize a single coherent answer.

2. Write in complete sentences. Never end mid-word or mid-clause.

3. Match answer length to available information:
   - If context is thin (1 short excerpt, tangential to the query), give a brief 2-4 sentence answer and say plainly that the document doesn't cover this in depth.
   - If context is rich (multiple relevant excerpts), give a fuller answer with structure: a short intro sentence, then 2-4 bullet points for key facts, then a closing sentence if needed.

4. Use **bold** only for genuinely key terms (names, numbers, technical terms) — not every noun.

5. Do not invent information not present in the excerpts. If the excerpts don't answer the question, say so directly instead of padding.

6. Do not mention "chunks," "sources," or "excerpts" in the answer text itself — write as if you simply know the document. Citations are added separately after your answer, not by you."""
            
            prompt = f"""Document excerpts:

{context}
{history_context}

Question: {request.message}

Provide a clear, well-structured answer based on the document information."""
            
            try:
                chat_model = genai.GenerativeModel(
                    model_name='gemini-1.5-flash',
                    generation_config={
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "top_k": 30,
                        "max_output_tokens": 1024,
                    },
                    system_instruction=system_instruction
                )
                response = chat_model.generate_content(prompt)
                assistant_response = response.text
            except Exception as e:
                print(f"LLM generation error: {e}")
                # Fallback response
                assistant_response = f"Based on the documents:\n\n{top_chunks[0]['content'][:300]}...\n\nSource: {top_chunks[0]['doc_name']}, Page {top_chunks[0]['page']}"
        
        elif top_chunks:
            # Simple response without LLM
            assistant_response = f"I found relevant information in your documents:\n\n"
            for idx, chunk in enumerate(top_chunks[:2], 1):
                assistant_response += f"{idx}. [{chunk['doc_name']}, Page {chunk['page']}]\n"
                assistant_response += f"{chunk['content'][:200]}...\n\n"
        else:
            assistant_response = "I couldn't find relevant information in your uploaded documents to answer this question. Could you try rephrasing or asking something else?"
        
        # Add assistant response to history
        assistant_message = ChatMessage(
            role="assistant",
            content=assistant_response,
            timestamp=datetime.now().isoformat()
        )
        chat_sessions[session_id].append(assistant_message)
        
        # Prepare sources for response
        sources = [
            {
                "document_name": c['doc_name'],
                "page_number": c['page'],
                "position": c['position'],
                "score": c['score'],
                "preview": c['content'][:150] + "..."
            }
            for c in top_chunks
        ]
        
        return ChatResponse(
            response=assistant_response,
            session_id=session_id,
            sources=sources,
            conversation_history=chat_sessions[session_id]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/chat/sessions")
async def list_chat_sessions():
    """List all active chat sessions."""
    return {
        "sessions": [
            {
                "session_id": sid,
                "message_count": len(messages),
                "last_message": messages[-1].timestamp if messages else None
            }
            for sid, messages in chat_sessions.items()
        ]
    }


@app.delete("/api/v1/chat/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session and its history."""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        return {"status": "success", "message": "Chat session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/api/v1/documents")
async def list_documents():
    """List all uploaded documents."""
    return {
        "documents": documents,
        "total": len(documents)
    }


@app.get("/api/v1/ocr/status")
async def ocr_status():
    """Get OCR system status and capabilities."""
    ocr_info = {
        "unlimited_ocr_available": UNLIMITED_OCR_AVAILABLE,
        "pytorch_available": False,
        "transformers_available": False,
        "device": "cpu"
    }
    
    # Check dependencies
    try:
        import torch
        ocr_info["pytorch_available"] = True
        ocr_info["device"] = "cuda" if torch.cuda.is_available() else "cpu"
        ocr_info["torch_version"] = torch.__version__
    except ImportError:
        pass
    
    try:
        import transformers
        ocr_info["transformers_available"] = True
        ocr_info["transformers_version"] = transformers.__version__
    except ImportError:
        pass
    
    if UNLIMITED_OCR_AVAILABLE:
        try:
            # Check if model can be initialized
            if hasattr(unlimited_ocr_service, 'model_name'):
                ocr_info["model_name"] = unlimited_ocr_service.model_name
                ocr_info["model_device"] = unlimited_ocr_service.device
        except Exception as e:
            ocr_info["model_error"] = str(e)
    
    return {
        "status": "operational" if UNLIMITED_OCR_AVAILABLE else "fallback",
        "ocr_engine": "Baidu Unlimited-OCR" if UNLIMITED_OCR_AVAILABLE else "PyMuPDF Basic",
        "capabilities": {
            "scanned_pdf_detection": UNLIMITED_OCR_AVAILABLE,
            "advanced_ocr": UNLIMITED_OCR_AVAILABLE,
            "intelligent_extraction": UNLIMITED_OCR_AVAILABLE,
            "multi_page_parsing": UNLIMITED_OCR_AVAILABLE,
            "image_processing": UNLIMITED_OCR_AVAILABLE
        },
        "system_info": ocr_info,
        "description": "Advanced OCR with Baidu Unlimited-OCR for superior document parsing" if UNLIMITED_OCR_AVAILABLE else "Basic text extraction using PyMuPDF"
    }


@app.post("/api/v1/ocr/test")
async def test_ocr_extraction(file: UploadFile = File(...)):
    """Test OCR extraction on a single document (demo endpoint)."""
    try:
        if not file.filename.endswith(('.pdf', '.png', '.jpg', '.jpeg')):
            raise HTTPException(
                status_code=400, 
                detail="Supported formats: PDF, PNG, JPG, JPEG"
            )
        
        content = await file.read()
        
        # Save temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename[-4:]) as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        extraction_results = {
            "filename": file.filename,
            "file_size": len(content),
            "extraction_methods": {}
        }
        
        try:
            if file.filename.endswith('.pdf'):
                # Test PDF extraction
                if UNLIMITED_OCR_AVAILABLE:
                    # Test intelligent extraction
                    start_time = datetime.now()
                    ocr_text = unlimited_ocr_service.intelligent_extract(tmp_file_path)
                    ocr_duration = (datetime.now() - start_time).total_seconds()
                    
                    extraction_results["extraction_methods"]["unlimited_ocr"] = {
                        "text_length": len(ocr_text),
                        "extraction_time": ocr_duration,
                        "preview": ocr_text[:500] + "..." if len(ocr_text) > 500 else ocr_text,
                        "method": "Unlimited-OCR (Intelligent)"
                    }
                    
                    # Test scanned detection
                    is_scanned = unlimited_ocr_service.is_scanned_pdf(tmp_file_path)
                    extraction_results["pdf_analysis"] = {
                        "appears_scanned": is_scanned,
                        "recommended_method": "OCR" if is_scanned else "PyMuPDF + OCR fallback"
                    }
                
                # Also test PyMuPDF for comparison
                start_time = datetime.now()
                pdf_doc = pymupdf.open(stream=content, filetype="pdf")
                basic_text = ""
                for page in pdf_doc:
                    basic_text += page.get_text()
                pdf_doc.close()
                basic_duration = (datetime.now() - start_time).total_seconds()
                
                extraction_results["extraction_methods"]["pymupdf_basic"] = {
                    "text_length": len(basic_text),
                    "extraction_time": basic_duration,
                    "preview": basic_text[:500] + "..." if len(basic_text) > 500 else basic_text,
                    "method": "PyMuPDF (Basic)"
                }
            
            elif file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                # Test image OCR
                if UNLIMITED_OCR_AVAILABLE:
                    start_time = datetime.now()
                    ocr_text = unlimited_ocr_service.extract_text_from_image(
                        tmp_file_path,
                        mode="gundam",  # Best for single images
                        prompt="Extract all text from this image."
                    )
                    ocr_duration = (datetime.now() - start_time).total_seconds()
                    
                    extraction_results["extraction_methods"]["unlimited_ocr_image"] = {
                        "text_length": len(ocr_text),
                        "extraction_time": ocr_duration,
                        "preview": ocr_text[:500] + "..." if len(ocr_text) > 500 else ocr_text,
                        "method": "Unlimited-OCR (Image Mode)"
                    }
                else:
                    extraction_results["extraction_methods"]["no_image_ocr"] = {
                        "error": "Image OCR requires Unlimited-OCR dependencies",
                        "fallback": "Upload as PDF for basic text extraction"
                    }
        
        finally:
            # Clean up
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        
        # Performance comparison
        if len(extraction_results["extraction_methods"]) > 1:
            methods = extraction_results["extraction_methods"]
            fastest_method = min(
                methods.keys(),
                key=lambda k: methods[k].get("extraction_time", float('inf'))
            )
            most_text = max(
                methods.keys(),
                key=lambda k: methods[k].get("text_length", 0)
            )
            
            extraction_results["comparison"] = {
                "fastest_extraction": fastest_method,
                "most_comprehensive": most_text,
                "methods_tested": len(methods)
            }
        
        return {
            "status": "success",
            "message": "OCR extraction test completed",
            "results": extraction_results,
            "recommendations": {
                "for_scanned_pdfs": "Use Unlimited-OCR for best accuracy",
                "for_native_pdfs": "PyMuPDF is faster, OCR provides better completeness",
                "for_images": "Unlimited-OCR required for text extraction"
            }
        }
        
    except Exception as e:
        # Clean up on error
        try:
            if 'tmp_file_path' in locals():
                os.unlink(tmp_file_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"OCR test failed: {str(e)}")


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
