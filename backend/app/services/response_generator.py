"""Response generation with precise page citations."""

import re
import time
from typing import List, Dict, Any
from app.models import SearchResult, Citation, QueryResponse
from app.services.gemini_client import gemini_client
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ResponseGenerator:
    """
    Generate answers with precise page citations.
    
    Process:
    1. Build context prompt with page references
    2. Generate answer using Gemini LLM
    3. Extract page citations from answer
    4. Validate citations against context
    5. Calculate confidence score
    6. Format response
    """
    
    def __init__(self):
        """Initialize response generator."""
        self.gemini_client = gemini_client
    
    def generate_answer(
        self,
        query: str,
        search_results: List[SearchResult]
    ) -> QueryResponse:
        """
        Generate answer with citations.
        
        Args:
            query: User query
            search_results: Retrieved and ranked search results
            
        Returns:
            Complete query response with citations
        """
        start_time = time.time()
        
        # Handle no results case
        if not search_results:
            return QueryResponse(
                answer="No relevant information found in the indexed documents. "
                       "Please try rephrasing your query or check if the relevant documents are uploaded.",
                citations=[],
                confidence=0.0,
                processing_time=(time.time() - start_time) * 1000,
                sources_used=0
            )
        
        # Step 1: Build context prompt
        prompt, page_map = self._build_context_prompt(query, search_results)
        
        # Step 2: Generate answer
        try:
            answer_text = self.gemini_client.generate_answer(
                prompt,
                temperature=0.7,
                max_tokens=1024
            )
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return QueryResponse(
                answer="Failed to generate answer. Please try again.",
                citations=[],
                confidence=0.0,
                processing_time=(time.time() - start_time) * 1000,
                sources_used=0
            )
        
        # Step 3: Extract citations
        cited_pages = self._extract_citations(answer_text)
        
        # Step 4: Validate and build citation objects
        citations = self._build_citations(cited_pages, search_results, page_map)
        
        # Step 5: Calculate confidence
        confidence = self._calculate_confidence(answer_text, search_results, citations)
        
        # Step 6: Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # milliseconds
        
        logger.info(
            f"Generated answer with {len(citations)} citations, "
            f"confidence {confidence:.2f}, time {processing_time:.0f}ms"
        )
        
        return QueryResponse(
            answer=answer_text,
            citations=citations,
            confidence=confidence,
            processing_time=processing_time,
            sources_used=len(search_results)
        )
    
    def _build_context_prompt(
        self,
        query: str,
        search_results: List[SearchResult]
    ) -> tuple[str, Dict[int, SearchResult]]:
        """
        Build context prompt with page references.
        
        Args:
            query: User query
            search_results: Search results
            
        Returns:
            Tuple of (prompt, page_mapping)
        """
        # Build page mapping
        page_map = {}
        context_parts = []
        
        for result in search_results:
            page_num = result.page_number
            page_map[page_num] = result
            
            # Format context item
            context_parts.append(
                f"[Page {page_num}]\n"
                f"Document: {result.metadata.get('document_name', 'Unknown')}\n"
                f"Content: {result.content}\n"
            )
        
        context_text = "\n\n".join(context_parts)
        
        # Build complete prompt
        prompt = f"""You are a helpful assistant that answers questions based on provided context from documents.

IMPORTANT INSTRUCTIONS:
1. Answer the question accurately using ONLY the information from the context provided below
2. ALWAYS cite your sources using [Page X] notation where X is the page number
3. Use multiple citations when information comes from different pages
4. If the context doesn't contain enough information to answer fully, say so
5. Be concise but comprehensive
6. Do not make up information not present in the context

CONTEXT FROM DOCUMENTS:
{context_text}

QUESTION: {query}

ANSWER (remember to cite pages using [Page X]):"""
        
        return prompt, page_map
    
    def _extract_citations(self, answer_text: str) -> List[int]:
        """
        Extract page numbers from citation patterns.
        
        Args:
            answer_text: Generated answer
            
        Returns:
            List of unique page numbers
        """
        # Pattern: [Page X] or [Page X, Y] or [Pages X-Y]
        patterns = [
            r'\[Page (\d+)\]',
            r'\[page (\d+)\]',
            r'page (\d+)',
        ]
        
        cited_pages = set()
        
        for pattern in patterns:
            matches = re.findall(pattern, answer_text, re.IGNORECASE)
            for match in matches:
                try:
                    page_num = int(match)
                    cited_pages.add(page_num)
                except ValueError:
                    continue
        
        return sorted(list(cited_pages))
    
    def _build_citations(
        self,
        cited_pages: List[int],
        search_results: List[SearchResult],
        page_map: Dict[int, SearchResult]
    ) -> List[Citation]:
        """
        Build citation objects with validation.
        
        Args:
            cited_pages: Extracted page numbers
            search_results: Search results
            page_map: Page number to result mapping
            
        Returns:
            List of validated citations
        """
        citations = []
        
        for page_num in cited_pages:
            # Validate page exists in context
            if page_num not in page_map:
                logger.warning(
                    f"Citation [Page {page_num}] not found in context, skipping"
                )
                continue
            
            result = page_map[page_num]
            
            # Create citation
            citation = Citation(
                page_number=page_num,
                document_id=result.document_id,
                document_name=result.metadata.get('document_name', 'Unknown'),
                content=result.content[:200],  # Truncated snippet
                relevance_score=result.final_score
            )
            citations.append(citation)
        
        # Sort by page number
        citations.sort(key=lambda c: c.page_number)
        
        return citations
    
    def _calculate_confidence(
        self,
        answer: str,
        search_results: List[SearchResult],
        citations: List[Citation]
    ) -> float:
        """
        Calculate confidence score based on context quality.
        
        Factors:
        - Average relevance score of context (40% weight)
        - Source diversity (30% weight)
        - Answer substantiality (30% weight)
        
        Args:
            answer: Generated answer
            search_results: Search results used
            citations: Extracted citations
            
        Returns:
            Confidence score in [0.0, 1.0]
        """
        if not search_results:
            return 0.0
        
        # Factor 1: Average relevance score (40% weight)
        avg_relevance = sum(r.final_score for r in search_results) / len(search_results)
        relevance_component = avg_relevance * 0.4
        
        # Factor 2: Source diversity (30% weight)
        unique_docs = len(set(r.document_id for r in search_results))
        diversity_score = min(unique_docs / 3.0, 1.0)  # Max at 3 documents
        diversity_component = diversity_score * 0.3
        
        # Factor 3: Answer substantiality (30% weight)
        answer_words = len(answer.split())
        substantiality = min(answer_words / 100.0, 1.0)  # Max at 100 words
        substantiality_component = substantiality * 0.3
        
        # Combine components
        confidence = (
            relevance_component +
            diversity_component +
            substantiality_component
        )
        
        # Penalty if no citations found
        if not citations:
            confidence *= 0.5
        
        # Clamp to [0, 1]
        confidence = max(0.0, min(1.0, confidence))
        
        return round(confidence, 3)
    
    def validate_citations(
        self,
        citations: List[Citation],
        search_results: List[SearchResult]
    ) -> bool:
        """
        Validate that all citations reference pages in context.
        
        Args:
            citations: Extracted citations
            search_results: Search results (context)
            
        Returns:
            True if all citations are valid
        """
        context_pages = {r.page_number for r in search_results}
        cited_pages = {c.page_number for c in citations}
        
        # Check if all cited pages exist in context
        invalid_citations = cited_pages - context_pages
        
        if invalid_citations:
            logger.warning(
                f"Found invalid citations: {invalid_citations} "
                f"not in context pages: {context_pages}"
            )
            return False
        
        return True


# Global response generator instance
response_generator = ResponseGenerator()
