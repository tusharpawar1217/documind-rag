"""
Vector Database - Handle vector database operations with Qdrant.

This module manages storing and retrieving vector embeddings for semantic search.
"""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

QDRANT_HOST = config['vectordb']['host']
QDRANT_PORT = config['vectordb']['port']
COLLECTION_NAME = config['vectordb']['collection_name']
VECTOR_SIZE = config['embeddings']['dimension']


class VectorStore:
    """Base vector store interface."""
    
    def upsert(self, vectors: List[List[float]], payloads: List[Dict], ids: List[str]) -> bool:
        raise NotImplementedError
    
    def search(self, query_vector: List[float], top_k: int = 5, filter_dict: Dict = None) -> List[Dict]:
        raise NotImplementedError
    
    def delete(self, ids: List[str]) -> bool:
        raise NotImplementedError


class QdrantVectorStore(VectorStore):
    """Qdrant vector database implementation."""
    
    def __init__(self):
        """Initialize Qdrant client and ensure collection exists."""
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.collection_name = COLLECTION_NAME
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
            )
    
    def upsert(self, vectors: List[List[float]], payloads: List[Dict], ids: List[str]) -> bool:
        """
        Insert or update vectors in Qdrant.
        
        Args:
            vectors: List of embedding vectors
            payloads: List of metadata dictionaries
            ids: List of unique IDs
            
        Returns:
            True if successful
        """
        points = [
            PointStruct(id=idx, vector=vector, payload=payload)
            for idx, (vector, payload) in enumerate(zip(vectors, payloads))
        ]
        
        self.client.upsert(collection_name=self.collection_name, points=points)
        return True
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filters
            
        Returns:
            List of search results with scores and payloads
        """
        search_filter = None
        if filter_dict:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_dict.items()
            ]
            search_filter = Filter(must=conditions)
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=search_filter
        )
        
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload
            }
            for hit in results
        ]
    
    def delete(self, ids: List[str]) -> bool:
        """Delete vectors by IDs."""
        self.client.delete(collection_name=self.collection_name, points_selector=ids)
        return True
    
    def delete_by_filter(self, filter_dict: Dict) -> bool:
        """Delete vectors matching filter."""
        conditions = [
            FieldCondition(key=k, match=MatchValue(value=v))
            for k, v in filter_dict.items()
        ]
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(must=conditions)
        )
        return True


# Global vector store instance
vector_store = QdrantVectorStore()
