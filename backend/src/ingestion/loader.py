"""
Document Ingestion - Load data from PDFs, CSVs, websites, etc.

This module handles loading documents from various sources and extracting their content.
"""

from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import io
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Constants from config
MAX_FILE_SIZE_BYTES = config['ingestion']['max_file_size_mb'] * 1024 * 1024
PDF_MAGIC_BYTES = b'%PDF'


class DocumentLoader:
    """
    Document loader for multiple file formats.
    
    Supports:
    - PDF files (text, images, tables)
    - Future: CSV, TXT, DOCX, websites
    """
    
    def __init__(self):
        """Initialize document loader."""
        self.pdf_parser = PDFParser()
    
    def load_document(self, file_path: str, file_type: str = "pdf") -> Dict[str, Any]:
        """
        Load document from file path.
        
        Args:
            file_path: Path to document file
            file_type: Type of document (pdf, csv, txt, etc.)
            
        Returns:
            Dictionary with document content and metadata
        """
        if file_type.lower() == "pdf":
            return self.pdf_parser.parse_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    def validate_document(self, file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate document before processing.
        
        Args:
            file_content: File bytes
            filename: Original filename
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Determine file type from extension
        ext = Path(filename).suffix.lower()
        
        if ext == '.pdf':
            return self.pdf_parser.validate_pdf(file_content, filename)
        else:
            return False, f"Unsupported file type: {ext}"


class PDFParser:
    """
    PDF parser for extracting text, images, and tables.
    
    Uses PyMuPDF (fitz) for PDF manipulation and content extraction.
    """
    
    def __init__(self):
        """Initialize PDF parser."""
        self.min_dpi = 150
        self.table_detection_dpi = 300
    
    def validate_pdf(self, file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """Validate PDF file before processing."""
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
            
            if doc.is_encrypted:
                doc.close()
                return False, "Password-protected PDFs are not supported"
            
            if doc.page_count == 0:
                doc.close()
                return False, "PDF has no pages"
            
            doc.close()
            return True, None
            
        except Exception as e:
            return False, f"Corrupted or invalid PDF: {str(e)}"
    
    def parse_pdf(self, file_path: str) -> Dict[str, Any]:
        """Parse PDF and extract all content."""
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
        return result
    
    def _extract_page_content(self, doc: fitz.Document, page_num: int) -> Dict[str, Any]:
        """Extract content from a single page."""
        page = doc.load_page(page_num)
        text = page.get_text("text")
        rect = page.rect
        
        return {
            "page_number": page_num + 1,
            "text": text,
            "images": self._extract_images(page, page_num),
            "table_regions": self._detect_table_regions(page, page_num),
            "page_image": self._render_page_image(page),
            "dimensions": {
                "width": rect.width,
                "height": rect.height,
            }
        }
    
    def _extract_images(self, page: fitz.Page, page_num: int) -> List[Dict[str, Any]]:
        """Extract images from page."""
        images = []
        for img_index, img_info in enumerate(page.get_images()):
            try:
                xref = img_info[0]
                base_image = page.parent.extract_image(xref)
                images.append({
                    "index": img_index,
                    "page_number": page_num + 1,
                    "image_bytes": base_image["image"],
                    "extension": base_image["ext"],
                    "width": base_image.get("width"),
                    "height": base_image.get("height"),
                })
            except:
                continue
        return images
    
    def _detect_table_regions(self, page: fitz.Page, page_num: int) -> List[Dict[str, Any]]:
        """Detect table regions using layout analysis."""
        table_regions = []
        try:
            blocks = page.get_text("dict")["blocks"]
            text_blocks = [b for b in blocks if b.get("type") == 0]
            aligned_groups = self._group_aligned_blocks(text_blocks)
            
            for group in aligned_groups:
                if len(group) >= 3:
                    bbox = self._get_group_bbox(group)
                    table_regions.append({
                        "page_number": page_num + 1,
                        "bbox": bbox,
                        "block_count": len(group),
                    })
        except:
            pass
        return table_regions
    
    def _group_aligned_blocks(self, blocks: List[Dict]) -> List[List[Dict]]:
        """Group horizontally aligned text blocks."""
        if not blocks:
            return []
        
        groups = []
        threshold = 10
        sorted_blocks = sorted(blocks, key=lambda b: b["bbox"][1])
        current_group = [sorted_blocks[0]]
        current_y = sorted_blocks[0]["bbox"][1]
        
        for block in sorted_blocks[1:]:
            block_y = block["bbox"][1]
            if abs(block_y - current_y) < threshold:
                current_group.append(block)
            else:
                if len(current_group) >= 2:
                    groups.append(current_group)
                current_group = [block]
                current_y = block_y
        
        if len(current_group) >= 2:
            groups.append(current_group)
        
        return groups
    
    def _get_group_bbox(self, blocks: List[Dict]) -> Tuple[float, float, float, float]:
        """Get bounding box encompassing all blocks."""
        x0 = min(b["bbox"][0] for b in blocks)
        y0 = min(b["bbox"][1] for b in blocks)
        x1 = max(b["bbox"][2] for b in blocks)
        y1 = max(b["bbox"][3] for b in blocks)
        return (x0, y0, x1, y1)
    
    def _render_page_image(self, page: fitz.Page, dpi: int = 150) -> bytes:
        """Render page as image."""
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("png")
    
    def _extract_metadata(self, doc: fitz.Document) -> Dict[str, Any]:
        """Extract PDF metadata."""
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


# Global document loader instance
document_loader = DocumentLoader()
