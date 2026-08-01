"""Qdrant vector database client."""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
)
from qdrant_client.http.exceptions import UnexpectedResponse
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models import DocumentChunk, SearchResult

logger = get_logger(__name__)


class QdrantService:
    """
    Service for interacting with Qdrant vector database.
    
    Handles:
    - Collection creation and management
    - Vector storage and retrieval
    - Similarity search
    - Metadata filtering
    """
    
    def __init__(self):
        """Initialize Qdrant client with connection pooling."""
        try:
            self.client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key,
                timeout=30,
            )
            self.collection_name = settings.qdrant_collection_name
            logger.info(f"Connected to Qdrant at {settings.qdrant_host}:{settings.qdrant_port}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
    
    def initialize_collection(self) -> bool:
        """
        Create Qdrant collection if it doesn't exist.
        
        Configuration:
        - Vector dimension: 768 (Gemini embeddings)
        - Distance metric: Cosine
        - HNSW index for fast approximate search
        
        Returns:
            True if collection exists or was created successfully
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name in collection_names:
                logger.info(f"Collection '{self.collection_name}' already exists")
                return True
            
            # Create collection with HNSW index
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE,
                ),
                hnsw_config={
                    "ef_construct": settings.hnsw_ef_construct,
                    "m": settings.hnsw_m,
                },
            )
            
            # Create payload indexes for efficient filtering
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="document_id",
                field_schema="keyword",
            )
            
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="page_number",
                field_schema="integer",
            )
            
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="chunk_type",
                field_schema="keyword",
            )
            
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="user_id",
                field_schema="keyword",
            )
            
            logger.info(f"Created collection '{self.collection_name}' with indexes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise
    
    def upsert_chunks(self, chunks: List[DocumentChunk], user_id: Optional[str] = None) -> bool:
        """
        Store document chunks with embeddings in Qdrant.
        
        Args:
            chunks: List of document chunks with embeddings
            user_id: User ID for access control
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If chunks don't have embeddings
            Exception: If upsert fails
        """
        if not chunks:
            logger.warning("No chunks to upsert")
            return True
        
        # Validate all chunks have embeddings
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.chunk_id} missing embedding")
        
        try:
            points = []
            for chunk in chunks:
                payload = {
                    "content": chunk.content,
                    "document_id": chunk.document_id,
                    "page_number": chunk.page_number,
                    "chunk_type": chunk.chunk_type,
                    "chunk_index": chunk.chunk_index,
                    "token_count": chunk.token_count,
                    "metadata": chunk.metadata,
                    "created_at": chunk.created_at.isoformat(),
                }
                
                if user_id:
                    payload["user_id"] = user_id
                
                points.append(
                    PointStruct(
                        id=chunk.chunk_id,
                        vector=chunk.embedding,
                        payload=payload,
                    )
                )
            
            # Upsert in batches to handle large document sets
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                )
            
            logger.info(f"Upserted {len(chunks)} chunks to Qdrant")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert chunks: {e}")
            raise
    
    def search(
        self,
        query_vector: List[float],
        limit: int = 20,
        document_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Perform semantic similarity search.
        
        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            document_ids: Filter by specific documents
            user_id: Filter by user ownership
            
        Returns:
            List of search results with scores
        """
        try:
            # Build filter conditions
            filter_conditions = []
            
            if document_ids:
                filter_conditions.append(
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(any=document_ids),
                    )
                )
            
            if user_id:
                filter_conditions.append(
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id),
                    )
                )
            
            search_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            # Perform search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit,
                with_payload=True,
            )
            
            # Convert to SearchResult objects
            results = []
            for hit in search_results:
                results.append(
                    SearchResult(
                        chunk_id=str(hit.id),
                        document_id=hit.payload["document_id"],
                        content=hit.payload["content"],
                        chunk_type=hit.payload["chunk_type"],
                        page_number=hit.payload["page_number"],
                        relevance_score=hit.score,
                        final_score=hit.score,  # Will be updated by hybrid search
                        metadata=hit.payload.get("metadata", {}),
                    )
                )
            
            logger.info(f"Found {len(results)} results for query")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def delete_by_document_id(self, document_id: str) -> bool:
        """
        Delete all chunks for a document.
        
        Args:
            document_id: Document UUID
            
        Returns:
            True if successful
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                ),
            )
            logger.info(f"Deleted chunks for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete chunks for document {document_id}: {e}")
            raise
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Dictionary with collection info
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": info.config.name,
                "vector_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "status": info.status,
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise
    
    def health_check(self) -> bool:
        """
        Check if Qdrant is healthy and accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            collections = self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False


# Global Qdrant service instance
qdrant_service = QdrantService()
