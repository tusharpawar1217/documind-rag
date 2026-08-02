"""
In-Memory Vector Store - Simple vector store for testing without Qdrant.

This is a temporary implementation to test the system without external dependencies.
"""

from typing import List, Dict, Optional
import numpy as np


class InMemoryVectorStore:
    """Simple in-memory vector store using numpy for similarity search."""
    
    def __init__(self):
        """Initialize empty store."""
        self.vectors = []
        self.payloads = []
        self.ids = []
    
    def upsert(self, vectors: List[List[float]], payloads: List[Dict], ids: List[str]) -> bool:
        """
        Insert or update vectors.
        
        Args:
            vectors: List of embedding vectors
            payloads: List of metadata dictionaries
            ids: List of unique IDs
            
        Returns:
            True if successful
        """
        for vector, payload, doc_id in zip(vectors, payloads, ids):
            if doc_id in self.ids:
                # Update existing
                idx = self.ids.index(doc_id)
                self.vectors[idx] = vector
                self.payloads[idx] = payload
            else:
                # Insert new
                self.vectors.append(vector)
                self.payloads.append(payload)
                self.ids.append(doc_id)
        return True
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar vectors using cosine similarity.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filters
            
        Returns:
            List of search results with scores and payloads
        """
        if not self.vectors:
            return []
        
        # Convert to numpy arrays
        query = np.array(query_vector)
        vectors = np.array(self.vectors)
        
        # Calculate cosine similarity
        query_norm = query / np.linalg.norm(query)
        vectors_norm = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        similarities = np.dot(vectors_norm, query_norm)
        
        # Apply filters
        valid_indices = list(range(len(self.vectors)))
        if filter_dict:
            valid_indices = [
                i for i in valid_indices
                if all(self.payloads[i].get(k) == v for k, v in filter_dict.items())
            ]
        
        # Get top-k results
        filtered_similarities = [(i, similarities[i]) for i in valid_indices]
        filtered_similarities.sort(key=lambda x: x[1], reverse=True)
        top_results = filtered_similarities[:top_k]
        
        return [
            {
                "id": self.ids[idx],
                "score": float(score),
                "payload": self.payloads[idx]
            }
            for idx, score in top_results
        ]
    
    def delete(self, ids: List[str]) -> bool:
        """Delete vectors by IDs."""
        for doc_id in ids:
            if doc_id in self.ids:
                idx = self.ids.index(doc_id)
                del self.vectors[idx]
                del self.payloads[idx]
                del self.ids[idx]
        return True
    
    def delete_by_filter(self, filter_dict: Dict) -> bool:
        """Delete vectors matching filter."""
        to_delete = [
            self.ids[i]
            for i in range(len(self.ids))
            if all(self.payloads[i].get(k) == v for k, v in filter_dict.items())
        ]
        return self.delete(to_delete)
    
    def count(self) -> int:
        """Get total number of vectors."""
        return len(self.vectors)


# Global in-memory store instance
in_memory_store = InMemoryVectorStore()
