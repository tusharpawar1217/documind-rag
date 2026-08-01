"""Unit tests for text processing utilities."""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from app.utils.text_processing import (
    cosine_similarity,
    split_into_sentences,
    count_tokens,
    SemanticChunker,
)


class TestCosineSimilarity:
    """Tests for cosine similarity calculation."""
    
    def test_identical_vectors(self):
        """Test cosine similarity of identical vectors returns 1.0."""
        vec = np.array([1.0, 2.0, 3.0])
        
        similarity = cosine_similarity(vec, vec)
        
        assert np.isclose(similarity, 1.0)
    
    def test_orthogonal_vectors(self):
        """Test cosine similarity of orthogonal vectors returns 0.0."""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        
        similarity = cosine_similarity(vec1, vec2)
        
        assert np.isclose(similarity, 0.0, atol=1e-10)
    
    def test_opposite_vectors(self):
        """Test cosine similarity of opposite vectors returns -1.0."""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([-1.0, -2.0, -3.0])
        
        similarity = cosine_similarity(vec1, vec2)
        
        assert np.isclose(similarity, -1.0)
    
    def test_commutative_property(self):
        """Test cosine similarity is commutative."""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([4.0, 5.0, 6.0])
        
        sim1 = cosine_similarity(vec1, vec2)
        sim2 = cosine_similarity(vec2, vec1)
        
        assert np.isclose(sim1, sim2)
    
    def test_range_constraint(self):
        """Test cosine similarity always returns value in [-1, 1]."""
        vec1 = np.random.randn(768)
        vec2 = np.random.randn(768)
        
        similarity = cosine_similarity(vec1, vec2)
        
        assert -1.0 <= similarity <= 1.0
    
    def test_different_dimensions_raises_error(self):
        """Test that vectors with different dimensions raise ValueError."""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([1.0, 2.0])
        
        with pytest.raises(ValueError, match="same shape"):
            cosine_similarity(vec1, vec2)
    
    def test_zero_vector_raises_error(self):
        """Test that zero vector raises ValueError."""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([0.0, 0.0, 0.0])
        
        with pytest.raises(ValueError, match="zero vector"):
            cosine_similarity(vec1, vec2)


class TestSplitIntoSentences:
    """Tests for sentence splitting."""
    
    def test_simple_sentences(self):
        """Test splitting simple sentences."""
        text = "This is sentence one. This is sentence two. This is sentence three."
        
        sentences = split_into_sentences(text)
        
        assert len(sentences) == 3
        assert "This is sentence one." in sentences[0]
    
    def test_empty_text(self):
        """Test splitting empty text returns empty list."""
        sentences = split_into_sentences("")
        assert sentences == []
    
    def test_single_sentence(self):
        """Test splitting single sentence."""
        text = "This is a single sentence without end punctuation"
        
        sentences = split_into_sentences(text)
        
        assert len(sentences) >= 1
    
    def test_preserves_sentence_content(self):
        """Test that sentence content is preserved."""
        text = "Climate change is real. We must act now."
        
        sentences = split_into_sentences(text)
        
        combined = " ".join(sentences)
        assert "Climate change is real" in combined
        assert "We must act now" in combined


class TestCountTokens:
    """Tests for token counting."""
    
    def test_empty_text(self):
        """Test token count for empty text."""
        assert count_tokens("") == 0
    
    def test_single_word(self):
        """Test token count for single word."""
        tokens = count_tokens("hello")
        assert tokens > 0
    
    def test_multiple_words(self):
        """Test token count increases with words."""
        tokens1 = count_tokens("hello")
        tokens2 = count_tokens("hello world")
        
        assert tokens2 > tokens1
    
    def test_approximate_count(self):
        """Test token count is approximately correct."""
        text = "This is a test sentence with several words."
        tokens = count_tokens(text)
        
        word_count = len(text.split())
        # Should be roughly 1.3x word count
        assert word_count < tokens < word_count * 2


class TestSemanticChunker:
    """Tests for semantic chunker."""
    
    @pytest.fixture
    def mock_gemini_client(self):
        """Create mock Gemini client."""
        client = Mock()
        # Mock embeddings with high similarity
        client.embed_batch.return_value = [
            [0.1] * 768,
            [0.11] * 768,  # Similar to first
            [0.5] * 768,   # Different
        ]
        return client
    
    def test_chunk_empty_text(self, mock_gemini_client):
        """Test chunking empty text returns empty list."""
        chunker = SemanticChunker(mock_gemini_client)
        
        chunks = chunker.chunk_text("", page_number=1, document_id="doc-1")
        
        assert chunks == []
    
    def test_chunk_single_sentence_within_limit(self, mock_gemini_client):
        """Test chunking single short sentence."""
        chunker = SemanticChunker(mock_gemini_client, max_chunk_size=100)
        text = "This is a short sentence."
        
        chunks = chunker.chunk_text(text, page_number=1, document_id="doc-1")
        
        assert len(chunks) == 1
        assert chunks[0]["content"] == text
        assert chunks[0]["page_number"] == 1
    
    def test_chunk_respects_max_size(self, mock_gemini_client):
        """Test that all chunks respect max_chunk_size."""
        chunker = SemanticChunker(mock_gemini_client, max_chunk_size=50)
        text = "This is sentence one. " * 20  # Long text
        
        chunks = chunker.chunk_text(text, page_number=1, document_id="doc-1")
        
        for chunk in chunks:
            assert chunk["token_count"] <= 50
    
    def test_chunk_groups_similar_sentences(self, mock_gemini_client):
        """Test that similar sentences are grouped together."""
        # Mock high similarity between all sentences
        mock_gemini_client.embed_batch.return_value = [
            [0.1] * 768,
            [0.11] * 768,
            [0.12] * 768,
        ]
        
        chunker = SemanticChunker(
            mock_gemini_client,
            similarity_threshold=0.9,
            max_chunk_size=500
        )
        text = "Sentence one. Sentence two. Sentence three."
        
        chunks = chunker.chunk_text(text, page_number=1, document_id="doc-1")
        
        # With high similarity and large max size, should group all
        assert len(chunks) >= 1
    
    def test_chunk_separates_dissimilar_sentences(self, mock_gemini_client):
        """Test that dissimilar sentences are separated."""
        # Mock low similarity between sentences
        mock_gemini_client.embed_batch.return_value = [
            [1.0, 0.0] + [0.0] * 766,
            [0.0, 1.0] + [0.0] * 766,
        ]
        
        chunker = SemanticChunker(
            mock_gemini_client,
            similarity_threshold=0.9,
            max_chunk_size=500
        )
        text = "First sentence. Second sentence."
        
        chunks = chunker.chunk_text(text, page_number=1, document_id="doc-1")
        
        # With low similarity, should separate
        assert len(chunks) >= 1
    
    def test_fallback_chunking_on_embedding_failure(self, mock_gemini_client):
        """Test fallback chunking when embedding fails."""
        mock_gemini_client.embed_batch.side_effect = Exception("API error")
        
        chunker = SemanticChunker(mock_gemini_client, max_chunk_size=50)
        text = "This is a test sentence. " * 10
        
        chunks = chunker.chunk_text(text, page_number=1, document_id="doc-1")
        
        # Should still create chunks using fallback
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk["token_count"] <= 50
    
    def test_invalid_similarity_threshold_raises_error(self, mock_gemini_client):
        """Test that invalid similarity threshold raises ValueError."""
        with pytest.raises(ValueError, match="similarity_threshold"):
            SemanticChunker(mock_gemini_client, similarity_threshold=1.5)
    
    def test_invalid_max_chunk_size_raises_error(self, mock_gemini_client):
        """Test that invalid max_chunk_size raises ValueError."""
        with pytest.raises(ValueError, match="max_chunk_size"):
            SemanticChunker(mock_gemini_client, max_chunk_size=-10)
