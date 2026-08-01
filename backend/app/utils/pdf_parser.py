"""PDF parsing and content extraction using PyMuPDF."""

from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import io

from app.core.config import settings, PDF_MIME_TYPE, PDF_MAGIC_BYTES, MAX_FILE_SIZE_BYTES
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class PDFParser:
    """
    PDF parser for extracting text, images, and tables.
    
    Uses PyMuPDF (fitz) for PDF manipulation and content extraction.
    """
    
    def __init__(self):
        """Initialize PDF parser."""
        self.min_dpi = 150  # Minimum DPI for page rendering
        self.table_detection_dpi = 300  # Higher DPI for table detection
    
    def validate_pdf(self, file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate PDF file before processing.
        
        Checks:
        - File size within limits
        - Valid PDF magic bytes
        - Not password-protected
        - Not corrupted
        
        Args:
            file_content: PDF file bytes
            filename: Original filename
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        if len(file_content) > MAX_FILE_SIZE_BYTES:
            max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
            return False, f"File size exceeds {max_mb}MB limit"
        
        # Check magic bytes
        if not file_content.startswith(PDF_MAGIC_BYTES):
            return False, "Invalid PDF file: magic bytes mismatch"
        
        # Try to open PDF
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            
            # Check if password protected
            if doc.is_encrypted:
                doc.close()
                return False, "Password-protected PDFs are not supported"
            
            # Check if has pages
            if doc.page_count == 0:
                doc.close()
                return False, "PDF has no pages"
            
            doc.close()
            return True, None
            
        except Exception as e:
            logger.error(f"PDF validation failed for {filename}: {e}")
            return False, f"Corrupted or invalid PDF: {str(e)}"
    
    def parse_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Parse PDF and extract all content.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary with:
            - page_count: Total pages
            - pages: List of page data
            - metadata: PDF metadata
        """
        try:
            doc = fitz.open(file_path)
            
            result = {
                "page_count": doc.page_count,
                "pages": [],
                "metadata": self._extract_metadata(doc),
            }
            
            # Process each page
            for page_num in range(doc.page_count):
                page_data = self._extract_page_content(doc, page_num)
                result["pages"].append(page_data)
            
            doc.close()
            logger.info(f"Parsed PDF with {doc.page_count} pages from {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise
    
    def _extract_page_content(self, doc: fitz.Document, page_num: int) -> Dict[str, Any]:
        """
        Extract content from a single page.
        
        Args:
            doc: PyMuPDF document
            page_num: Page number (0-indexed)
            
        Returns:
            Dictionary with text, images, and table regions
        """
        page = doc.load_page(page_num)
        
        # Extract text
        text = page.get_text("text")
        
        # Get page dimensions
        rect = page.rect
        
        # Extract images
        images = self._extract_images(page, page_num)
        
        # Detect table regions (bounding boxes)
        table_regions = self._detect_table_regions(page, page_num)
        
        # Render page as image for Vision API
        page_image = self._render_page_image(page)
        
        return {
            "page_number": page_num + 1,  # 1-indexed for user display
            "text": text,
            "images": images,
            "table_regions": table_regions,
            "page_image": page_image,
            "dimensions": {
                "width": rect.width,
                "height": rect.height,
            }
        }
    
    def _extract_images(self, page: fitz.Page, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract images from page.
        
        Args:
            page: PyMuPDF page
            page_num: Page number
            
        Returns:
            List of image data dictionaries
        """
        images = []
        image_list = page.get_images()
        
        for img_index, img_info in enumerate(image_list):
            try:
                xref = img_info[0]
                base_image = page.parent.extract_image(xref)
                
                image_data = {
                    "index": img_index,
                    "page_number": page_num + 1,
                    "image_bytes": base_image["image"],
                    "extension": base_image["ext"],
                    "width": base_image.get("width"),
                    "height": base_image.get("height"),
                }
                images.append(image_data)
                
            except Exception as e:
                logger.warning(f"Failed to extract image {img_index} from page {page_num}: {e}")
                continue
        
        return images
    
    def _detect_table_regions(self, page: fitz.Page, page_num: int) -> List[Dict[str, Any]]:
        """
        Detect table regions in page using layout analysis.
        
        Uses text block positioning to identify potential tables.
        
        Args:
            page: PyMuPDF page
            page_num: Page number
            
        Returns:
            List of table region bounding boxes
        """
        table_regions = []
        
        try:
            # Get text blocks with position
            blocks = page.get_text("dict")["blocks"]
            
            # Simple heuristic: look for aligned text blocks
            # (A more sophisticated approach would use ML-based table detection)
            text_blocks = [b for b in blocks if b.get("type") == 0]  # Text blocks
            
            # Group blocks that are horizontally aligned
            aligned_groups = self._group_aligned_blocks(text_blocks)
            
            # Identify potential tables (groups with multiple aligned rows)
            for group in aligned_groups:
                if len(group) >= 3:  # At least 3 rows
                    bbox = self._get_group_bbox(group)
                    table_regions.append({
                        "page_number": page_num + 1,
                        "bbox": bbox,  # (x0, y0, x1, y1)
                        "block_count": len(group),
                    })
            
        except Exception as e:
            logger.warning(f"Table detection failed for page {page_num}: {e}")
        
        return table_regions
    
    def _group_aligned_blocks(self, blocks: List[Dict]) -> List[List[Dict]]:
        """
        Group text blocks that are horizontally aligned.
        
        Args:
            blocks: List of text blocks
            
        Returns:
            List of aligned block groups
        """
        if not blocks:
            return []
        
        groups = []
        threshold = 10  # Vertical alignment threshold in points
        
        # Sort blocks by vertical position
        sorted_blocks = sorted(blocks, key=lambda b: b["bbox"][1])
        
        current_group = [sorted_blocks[0]]
        current_y = sorted_blocks[0]["bbox"][1]
        
        for block in sorted_blocks[1:]:
            block_y = block["bbox"][1]
            
            if abs(block_y - current_y) < threshold:
                # Same row
                current_group.append(block)
            else:
                # New row
                if len(current_group) >= 2:  # Only keep groups with multiple columns
                    groups.append(current_group)
                current_group = [block]
                current_y = block_y
        
        # Add last group
        if len(current_group) >= 2:
            groups.append(current_group)
        
        return groups
    
    def _get_group_bbox(self, blocks: List[Dict]) -> Tuple[float, float, float, float]:
        """
        Get bounding box encompassing all blocks.
        
        Args:
            blocks: List of blocks
            
        Returns:
            Tuple of (x0, y0, x1, y1)
        """
        x0 = min(b["bbox"][0] for b in blocks)
        y0 = min(b["bbox"][1] for b in blocks)
        x1 = max(b["bbox"][2] for b in blocks)
        y1 = max(b["bbox"][3] for b in blocks)
        return (x0, y0, x1, y1)
    
    def _render_page_image(self, page: fitz.Page, dpi: int = 150) -> bytes:
        """
        Render page as image.
        
        Args:
            page: PyMuPDF page
            dpi: Resolution for rendering
            
        Returns:
            PNG image bytes
        """
        try:
            # Calculate zoom factor for DPI
            zoom = dpi / 72  # 72 is default DPI
            mat = fitz.Matrix(zoom, zoom)
            
            # Render page
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PNG bytes
            img_bytes = pix.tobytes("png")
            return img_bytes
            
        except Exception as e:
            logger.error(f"Failed to render page image: {e}")
            raise
    
    def crop_region(self, page_image_bytes: bytes, bbox: Tuple[float, float, float, float]) -> bytes:
        """
        Crop a region from page image.
        
        Args:
            page_image_bytes: Full page image
            bbox: Bounding box (x0, y0, x1, y1)
            
        Returns:
            Cropped image bytes
        """
        try:
            # Open image
            img = Image.open(io.BytesIO(page_image_bytes))
            
            # Crop region
            cropped = img.crop(bbox)
            
            # Convert to bytes
            output = io.BytesIO()
            cropped.save(output, format="PNG")
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to crop image region: {e}")
            raise
    
    def _extract_metadata(self, doc: fitz.Document) -> Dict[str, Any]:
        """
        Extract PDF metadata.
        
        Args:
            doc: PyMuPDF document
            
        Returns:
            Metadata dictionary
        """
        metadata = doc.metadata or {}
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
        }


# Global PDF parser instance
pdf_parser = PDFParser()
