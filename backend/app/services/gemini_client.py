"""Gemini API client for embeddings, vision, and text generation."""

import time
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import numpy as np

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class GeminiClient:
    """
    Client for Google Gemini API.
    
    Provides:
    - Text embeddings (text-embedding-004, 768 dimensions)
    - Vision API for table and image extraction
    - Text generation (gemini-pro)
    - Retry logic with exponential backoff
    """
    
    def __init__(self):
        """Initialize Gemini client with API key."""
        try:
            genai.configure(api_key=settings.gemini_api_key)
            
            # Initialize models
            self.embedding_model = "models/text-embedding-004"
            self.vision_model = genai.GenerativeModel("gemini-pro-vision")
            self.text_model = genai.GenerativeModel(
                "gemini-pro",
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
            
            logger.info("Gemini client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for single text.
        
        Args:
            text: Text to embed
            
        Returns:
            768-dimensional embedding vector
        """
        embeddings = self.embed_batch([text])
        return embeddings[0]
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = None,
        max_retries: int = 3
    ) -> List[List[float]]:
        """
        Generate embeddings for batch of texts with retry logic.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size (default from settings)
            max_retries: Maximum retry attempts for rate limits
            
        Returns:
            List of 768-dimensional embedding vectors
            
        Raises:
            Exception: If all retries fail
        """
        if not texts:
            return []
        
        if batch_size is None:
            batch_size = settings.embedding_batch_size
        
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Retry logic with exponential backoff
            for attempt in range(max_retries):
                try:
                    result = genai.embed_content(
                        model=self.embedding_model,
                        content=batch,
                        task_type="retrieval_document"
                    )
                    
                    batch_embeddings = result['embedding']
                    
                    # Handle single vs multiple embeddings
                    if isinstance(batch_embeddings[0], (int, float)):
                        # Single embedding returned
                        batch_embeddings = [batch_embeddings]
                    
                    # Validate embeddings
                    for emb in batch_embeddings:
                        if len(emb) != settings.embedding_dimension:
                            raise ValueError(
                                f"Expected {settings.embedding_dimension} dimensions, "
                                f"got {len(emb)}"
                            )
                        
                        # Check for NaN or Inf
                        if not all(np.isfinite(emb)):
                            raise ValueError("Embedding contains NaN or Infinity values")
                    
                    all_embeddings.extend(batch_embeddings)
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                            logger.warning(
                                f"Rate limit hit, retrying in {wait_time}s "
                                f"(attempt {attempt + 1}/{max_retries})"
                            )
                            time.sleep(wait_time)
                        else:
                            logger.error(f"All retries exhausted for embedding batch")
                            raise
                    else:
                        logger.error(f"Embedding generation failed: {e}")
                        raise
        
        logger.info(f"Generated {len(all_embeddings)} embeddings")
        return all_embeddings
    
    def extract_table_from_image(
        self,
        image_bytes: bytes,
        max_retries: int = 3
    ) -> str:
        """
        Extract table from image as Markdown using Vision API.
        
        Args:
            image_bytes: Image bytes (PNG/JPEG)
            max_retries: Maximum retry attempts
            
        Returns:
            Markdown table string
        """
        prompt = """Extract the table from this image and convert it to Markdown format.

Rules:
1. Preserve all cell values exactly as they appear
2. Align columns properly using pipes (|)
3. Include header row with separator (|----|)
4. If multiple tables, extract all of them
5. If no table found, return "NO_TABLE_FOUND"

Output only the Markdown table, nothing else."""
        
        for attempt in range(max_retries):
            try:
                # Convert bytes to PIL Image
                from PIL import Image
                import io
                image = Image.open(io.BytesIO(image_bytes))
                
                response = self.vision_model.generate_content([prompt, image])
                markdown = response.text.strip()
                
                # Validate it's actually a table
                if "NO_TABLE_FOUND" in markdown:
                    logger.warning("Vision API did not detect a table")
                    return ""
                
                if "|" not in markdown:
                    logger.warning("Vision API output doesn't contain table markers")
                    return ""
                
                logger.info("Successfully extracted table from image")
                return markdown
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Vision API failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to extract table after {max_retries} attempts: {e}")
                    raise
    
    def summarize_image(
        self,
        image_bytes: bytes,
        max_retries: int = 3
    ) -> str:
        """
        Generate technical summary of image using Vision API.
        
        Args:
            image_bytes: Image bytes (PNG/JPEG)
            max_retries: Maximum retry attempts
            
        Returns:
            Technical description of image
        """
        prompt = """Provide a concise technical description of this image.

Focus on:
1. Main subject or content
2. Key visual elements (charts, diagrams, photos, etc.)
3. Any text or labels visible
4. Technical details if applicable
5. Context for document search

Keep the description under 200 words and factual."""
        
        for attempt in range(max_retries):
            try:
                from PIL import Image
                import io
                image = Image.open(io.BytesIO(image_bytes))
                
                response = self.vision_model.generate_content([prompt, image])
                summary = response.text.strip()
                
                logger.info("Successfully generated image summary")
                return summary
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Image summarization failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to summarize image after {max_retries} attempts: {e}")
                    raise
    
    def generate_answer(
        self,
        prompt: str,
        max_retries: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """
        Generate text using Gemini LLM.
        
        Args:
            prompt: Input prompt with context and query
            max_retries: Maximum retry attempts
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum output tokens
            
        Returns:
            Generated text
        """
        for attempt in range(max_retries):
            try:
                response = self.text_model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    )
                )
                
                answer = response.text.strip()
                logger.info(f"Generated answer with {len(answer)} characters")
                return answer
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Text generation failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to generate text after {max_retries} attempts: {e}")
                    raise
    
    def validate_markdown_table(self, markdown: str) -> bool:
        """
        Validate Markdown table structure.
        
        Args:
            markdown: Markdown table string
            
        Returns:
            True if valid table structure
        """
        if not markdown or "|" not in markdown:
            return False
        
        lines = [line.strip() for line in markdown.strip().split("\n") if line.strip()]
        
        if len(lines) < 3:  # Need header, separator, and at least one row
            return False
        
        # Check for separator line
        has_separator = any("---" in line or "|-" in line for line in lines[:3])
        if not has_separator:
            return False
        
        # Check column consistency
        column_counts = [line.count("|") for line in lines if "|" in line]
        if not column_counts or len(set(column_counts)) > 2:
            # Allow some variance for edge cases
            return False
        
        return True
    
    def health_check(self) -> bool:
        """
        Check if Gemini API is accessible.
        
        Returns:
            True if API is working
        """
        try:
            # Test with simple embedding
            result = genai.embed_content(
                model=self.embedding_model,
                content=["test"],
                task_type="retrieval_document"
            )
            return True
        except Exception as e:
            logger.error(f"Gemini API health check failed: {e}")
            return False


# Global Gemini client instance
gemini_client = GeminiClient()
