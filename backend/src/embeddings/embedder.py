"""
Embeddings - Convert text chunks into vector embeddings.

This module handles converting text into dense vector representations for semantic search.
"""

from typing import List
import os
import yaml
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

EMBEDDING_MODEL = config['embeddings']['model']
EMBEDDING_DIMENSION = config['embeddings']['dimension']
BATCH_SIZE = config['embeddings']['batch_size']


class Embedder:
    """Base embedder class."""
    
    def embed_text(self, text: str) -> List[float]:
        """
        Convert single text to embedding.
        
        Args:
            text: Input text
            
        Returns:
            List of floats representing the embedding vector
        """
        raise NotImplementedError
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Convert multiple texts to embeddings.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        raise NotImplementedError


class GeminiEmbedder(Embedder):
    """
    Gemini embeddings using Google's Generative AI.
    
    Uses Gemini embedding models to convert text into 768-dimensional vectors.
    """
    
    def __init__(self):
        """Initialize Gemini embedder."""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        self.model = EMBEDDING_MODEL
        self.dimension = EMBEDDING_DIMENSION
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for single text.
        
        Args:
            text: Input text (max 2048 tokens)
            
        Returns:
            768-dimensional embedding vector
        """
        if not text or not text.strip():
            return [0.0] * self.dimension
        
        result = genai.embed_content(
            model=self.model,
            content=text,
            task_type="retrieval_document"
        )
        
        return result['embedding']
    
    def embed_batch(self, texts: List[str], batch_size: int = BATCH_SIZE) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of input texts
            batch_size: Number of texts per batch
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Filter empty texts
            valid_texts = [t if t and t.strip() else " " for t in batch]
            
            try:
                result = genai.embed_content(
                    model=self.model,
                    content=valid_texts,
                    task_type="retrieval_document"
                )
                
                # Handle both single and batch responses
                if isinstance(result['embedding'][0], list):
                    embeddings.extend(result['embedding'])
                else:
                    embeddings.append(result['embedding'])
                    
            except Exception as e:
                print(f"Error embedding batch: {e}")
                # Fallback: embed individually
                for text in batch:
                    try:
                        embeddings.append(self.embed_text(text))
                    except:
                        embeddings.append([0.0] * self.dimension)
        
        return embeddings
    
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for search query.
        
        Args:
            query: Search query text
            
        Returns:
            Embedding vector optimized for retrieval
        """
        if not query or not query.strip():
            return [0.0] * self.dimension
        
        result = genai.embed_content(
            model=self.model,
            content=query,
            task_type="retrieval_query"
        )
        
        return result['embedding']


# Global embedder instance
embedder = GeminiEmbedder()
