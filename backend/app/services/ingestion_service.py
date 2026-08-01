"""Document ingestion service for end-to-end processing."""

from typing import Dict, Any, List
from uuid import uuid4
from datetime import datetime

from app.models import (
    Document,
    DocumentStatus,
    DocumentChunk,
    ChunkCreate,
)
from app.services.qdrant_client import qdrant_service
from app.services.storage import storage_service
from app.services.gemini_client import gemini_client
from app.services.vision_processor import vision_processor
from app.utils.pdf_parser import pdf_parser
from app.utils.text_processing import SemanticChunker, count_tokens
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class IngestionService:
    """
    End-to-end document ingestion service.
    
    Pipeline:
    1. Validate and store PDF file
    2. Parse PDF (extract text, tables, images)
    3. Semantic chunking of text
    4. Extract tables with Vision API
    5. Process images with Vision API
    6. Generate embeddings for all chunks
    7. Store chunks in Qdrant
    8. Update document status
    """
    
    def __init__(self):
        """Initialize ingestion service with all dependencies."""
        self.qdrant_service = qdrant_service
        self.storage_service = storage_service
        self.gemini_client = gemini_client
        self.vision_processor = vision_processor
        self.pdf_parser = pdf_parser
        self.semantic_chunker = SemanticChunker(gemini_client)
    
    async def ingest_document(
        self,
        file_content: bytes,
        filename: str,
        user_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Main ingestion pipeline for PDF documents.
        
        Args:
            file_content: PDF file bytes
            filename: Original filename
            user_id: User ID for ownership
            metadata: Additional metadata
            
        Returns:
            Dictionary with ingestion status and details
        """
        document_id = str(uuid4())
        
        try:
            # Step 1: Validate PDF
            logger.info(f"Starting ingestion for document {document_id}")
            is_valid, error = self.pdf_parser.validate_pdf(file_content, filename)
            if not is_valid:
                return {
                    "status": "error",
                    "document_id": document_id,
                    "error": error,
                }
            
            # Step 2: Store file
            file_path = self.storage_service.save_file(
                file_content,
                document_id,
                filename,
                encrypt=True
            )
            
            # Step 3: Create document record
            document = Document(
                document_id=document_id,
                filename=filename,
                file_path=file_path,
                page_count=0,  # Will update after parsing
                status=DocumentStatus.PROCESSING,
                file_size=len(file_content),
                user_id=user_id,
                metadata=metadata or {}
            )
            
            # Step 4: Parse PDF
            logger.info(f"Parsing PDF for document {document_id}")
            pdf_data = self.pdf_parser.parse_pdf(file_path)
            document.page_count = pdf_data["page_count"]
            document.metadata.update(pdf_data.get("metadata", {}))
            
            # Step 5: Process all pages
            all_chunks = []
            
            for page_data in pdf_data["pages"]:
                page_num = page_data["page_number"]
                logger.info(f"Processing page {page_num}/{document.page_count}")
                
                # Extract text chunks
                text = page_data.get("text", "").strip()
                if text:
                    text_chunks = self.semantic_chunker.chunk_text(
                        text,
                        page_num,
                        document_id
                    )
                    all_chunks.extend(text_chunks)
                
                # Extract tables
                table_chunks = self.vision_processor.extract_tables_from_page(
                    page_data,
                    document_id
                )
                all_chunks.extend(table_chunks)
                
                # Process images
                image_chunks = self.vision_processor.process_images_from_page(
                    page_data,
                    document_id
                )
                all_chunks.extend(image_chunks)
            
            if not all_chunks:
                logger.warning(f"No chunks created for document {document_id}")
                return {
                    "status": "error",
                    "document_id": document_id,
                    "error": "No content extracted from document",
                }
            
            # Step 6: Generate embeddings
            logger.info(f"Generating embeddings for {len(all_chunks)} chunks")
            chunk_texts = [chunk["content"] for chunk in all_chunks]
            embeddings = self.gemini_client.embed_batch(chunk_texts)
            
            # Step 7: Create DocumentChunk objects
            document_chunks = []
            for idx, (chunk_data, embedding) in enumerate(zip(all_chunks, embeddings)):
                doc_chunk = DocumentChunk(
                    chunk_id=str(uuid4()),
                    document_id=document_id,
                    content=chunk_data["content"],
                    chunk_type=chunk_data.get("chunk_type", "text"),
                    page_number=chunk_data["page_number"],
                    chunk_index=idx,
                    embedding=embedding,
                    token_count=chunk_data.get("token_count", count_tokens(chunk_data["content"])),
                    metadata={
                        **chunk_data.get("metadata", {}),
                        "document_name": filename,
                        "total_pages": document.page_count,
                    }
                )
                document_chunks.append(doc_chunk)
            
            # Step 8: Store in Qdrant
            logger.info(f"Storing {len(document_chunks)} chunks in Qdrant")
            self.qdrant_service.upsert_chunks(document_chunks, user_id=user_id)
            
            # Step 9: Update document status
            document.status = DocumentStatus.READY
            document.chunk_count = len(document_chunks)
            
            logger.info(
                f"Successfully ingested document {document_id}: "
                f"{document.page_count} pages, {document.chunk_count} chunks"
            )
            
            return {
                "status": "success",
                "document_id": document_id,
                "filename": filename,
                "page_count": document.page_count,
                "chunk_count": document.chunk_count,
                "chunks_by_type": {
                    "text": sum(1 for c in document_chunks if c.chunk_type == "text"),
                    "table": sum(1 for c in document_chunks if c.chunk_type == "table"),
                    "image": sum(1 for c in document_chunks if c.chunk_type == "image"),
                }
            }
            
        except Exception as e:
            logger.error(f"Ingestion failed for document {document_id}: {e}")
            
            # Clean up on failure
            try:
                if file_path and self.storage_service.file_exists(file_path):
                    self.storage_service.delete_file(file_path)
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup after error: {cleanup_error}")
            
            return {
                "status": "error",
                "document_id": document_id,
                "error": str(e),
            }
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete document and all associated chunks.
        
        Args:
            document_id: Document UUID
            
        Returns:
            True if successful
        """
        try:
            # Delete from Qdrant
            self.qdrant_service.delete_by_document_id(document_id)
            
            # Delete file
            file_path = self.storage_service.get_file_path(document_id)
            if self.storage_service.file_exists(str(file_path)):
                self.storage_service.delete_file(str(file_path), secure=True)
            
            logger.info(f"Deleted document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise


# Global ingestion service instance
ingestion_service = IngestionService()
