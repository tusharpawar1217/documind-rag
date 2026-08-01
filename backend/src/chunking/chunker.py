"""
Text Chunking - Split text into small, semantically meaningful chunks.

This module handles splitting long documents into smaller chunks suitable for embedding and retrieval.
"""

from typing import List, Dict, Any
import re
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

CHUNK_SIZE = config['chunking']['chunk_size']
CHUNK_OVERLAP = config['chunking']['chunk_overlap']
MIN_CHUNK_SIZE = config['chunking']['min_chunk_size']
MAX_CHUNK_SIZE = config['chunking']['max_chunk_size']


class TextChunker:
    """
    Basic text chunker with fixed size and overlap.
    
    Splits text into chunks of approximately equal size with overlap between chunks
    to maintain context across boundaries.
    """
    
    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
        min_chunk_size: int = MIN_CHUNK_SIZE
    ):
        """
        Initialize text chunker.
        
        Args:
            chunk_size: Target size for each chunk (in characters)
            chunk_overlap: Number of overlapping characters between chunks
            min_chunk_size: Minimum chunk size to keep
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_text(
        self,
        text: str,
        page_number: int = 1,
        document_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks.
        
        Args:
            text: Input text to chunk
            page_number: Page number for metadata
            document_id: Document ID for metadata
            
        Returns:
            List of chunk dictionaries with content and metadata
        """
        # Clean text
        text = self._clean_text(text)
        
        if len(text) < self.min_chunk_size:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Find end position
            end = start + self.chunk_size
            
            # If not at document end, try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings within overlap range
                search_start = max(start, end - self.chunk_overlap)
                sentence_end = self._find_sentence_boundary(text, search_start, end + self.chunk_overlap)
                if sentence_end:
                    end = sentence_end
            
            chunk_text = text[start:end].strip()
            
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append({
                    "content": chunk_text,
                    "page_number": page_number,
                    "chunk_type": "text",
                    "token_count": self._count_tokens(chunk_text),
                    "metadata": {
                        "document_id": document_id,
                        "start_char": start,
                        "end_char": end,
                    }
                })
            
            # Move to next chunk with overlap
            start = end - self.chunk_overlap
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might interfere
        text = text.strip()
        return text
    
    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """Find the nearest sentence boundary."""
        # Look for sentence endings: . ! ?
        sentence_endings = ['.', '!', '?']
        
        # Search backwards from end
        for i in range(end - 1, start, -1):
            if text[i] in sentence_endings:
                # Check if followed by space or end
                if i + 1 >= len(text) or text[i + 1].isspace():
                    return i + 1
        
        return None
    
    def _count_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        # Rough estimate: 1 token ~= 4 characters
        return len(text) // 4


class SemanticChunker:
    """
    Advanced semantic chunker.
    
    Uses embeddings and similarity to create semantically coherent chunks.
    Falls back to TextChunker for basic splitting.
    """
    
    def __init__(self, embedder=None):
        """
        Initialize semantic chunker.
        
        Args:
            embedder: Embeddings client (optional, for semantic splitting)
        """
        self.embedder = embedder
        self.text_chunker = TextChunker()
        self.similarity_threshold = config['chunking'].get('similarity_threshold', 0.7)
    
    def chunk_text(
        self,
        text: str,
        page_number: int = 1,
        document_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Split text into semantically coherent chunks.
        
        If embedder is not available, falls back to basic text chunking.
        
        Args:
            text: Input text
            page_number: Page number
            document_id: Document ID
            
        Returns:
            List of chunks
        """
        # For now, use basic text chunking
        # TODO: Implement semantic chunking with embeddings
        return self.text_chunker.chunk_text(text, page_number, document_id)
    
    def _split_by_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitter
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _merge_similar_sentences(self, sentences: List[str]) -> List[str]:
        """Merge sentences that are semantically similar."""
        if not self.embedder or len(sentences) < 2:
            return sentences
        
        # TODO: Implement semantic merging using embeddings
        return sentences


# Global chunker instances
text_chunker = TextChunker()
semantic_chunker = SemanticChunker()
