"""Text processing utilities for chunking and similarity."""

import numpy as np
from typing import List, Dict, Any
import spacy
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Load spaCy model (lazy loading)
_nlp = None


def get_nlp():
    """Get or load spaCy model."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load(settings.spacy_model)
            logger.info(f"Loaded spaCy model: {settings.spacy_model}")
        except OSError:
            logger.warning(
                f"spaCy model '{settings.spacy_model}' not found. "
                f"Run: python -m spacy download {settings.spacy_model}"
            )
            # Fallback to basic sentence splitting
            _nlp = None
    return _nlp


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Properties:
    - Commutative: cosine_similarity(v1, v2) == cosine_similarity(v2, v1)
    - Range: [-1.0, 1.0]
    - 1.0 = identical direction
    - 0.0 = orthogonal
    - -1.0 = opposite direction
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Cosine similarity score
        
    Raises:
        ValueError: If vectors have different dimensions or are zero vectors
    """
    # Validate inputs
    if vec1.shape != vec2.shape:
        raise ValueError(
            f"Vectors must have same shape: {vec1.shape} vs {vec2.shape}"
        )
    
    # Convert to numpy arrays if needed
    vec1 = np.asarray(vec1, dtype=np.float64)
    vec2 = np.asarray(vec2, dtype=np.float64)
    
    # Calculate norms
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    # Check for zero vectors
    if norm1 == 0 or norm2 == 0:
        raise ValueError("Cannot compute similarity for zero vector")
    
    # Compute cosine similarity
    dot_product = np.dot(vec1, vec2)
    similarity = dot_product / (norm1 * norm2)
    
    # Clamp to valid range due to floating point errors
    similarity = np.clip(similarity, -1.0, 1.0)
    
    return float(similarity)


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using spaCy.
    
    Args:
        text: Input text
        
    Returns:
        List of sentences
    """
    if not text or not text.strip():
        return []
    
    nlp = get_nlp()
    
    if nlp is None:
        # Fallback: simple sentence splitting
        import re
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    # Use spaCy for proper sentence segmentation
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    
    return sentences


def count_tokens(text: str) -> int:
    """
    Estimate token count for text.
    
    Uses simple heuristic: ~1.3 tokens per word for English.
    For production, use actual tokenizer (tiktoken, transformers).
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    words = text.split()
    return int(len(words) * 1.3)


class SemanticChunker:
    """
    Semantic chunking using sentence-level similarity.
    
    Algorithm:
    1. Split text into sentences
    2. Generate embeddings for each sentence
    3. Calculate cosine similarity between adjacent sentences
    4. Group sentences with similarity > threshold
    5. Respect max_chunk_size constraint
    """
    
    def __init__(
        self,
        gemini_client,
        similarity_threshold: float = None,
        max_chunk_size: int = None
    ):
        """
        Initialize semantic chunker.
        
        Args:
            gemini_client: Gemini client for embeddings
            similarity_threshold: Minimum similarity for grouping
            max_chunk_size: Maximum tokens per chunk
        """
        self.gemini_client = gemini_client
        self.similarity_threshold = similarity_threshold or settings.similarity_threshold
        self.max_chunk_size = max_chunk_size or settings.max_chunk_size
        
        # Validate parameters
        if not 0.0 <= self.similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        if self.max_chunk_size <= 0:
            raise ValueError("max_chunk_size must be positive")
    
    def chunk_text(
        self,
        text: str,
        page_number: int,
        document_id: str
    ) -> List[Dict[str, Any]]:
        """
        Chunk text using semantic similarity.
        
        Args:
            text: Input text
            page_number: Page number for citation
            document_id: Document UUID
            
        Returns:
            List of chunk dictionaries
        """
        if not text or not text.strip():
            return []
        
        # Split into sentences
        sentences = split_into_sentences(text)
        
        if not sentences:
            return []
        
        # Single sentence - return as single chunk if within size
        if len(sentences) == 1:
            token_count = count_tokens(sentences[0])
            if token_count <= self.max_chunk_size:
                return [{
                    "content": sentences[0],
                    "page_number": page_number,
                    "token_count": token_count,
                }]
            else:
                # Split long sentence by words
                return self._split_long_sentence(
                    sentences[0],
                    page_number
                )
        
        # Generate embeddings for sentences
        try:
            embeddings = self.gemini_client.embed_batch(sentences)
        except Exception as e:
            logger.error(f"Failed to generate embeddings for chunking: {e}")
            # Fallback: simple chunking by token count
            return self._fallback_chunk_by_tokens(text, page_number)
        
        # Group sentences by similarity
        chunks = self._group_sentences_by_similarity(
            sentences,
            embeddings,
            page_number
        )
        
        return chunks
    
    def _group_sentences_by_similarity(
        self,
        sentences: List[str],
        embeddings: List[List[float]],
        page_number: int
    ) -> List[Dict[str, Any]]:
        """
        Group sentences into chunks based on similarity.
        
        Args:
            sentences: List of sentences
            embeddings: Sentence embeddings
            page_number: Page number
            
        Returns:
            List of chunks
        """
        chunks = []
        current_chunk_sentences = [sentences[0]]
        current_chunk_tokens = count_tokens(sentences[0])
        
        for i in range(1, len(sentences)):
            sentence = sentences[i]
            sentence_tokens = count_tokens(sentence)
            
            # Calculate similarity with previous sentence
            similarity = cosine_similarity(
                np.array(embeddings[i - 1]),
                np.array(embeddings[i])
            )
            
            # Check if we should add to current chunk
            would_exceed_size = (
                current_chunk_tokens + sentence_tokens > self.max_chunk_size
            )
            is_similar = similarity >= self.similarity_threshold
            
            if is_similar and not would_exceed_size:
                # Add to current chunk
                current_chunk_sentences.append(sentence)
                current_chunk_tokens += sentence_tokens
            else:
                # Finalize current chunk and start new one
                chunk_text = " ".join(current_chunk_sentences)
                chunks.append({
                    "content": chunk_text,
                    "page_number": page_number,
                    "token_count": current_chunk_tokens,
                })
                
                current_chunk_sentences = [sentence]
                current_chunk_tokens = sentence_tokens
        
        # Add final chunk
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences)
            chunks.append({
                "content": chunk_text,
                "page_number": page_number,
                "token_count": current_chunk_tokens,
            })
        
        logger.info(f"Created {len(chunks)} semantic chunks from {len(sentences)} sentences")
        return chunks
    
    def _split_long_sentence(
        self,
        sentence: str,
        page_number: int
    ) -> List[Dict[str, Any]]:
        """
        Split long sentence into chunks by words.
        
        Args:
            sentence: Long sentence
            page_number: Page number
            
        Returns:
            List of chunks
        """
        words = sentence.split()
        chunks = []
        current_words = []
        current_tokens = 0
        
        for word in words:
            word_tokens = count_tokens(word)
            
            if current_tokens + word_tokens > self.max_chunk_size:
                if current_words:
                    chunk_text = " ".join(current_words)
                    chunks.append({
                        "content": chunk_text,
                        "page_number": page_number,
                        "token_count": current_tokens,
                    })
                current_words = [word]
                current_tokens = word_tokens
            else:
                current_words.append(word)
                current_tokens += word_tokens
        
        if current_words:
            chunk_text = " ".join(current_words)
            chunks.append({
                "content": chunk_text,
                "page_number": page_number,
                "token_count": current_tokens,
            })
        
        return chunks
    
    def _fallback_chunk_by_tokens(
        self,
        text: str,
        page_number: int
    ) -> List[Dict[str, Any]]:
        """
        Fallback chunking by token count when embeddings fail.
        
        Args:
            text: Input text
            page_number: Page number
            
        Returns:
            List of chunks
        """
        words = text.split()
        chunks = []
        current_words = []
        current_tokens = 0
        
        for word in words:
            word_tokens = count_tokens(word)
            
            if current_tokens + word_tokens > self.max_chunk_size:
                if current_words:
                    chunk_text = " ".join(current_words)
                    chunks.append({
                        "content": chunk_text,
                        "page_number": page_number,
                        "token_count": current_tokens,
                    })
                current_words = [word]
                current_tokens = word_tokens
            else:
                current_words.append(word)
                current_tokens += word_tokens
        
        if current_words:
            chunk_text = " ".join(current_words)
            chunks.append({
                "content": chunk_text,
                "page_number": page_number,
                "token_count": current_tokens,
            })
        
        logger.warning(f"Used fallback chunking, created {len(chunks)} chunks")
        return chunks
