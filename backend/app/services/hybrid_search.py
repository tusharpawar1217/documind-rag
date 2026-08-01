"""Hybrid search engine combining semantic search, BM25, and reranking."""

from typing import List, Optional, Dict, Any
from sentence_transformers import CrossEncoder
import numpy as np

from app.models import SearchResult
from app.services.qdrant_client import qdrant_service
from app.services.gemini_client import gemini_client
from app.utils.bm25 import bm25_scorer
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class HybridSearchEngine:
    """
    Hybrid search combining semantic similarity, BM25, and cross-encoder reranking.
    
    Pipeline:
    1. Semantic search in Qdrant (top-k=20)
    2. BM25 keyword filtering
    3. Score combination (70% semantic, 30% BM25)
    4. Cross-encoder reranking
    5. Final score: 50% rerank, 30% semantic, 20% BM25
    6. Deduplication by page number
    """
    
    def __init__(self):
        """Initialize hybrid search engine."""
        self.qdrant_service = qdrant_service
        self.gemini_client = gemini_client
        self.bm25_scorer = bm25_scorer
        
        # Load cross-encoder for reranking
        try:
            self.reranker = CrossEncoder(settings.reranker_model)
            logger.info(f"Loaded reranker model: {settings.reranker_model}")
        except Exception as e:
            logger.error(f"Failed to load reranker model: {e}")
            self.reranker = None
    
    def search(
        self,
        query: str,
        top_k: int = None,
        rerank_top_n: int = None,
        document_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Perform hybrid search with reranking.
        
        Args:
            query: User query string
            top_k: Number of results from initial search
            rerank_top_n: Number of results after reranking
            document_ids: Filter by specific documents
            user_id: Filter by user ownership
            
        Returns:
            Ranked list of search results with citations
        """
        if top_k is None:
            top_k = settings.top_k_search
        if rerank_top_n is None:
            rerank_top_n = settings.rerank_top_n
        
        logger.info(f"Executing hybrid search for query (top_k={top_k}, rerank={rerank_top_n})")
        
        # Step 1: Generate query embedding
        try:
            query_embedding = self.gemini_client.embed_text(query)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return []
        
        # Step 2: Semantic search in Qdrant
        semantic_results = self.qdrant_service.search(
            query_vector=query_embedding,
            limit=top_k,
            document_ids=document_ids,
            user_id=user_id,
        )
        
        if not semantic_results:
            logger.info("No semantic search results found")
            return []
        
        logger.info(f"Found {len(semantic_results)} semantic search results")
        
        # Step 3: Apply BM25 keyword filtering
        results_with_bm25 = self._apply_bm25_scoring(query, semantic_results)
        
        # Step 4: Combine scores (70% semantic, 30% BM25)
        for result in results_with_bm25:
            result.final_score = (
                0.7 * result.relevance_score +
                0.3 * result.bm25_score
            )
        
        # Sort by combined score
        results_with_bm25.sort(key=lambda r: r.final_score, reverse=True)
        
        # Take top candidates for reranking (2x for better coverage)
        candidates = results_with_bm25[:rerank_top_n * 2]
        
        # Step 5: Rerank using cross-encoder
        if self.reranker:
            reranked_results = self._rerank_results(query, candidates)
        else:
            logger.warning("Reranker not available, skipping reranking step")
            reranked_results = candidates
        
        # Step 6: Deduplicate by page number
        final_results = self._deduplicate_by_page(reranked_results, rerank_top_n)
        
        logger.info(f"Returning {len(final_results)} final results after deduplication")
        return final_results
    
    def _apply_bm25_scoring(
        self,
        query: str,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Apply BM25 keyword scoring to search results.
        
        Args:
            query: User query
            results: Semantic search results
            
        Returns:
            Results with BM25 scores added
        """
        query_tokens = self.bm25_scorer.tokenize(query)
        
        for result in results:
            doc_tokens = self.bm25_scorer.tokenize(result.content)
            bm25_score = self.bm25_scorer.score(
                query_tokens,
                doc_tokens,
                doc_length=len(doc_tokens)
            )
            
            # Normalize BM25 score to [0, 1]
            result.bm25_score = self.bm25_scorer.normalize_score(bm25_score)
        
        return results
    
    def _rerank_results(
        self,
        query: str,
        candidates: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Rerank results using cross-encoder model.
        
        Args:
            query: User query
            candidates: Candidate results
            
        Returns:
            Reranked results
        """
        if not candidates:
            return []
        
        try:
            # Prepare query-document pairs
            pairs = [(query, result.content) for result in candidates]
            
            # Get rerank scores
            rerank_scores = self.reranker.predict(pairs)
            
            # Update results with rerank scores and final combined scores
            for result, rerank_score in zip(candidates, rerank_scores):
                result.rerank_score = float(rerank_score)
                
                # Final score: 50% rerank, 30% semantic, 20% BM25
                result.final_score = (
                    0.5 * result.rerank_score +
                    0.3 * result.relevance_score +
                    0.2 * result.bm25_score
                )
            
            # Sort by final score
            candidates.sort(key=lambda r: r.final_score, reverse=True)
            
            logger.info("Reranking completed successfully")
            return candidates
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return candidates
    
    def _deduplicate_by_page(
        self,
        results: List[SearchResult],
        limit: int
    ) -> List[SearchResult]:
        """
        Remove duplicate pages, keeping highest scoring instance.
        
        Args:
            results: Search results
            limit: Maximum number of results
            
        Returns:
            Deduplicated results
        """
        seen_pages = set()
        deduplicated = []
        
        for result in results:
            page_key = (result.document_id, result.page_number)
            
            if page_key not in seen_pages:
                seen_pages.add(page_key)
                deduplicated.append(result)
                
                if len(deduplicated) >= limit:
                    break
        
        logger.info(
            f"Deduplicated from {len(results)} to {len(deduplicated)} results"
        )
        return deduplicated
    
    def validate_results_ordering(self, results: List[SearchResult]) -> bool:
        """
        Validate that results are properly ordered by descending score.
        
        Args:
            results: Search results
            
        Returns:
            True if properly ordered
        """
        for i in range(len(results) - 1):
            if results[i].final_score < results[i + 1].final_score:
                logger.warning(
                    f"Results not properly ordered at index {i}: "
                    f"{results[i].final_score} < {results[i + 1].final_score}"
                )
                return False
        return True


# Global hybrid search engine instance
hybrid_search_engine = HybridSearchEngine()
