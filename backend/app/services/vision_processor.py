"""Vision processing service for tables and images."""

from typing import List, Dict, Any, Optional
from app.services.gemini_client import gemini_client
from app.utils.pdf_parser import pdf_parser
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class VisionProcessor:
    """
    Processor for extracting tables and summarizing images using Vision API.
    
    Uses Gemini Vision for:
    - Table extraction to Markdown
    - Image technical summaries
    - OCR fallback for failed extractions
    """
    
    def __init__(self):
        """Initialize vision processor with Gemini client."""
        self.gemini_client = gemini_client
    
    def extract_tables_from_page(
        self,
        page_data: Dict[str, Any],
        document_id: str
    ) -> List[Dict[str, Any]]:
        """
        Extract all tables from a page.
        
        Args:
            page_data: Page data from PDF parser
            document_id: Document UUID
            
        Returns:
            List of table chunks
        """
        table_chunks = []
        table_regions = page_data.get("table_regions", [])
        
        if not table_regions:
            return []
        
        page_image = page_data.get("page_image")
        if not page_image:
            logger.warning(f"No page image for table extraction on page {page_data['page_number']}")
            return []
        
        for region_idx, region in enumerate(table_regions):
            try:
                # Crop table region from page image
                bbox = region["bbox"]
                table_image = pdf_parser.crop_region(page_image, bbox)
                
                # Extract table using Vision API
                markdown_table = self.gemini_client.extract_table_from_image(table_image)
                
                if not markdown_table:
                    logger.warning(
                        f"No table extracted from region {region_idx} "
                        f"on page {page_data['page_number']}"
                    )
                    continue
                
                # Validate Markdown structure
                if not self.gemini_client.validate_markdown_table(markdown_table):
                    logger.warning(
                        f"Invalid Markdown table structure on page {page_data['page_number']}, "
                        f"attempting OCR fallback"
                    )
                    # TODO: Implement OCR fallback with pytesseract
                    continue
                
                # Create chunk for table
                table_chunk = {
                    "content": markdown_table,
                    "chunk_type": "table",
                    "page_number": page_data["page_number"],
                    "metadata": {
                        "region_index": region_idx,
                        "bbox": bbox,
                        "extraction_method": "gemini_vision",
                    }
                }
                table_chunks.append(table_chunk)
                
                logger.info(
                    f"Extracted table {region_idx} from page {page_data['page_number']}"
                )
                
            except Exception as e:
                logger.error(
                    f"Failed to extract table {region_idx} from "
                    f"page {page_data['page_number']}: {e}"
                )
                continue
        
        return table_chunks
    
    def process_images_from_page(
        self,
        page_data: Dict[str, Any],
        document_id: str
    ) -> List[Dict[str, Any]]:
        """
        Process all images from a page.
        
        Args:
            page_data: Page data from PDF parser
            document_id: Document UUID
            
        Returns:
            List of image summary chunks
        """
        image_chunks = []
        images = page_data.get("images", [])
        
        if not images:
            return []
        
        for image_data in images:
            try:
                image_bytes = image_data.get("image_bytes")
                if not image_bytes:
                    continue
                
                # Generate technical summary using Vision API
                summary = self.gemini_client.summarize_image(image_bytes)
                
                if not summary or len(summary.strip()) < 10:
                    logger.warning(
                        f"Empty or too short image summary on page {page_data['page_number']}"
                    )
                    continue
                
                # Create chunk for image
                image_chunk = {
                    "content": summary,
                    "chunk_type": "image",
                    "page_number": page_data["page_number"],
                    "metadata": {
                        "image_index": image_data["index"],
                        "image_extension": image_data.get("extension"),
                        "image_width": image_data.get("width"),
                        "image_height": image_data.get("height"),
                        "extraction_method": "gemini_vision",
                    }
                }
                image_chunks.append(image_chunk)
                
                logger.info(
                    f"Processed image {image_data['index']} from "
                    f"page {page_data['page_number']}"
                )
                
            except Exception as e:
                logger.error(
                    f"Failed to process image {image_data.get('index')} from "
                    f"page {page_data['page_number']}: {e}"
                )
                continue
        
        return image_chunks
    
    def ocr_fallback(self, image_bytes: bytes) -> str:
        """
        OCR fallback for failed Vision API extractions.
        
        Args:
            image_bytes: Image bytes
            
        Returns:
            Extracted text
        """
        # TODO: Implement pytesseract OCR fallback
        logger.info("OCR fallback not yet implemented")
        return ""


# Global vision processor instance
vision_processor = VisionProcessor()
