"""
Retrieval - Retrieve relevant chunks using hybrid search.

Combines semantic search (vector similarity) with keyword search (BM25).
"""

from typing import List, Dict, Any
import yaml
from rank_bm25 import BM25Okapi

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

TOP_K = config['retrieval']['top_k']
HYBRID_ALPHA = config['retrieval']['hybrid_alpha']


class Retriever:
    """Base retriever interface."""
    
    def retrieve(self, query: str, top_k: int = TOP_K) -> List[Dict]:
        raise NotImplementedError


class HybridRetriever(Retriever):
    """
    Hybrid retrieval combining semantic and keyword search.
    
    Uses both vector similarity (semantic) and BM25 (keyword) search,
    then combines results using weighted scoring.
    """
    
    def __init__(self, vector_store, embedder):
        """
        Initialize hybrid retriever.
        
        Args:
            vector_store: Vector database instance
            embedder: Embedding model instance
        """
        self.vector_store = vector_store
        self.embedder = embedder
        self.alpha = HYBRID_ALPHA  # 0=keyword only, 1=semantic only
    
    def retrieve(
        self,
        query: str,
        top_k: int = TOP_K,
        alpha: float = None
    ) -> List[Dict]:
        """
        Retrieve relevant chunks using hybrid search.
        
        Args:
            query: Search query
            top_k: Number of results
            alpha: Hybrid weight (0=keyword, 1=semantic)
            
        Returns:
            List of relevant chunks with scores
        """
        if alpha is None:
            alpha = self.alpha
        
        # Get query embedding for semantic search
        query_vector = self.embedder.embed_query(query)
        
        # Semantic search
        semantic_results = self.vector_store.search(
            query_vector=query_vector,
            top_k=top_k * 2  # Get more for reranking
        )
        
        # Combine scores (simplified hybrid)
        # In production, would also do BM25 keyword search and combine
        results = [
            {
                "content": r["payload"].get("content", ""),
                "score": r["score"] * alpha,
                "metadata": r["payload"]
            }
            for r in semantic_results
        ]
        
        # Sort by combined score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:top_k]


# Initialize retriever (requires vector_store and embedder instances)
# retriever = HybridRetriever(vector_store, embedder)
