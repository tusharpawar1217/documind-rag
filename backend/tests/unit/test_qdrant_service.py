"""Unit tests for Qdrant service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.qdrant_client import QdrantService
from app.models import DocumentChunk


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client."""
    with patch("app.services.qdrant_client.QdrantClient") as mock:
        yield mock


@pytest.fixture
def qdrant_service(mock_qdrant_client):
    """Create Qdrant service with mocked client."""
    service = QdrantService()
    return service


def test_initialize_collection_creates_new(qdrant_service, mock_qdrant_client):
    """Test collection creation when it doesn't exist."""
    # Mock empty collections list
    mock_collections = Mock()
    mock_collections.collections = []
    qdrant_service.client.get_collections.return_value = mock_collections
    
    # Initialize collection
    result = qdrant_service.initialize_collection()
    
    assert result is True
    qdrant_service.client.create_collection.assert_called_once()
    assert qdrant_service.client.create_payload_index.call_count == 4


def test_initialize_collection_already_exists(qdrant_service):
    """Test collection initialization when it already exists."""
    # Mock existing collection
    mock_collection = Mock()
    mock_collection.name = "documind"
    mock_collections = Mock()
    mock_collections.collections = [mock_collection]
    qdrant_service.client.get_collections.return_value = mock_collections
    
    result = qdrant_service.initialize_collection()
    
    assert result is True
    qdrant_service.client.create_collection.assert_not_called()


def test_upsert_chunks_validates_embeddings(qdrant_service):
    """Test that chunks without embeddings are rejected."""
    chunk = DocumentChunk(
        document_id="doc-123",
        content="Test content",
        chunk_type="text",
        page_number=1,
        chunk_index=0,
        embedding=None  # Missing embedding
    )
    
    with pytest.raises(ValueError, match="missing embedding"):
        qdrant_service.upsert_chunks([chunk])


def test_upsert_chunks_success(qdrant_service):
    """Test successful chunk upsertion."""
    chunk = DocumentChunk(
        document_id="doc-123",
        content="Test content",
        chunk_type="text",
        page_number=1,
        chunk_index=0,
        embedding=[0.1] * 768
    )
    
    result = qdrant_service.upsert_chunks([chunk], user_id="user-1")
    
    assert result is True
    qdrant_service.client.upsert.assert_called_once()


def test_search_with_filters(qdrant_service):
    """Test search with document and user filters."""
    query_vector = [0.1] * 768
    
    # Mock search results
    mock_hit = Mock()
    mock_hit.id = "chunk-1"
    mock_hit.score = 0.95
    mock_hit.payload = {
        "document_id": "doc-123",
        "content": "Test content",
        "chunk_type": "text",
        "page_number": 1,
        "metadata": {}
    }
    qdrant_service.client.search.return_value = [mock_hit]
    
    results = qdrant_service.search(
        query_vector=query_vector,
        limit=5,
        document_ids=["doc-123"],
        user_id="user-1"
    )
    
    assert len(results) == 1
    assert results[0].chunk_id == "chunk-1"
    assert results[0].relevance_score == 0.95


def test_delete_by_document_id(qdrant_service):
    """Test deletion of chunks by document ID."""
    result = qdrant_service.delete_by_document_id("doc-123")
    
    assert result is True
    qdrant_service.client.delete.assert_called_once()


def test_health_check_success(qdrant_service):
    """Test health check when Qdrant is accessible."""
    qdrant_service.client.get_collections.return_value = Mock()
    
    result = qdrant_service.health_check()
    
    assert result is True


def test_health_check_failure(qdrant_service):
    """Test health check when Qdrant is inaccessible."""
    qdrant_service.client.get_collections.side_effect = Exception("Connection error")
    
    result = qdrant_service.health_check()
    
    assert result is False


def test_upsert_empty_chunks_list(qdrant_service):
    """Test upserting empty list does nothing."""
    result = qdrant_service.upsert_chunks([])
    
    assert result is True
    qdrant_service.client.upsert.assert_not_called()
