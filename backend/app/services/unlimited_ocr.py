"""
Advanced OCR service using Baidu Unlimited-OCR for superior PDF extraction
"""
import os
import torch
import tempfile
import fitz  # PyMuPDF
from typing import List, Optional, Dict, Any
from transformers import AutoModel, AutoTokenizer
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class UnlimitedOCRService:
    """Advanced OCR service using Baidu Unlimited-OCR for superior document parsing"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_name = 'baidu/Unlimited-OCR'
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"UnlimitedOCR initialized with device: {self.device}")
    
    def _load_model(self):
        """Lazy load the OCR model"""
        if self.model is None:
            try:
                logger.info(f"Loading Unlimited-OCR model from {self.model_name}")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name, 
                    trust_remote_code=True
                )
                self.model = AutoModel.from_pretrained(
                    self.model_name,
                    trust_remote_code=True,
                    use_safetensors=True,
                    torch_dtype=torch.bfloat16 if self.device == 'cuda' else torch.float32,
                )
                self.model = self.model.eval()
                if self.device == 'cuda':
                    self.model = self.model.cuda()
                logger.info("Unlimited-OCR model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Unlimited-OCR model: {e}")
                raise
    
    def pdf_to_images(self, pdf_path: str, dpi: int = 300) -> List[str]:
        """Convert PDF pages to high-resolution images"""
        try:
            doc = fitz.open(pdf_path)
            tmp_dir = tempfile.mkdtemp(prefix='unlimited_ocr_')
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            image_paths = []
            
            for i, page in enumerate(doc):
                image_path = os.path.join(tmp_dir, f'page_{i+1:04d}.png')
                page.get_pixmap(matrix=mat).save(image_path)
                image_paths.append(image_path)
            
            doc.close()
            logger.info(f"Converted PDF to {len(image_paths)} images at {dpi} DPI")
            return image_paths
        
        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {e}")
            raise
    
    def extract_text_from_pdf(
        self, 
        pdf_path: str, 
        prompt: str = "Multi page parsing.",
        dpi: int = 300,
        output_path: Optional[str] = None
    ) -> str:
        """
        Extract text from PDF using Unlimited-OCR with multi-page parsing
        
        Args:
            pdf_path: Path to PDF file
            prompt: OCR prompt for the model
            dpi: Resolution for PDF-to-image conversion
            output_path: Optional path to save OCR results
        
        Returns:
            Extracted text content
        """
        self._load_model()
        
        try:
            # Convert PDF pages to images
            image_paths = self.pdf_to_images(pdf_path, dpi=dpi)
            
            if not image_paths:
                raise ValueError("No pages found in PDF")
            
            # Use multi-page parsing for best results
            logger.info(f"Processing {len(image_paths)} pages with Unlimited-OCR")
            
            # Create output directory if specified
            if output_path is None:
                output_path = tempfile.mkdtemp(prefix='ocr_results_')
            
            # Run OCR on all pages
            extracted_text = self.model.infer_multi(
                self.tokenizer,
                prompt=f'<image>{prompt}',
                image_files=image_paths,
                output_path=output_path,
                image_size=1024,  # Base mode for multi-page
                max_length=32768,
                no_repeat_ngram_size=35,
                ngram_window=1024,
                save_results=True,
            )
            
            # Clean up temporary image files
            for img_path in image_paths:
                try:
                    os.unlink(img_path)
                except:
                    pass
            
            logger.info(f"Successfully extracted text using Unlimited-OCR: {len(extracted_text)} characters")
            return extracted_text
        
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            # Fallback to basic PyMuPDF extraction
            return self._fallback_text_extraction(pdf_path)
    
    def extract_text_from_image(
        self, 
        image_path: str, 
        prompt: str = "document parsing.",
        mode: str = "gundam",
        output_path: Optional[str] = None
    ) -> str:
        """
        Extract text from a single image using Unlimited-OCR
        
        Args:
            image_path: Path to image file
            prompt: OCR prompt for the model
            mode: OCR mode - 'gundam' (crop_mode=True) or 'base' (crop_mode=False)
            output_path: Optional path to save OCR results
        
        Returns:
            Extracted text content
        """
        self._load_model()
        
        try:
            if output_path is None:
                output_path = tempfile.mkdtemp(prefix='ocr_results_')
            
            # Configure based on mode
            if mode == "gundam":
                base_size, image_size, crop_mode = 1024, 640, True
                ngram_window = 128
            else:  # base mode
                base_size, image_size, crop_mode = 1024, 1024, False
                ngram_window = 128
            
            logger.info(f"Processing single image with Unlimited-OCR ({mode} mode)")
            
            extracted_text = self.model.infer(
                self.tokenizer,
                prompt=f'<image>{prompt}',
                image_file=image_path,
                output_path=output_path,
                base_size=base_size,
                image_size=image_size,
                crop_mode=crop_mode,
                max_length=32768,
                no_repeat_ngram_size=35,
                ngram_window=ngram_window,
                save_results=True,
            )
            
            logger.info(f"Successfully extracted text from image: {len(extracted_text)} characters")
            return extracted_text
        
        except Exception as e:
            logger.error(f"Image OCR extraction failed: {e}")
            raise
    
    def _fallback_text_extraction(self, pdf_path: str) -> str:
        """Fallback to basic PyMuPDF extraction if OCR fails"""
        try:
            logger.info("Using fallback PyMuPDF extraction")
            doc = fitz.open(pdf_path)
            full_text = ""
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                page_text = page.get_text()
                full_text += f"\n\n--- Page {page_num + 1} ---\n\n{page_text}"
            
            doc.close()
            return full_text
        
        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
            return ""
    
    def is_scanned_pdf(self, pdf_path: str, threshold: float = 0.1) -> bool:
        """
        Detect if PDF is scanned (image-based) and would benefit from OCR
        
        Args:
            pdf_path: Path to PDF file
            threshold: Minimum text ratio to consider as native PDF
        
        Returns:
            True if PDF appears to be scanned/image-based
        """
        try:
            doc = fitz.open(pdf_path)
            total_chars = 0
            total_images = 0
            
            for page_num in range(min(3, doc.page_count)):  # Check first 3 pages
                page = doc[page_num]
                text = page.get_text().strip()
                total_chars += len(text)
                total_images += len(page.get_images())
            
            doc.close()
            
            # Heuristic: if very little text but images present, likely scanned
            has_minimal_text = total_chars < (1000 * min(3, doc.page_count))
            has_images = total_images > 0
            
            is_scanned = has_minimal_text and has_images
            logger.info(f"PDF scan detection: chars={total_chars}, images={total_images}, scanned={is_scanned}")
            return is_scanned
        
        except Exception as e:
            logger.error(f"Failed to detect PDF type: {e}")
            return False  # Assume native PDF on error
    
    def intelligent_extract(self, pdf_path: str) -> str:
        """
        Intelligently choose extraction method based on PDF type
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Extracted text using the most appropriate method
        """
        try:
            # Check if PDF is scanned/image-based
            if self.is_scanned_pdf(pdf_path):
                logger.info("Detected scanned PDF - using Unlimited-OCR")
                return self.extract_text_from_pdf(
                    pdf_path, 
                    prompt="Multi page parsing with layout preservation.",
                    dpi=300
                )
            else:
                logger.info("Detected native PDF - using PyMuPDF with OCR enhancement")
                # Try PyMuPDF first, then enhance with OCR if text is sparse
                basic_text = self._fallback_text_extraction(pdf_path)
                
                # If basic extraction yields very little text, use OCR
                if len(basic_text.strip()) < 500:
                    logger.info("Basic extraction insufficient - switching to OCR")
                    return self.extract_text_from_pdf(pdf_path)
                
                return basic_text
        
        except Exception as e:
            logger.error(f"Intelligent extraction failed: {e}")
            return self._fallback_text_extraction(pdf_path)


# Global instance
unlimited_ocr_service = UnlimitedOCRService()