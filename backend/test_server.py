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

# Load environment variables
load_dotenv()

# Initialize Gemini for LLM responses
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    llm_model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini LLM initialized")
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
chat_history = []  # Store conversation history
chat_sessions = {}  # Store chat history per session


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
            
            # IMPROVED CHUNKING: Recursive Character Text Splitter approach
            # Try to split at natural boundaries with overlap
            
            # First, try paragraph boundaries
            raw_paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
            
            paragraphs = []
            chunk_size = 800  # Target chunk size in characters
            chunk_overlap = 150  # Overlap between chunks for context continuity
            
            if raw_paragraphs:
                # Process each paragraph
                for para in raw_paragraphs:
                    # If paragraph is small enough, keep it as is
                    if len(para) <= chunk_size:
                        if len(para) > 100:  # Only keep substantial paragraphs
                            paragraphs.append(para)
                    else:
                        # Split large paragraph by sentences
                        # Split on multiple sentence endings
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
            
            # If still no good chunks, fall back to simple word-based splitting
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
    """Search documents with chat history, prompt enhancement, and page-level accuracy."""
    try:
        session_id = request.session_id or "default"
        
        # Get chat history for context
        context_history = get_chat_history(session_id, limit=5) if request.use_chat_history else []
        
        # Enhance the user's raw query
        query_enhancement = enhance_user_prompt(request.query, context_history)
        enhanced_query = query_enhancement['enhanced']
        search_keywords = query_enhancement['search_keywords']
        
        # Save user query to history
        save_to_chat_history(session_id, "user", request.query, query_enhancement)
        
        # Search using enhanced keywords
        query_lower = search_keywords.lower()
        
        # Enhanced keyword search with relevance scoring
        results = []
        for chunk in chunks_store:
            content_lower = chunk['content'].lower()
            
            # Calculate relevance score
            score = 0.0
            key_terms = query_enhancement['key_terms']
            content_words = content_lower.split()
            
            # Exact phrase match (highest score)
            if query_lower in content_lower or request.query.lower() in content_lower:
                score = 0.95
            else:
                # Key term matching
                matching_terms = sum(1 for term in key_terms if term in content_words)
                if matching_terms > 0:
                    score = (matching_terms / len(key_terms)) * 0.85
                
                # Boost score if multiple terms appear close together
                for term in key_terms:
                    if term in content_lower:
                        score += 0.05
            
            if score > 0:
                results.append({
                    "content": chunk['content'],
                    "score": min(score, 1.0),  # Cap at 1.0
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
            
            # Use LLM to generate answer
            try:
                import google.generativeai as genai
                import os
                from dotenv import load_dotenv
                
                # Load environment
                load_dotenv()
                
                # Configure Gemini
                api_key = os.getenv('GEMINI_API_KEY')
                if api_key:
                    genai.configure(api_key=api_key)
                    
                    # Create prompt for LLM
                    # System prompt following your exact specification
                    system_prompt = """You are DocuMind, an AI document assistant.

Task: Synthesize a clear, coherent, and well-structured answer to the user's query based strictly on the provided context chunks.

Rules:
- Do NOT output raw chunks or snippet headers directly.
- Formulate complete, professional sentences and rephrase where necessary.
- If key details are cut off in the context, synthesize what is available.
- Use proper formatting: **bold** for emphasis, bullet points for lists, clear paragraphs
- Reference page numbers naturally when relevant (e.g., "The methodology on page 5...")
- Never say "based on the context" - it's implied
- Be direct, professional, and well-structured
- Use section headers when appropriate (e.g., **Overview**, **Key Highlights**)
- If listing items, use bullet points (•) or numbered lists
- Keep paragraphs concise (2-4 sentences)
- Never fabricate information beyond the provided context"""
                    
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
                    user_prompt = f"""User Query: {request.query}

Retrieved Context:
{context_for_llm}

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
                    response_text = _generate_fallback_response(
                        request.query, context_parts, page_refs, query_enhancement
                    )
                    
            except Exception as e:
                print(f"LLM generation error: {e}")
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
            system_instruction = """You are DocuMind, an AI document assistant.

Task: Synthesize a clear, coherent, and well-structured answer to the user's query based strictly on the provided context chunks.

Rules:
- Do NOT output raw chunks or snippet headers directly.
- Formulate complete, professional sentences and rephrase where necessary.
- If key details are cut off in the context, synthesize what is available.
- Use proper formatting: **bold** for emphasis, bullet points for lists
- Reference page numbers naturally (e.g., "The methodology on page 5...")
- Never say "based on the context"
- Be conversational and natural
- If this is a follow-up question, consider the conversation history"""
            
            prompt = f"""User Query: {request.message}

Retrieved Context:
{context}
{history_context}

Format your answer clearly with structure, bold emphasis for key terms."""
            
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


@app.get("/api/v1/documents/stats")
async def get_statistics():
    """Get document and chat statistics."""
    total_size = sum(doc['size'] for doc in documents)
    total_chunks = len(chunks_store)
    total_chats = len(chat_history)
    unique_sessions = len(set(msg.get('session_id', 'default') for msg in chat_history))
    
    return {
        "total_documents": len(documents),
        "total_chunks": total_chunks,
        "total_size": total_size,
        "total_conversations": total_chats,
        "active_sessions": unique_sessions
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
