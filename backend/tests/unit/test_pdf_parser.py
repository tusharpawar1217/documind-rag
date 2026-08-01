"""Unit tests for PDF parser."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from app.utils.pdf_parser import PDFParser


@pytest.fixture
def pdf_parser():
    """Create PDF parser instance."""
    return PDFParser()


@pytest.fixture
def sample_pdf_bytes():
    """Sample valid PDF bytes."""
    return b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n" + b"x" * 1000


def test_validate_pdf_valid_file(pdf_parser, sample_pdf_bytes):
    """Test validation of valid PDF file."""
    with patch('fitz.open') as mock_open:
        mock_doc = Mock()
        mock_doc.is_encrypted = False
        mock_doc.page_count = 5
        mock_open.return_value = mock_doc
        
        is_valid, error = pdf_parser.validate_pdf(sample_pdf_bytes, "test.pdf")
        
        assert is_valid is True
        assert error is None


def test_validate_pdf_exceeds_size_limit(pdf_parser):
    """Test validation fails for oversized files."""
    large_file = b"%PDF-1.4\n" + b"x" * (51 * 1024 * 1024)  # 51MB
    
    is_valid, error = pdf_parser.validate_pdf(large_file, "large.pdf")
    
    assert is_valid is False
    assert "exceeds" in error.lower()


def test_validate_pdf_invalid_magic_bytes(pdf_parser):
    """Test validation fails for invalid magic bytes."""
    invalid_bytes = b"NOT A PDF FILE"
    
    is_valid, error = pdf_parser.validate_pdf(invalid_bytes, "fake.pdf")
    
    assert is_valid is False
    assert "magic bytes" in error.lower()


def test_validate_pdf_password_protected(pdf_parser, sample_pdf_bytes):
    """Test validation fails for password-protected PDFs."""
    with patch('fitz.open') as mock_open:
        mock_doc = Mock()
        mock_doc.is_encrypted = True
        mock_open.return_value = mock_doc
        
        is_valid, error = pdf_parser.validate_pdf(sample_pdf_bytes, "encrypted.pdf")
        
        assert is_valid is False
        assert "password" in error.lower()


def test_validate_pdf_no_pages(pdf_parser, sample_pdf_bytes):
    """Test validation fails for PDF with no pages."""
    with patch('fitz.open') as mock_open:
        mock_doc = Mock()
        mock_doc.is_encrypted = False
        mock_doc.page_count = 0
        mock_open.return_value = mock_doc
        
        is_valid, error = pdf_parser.validate_pdf(sample_pdf_bytes, "empty.pdf")
        
        assert is_valid is False
        assert "no pages" in error.lower()


def test_validate_pdf_corrupted_file(pdf_parser):
    """Test validation fails for corrupted PDF."""
    corrupted_bytes = b"%PDF-1.4\n" + b"corrupted data"
    
    with patch('fitz.open') as mock_open:
        mock_open.side_effect = Exception("Corrupted PDF")
        
        is_valid, error = pdf_parser.validate_pdf(corrupted_bytes, "corrupted.pdf")
        
        assert is_valid is False
        assert "corrupted" in error.lower() or "invalid" in error.lower()


@patch('fitz.open')
def test_parse_pdf_extracts_content(mock_open, pdf_parser):
    """Test PDF parsing extracts all content."""
    # Mock document
    mock_doc = Mock()
    mock_doc.page_count = 2
    mock_doc.metadata = {"title": "Test Document"}
    
    # Mock pages
    mock_page1 = Mock()
    mock_page1.get_text.return_value = "Page 1 text"
    mock_page1.rect = Mock(width=612, height=792)
    mock_page1.get_images.return_value = []
    mock_page1.get_text.return_value = "text"
    
    mock_page2 = Mock()
    mock_page2.get_text.return_value = "Page 2 text"
    mock_page2.rect = Mock(width=612, height=792)
    mock_page2.get_images.return_value = []
    
    mock_doc.load_page.side_effect = [mock_page1, mock_page2]
    mock_open.return_value = mock_doc
    
    # Mock page rendering
    with patch.object(pdf_parser, '_render_page_image', return_value=b'image_bytes'):
        with patch.object(pdf_parser, '_detect_table_regions', return_value=[]):
            result = pdf_parser.parse_pdf("test.pdf")
    
    assert result["page_count"] == 2
    assert len(result["pages"]) == 2
    assert result["pages"][0]["page_number"] == 1
    assert result["pages"][1]["page_number"] == 2


@patch('fitz.open')
def test_extract_images_from_page(mock_open, pdf_parser):
    """Test image extraction from page."""
    mock_doc = Mock()
    mock_page = Mock()
    
    # Mock image list
    mock_page.get_images.return_value = [(123, 0, 0, 0, 0, 0, 0)]
    mock_page.parent = mock_doc
    
    # Mock extracted image
    mock_doc.extract_image.return_value = {
        "image": b"image_data",
        "ext": "png",
        "width": 800,
        "height": 600,
    }
    
    images = pdf_parser._extract_images(mock_page, 0)
    
    assert len(images) == 1
    assert images[0]["extension"] == "png"
    assert images[0]["width"] == 800


def test_group_aligned_blocks(pdf_parser):
    """Test grouping of aligned text blocks."""
    blocks = [
        {"bbox": (10, 100, 100, 120)},
        {"bbox": (110, 102, 200, 122)},  # Aligned with first
        {"bbox": (10, 150, 100, 170)},
        {"bbox": (110, 152, 200, 172)},  # Aligned with third
    ]
    
    groups = pdf_parser._group_aligned_blocks(blocks)
    
    assert len(groups) == 2
    assert len(groups[0]) == 2
    assert len(groups[1]) == 2


def test_get_group_bbox(pdf_parser):
    """Test bounding box calculation for block group."""
    blocks = [
        {"bbox": (10, 100, 50, 120)},
        {"bbox": (60, 105, 150, 125)},
        {"bbox": (160, 102, 200, 118)},
    ]
    
    bbox = pdf_parser._get_group_bbox(blocks)
    
    assert bbox == (10, 100, 200, 125)


def test_render_page_image(pdf_parser):
    """Test page rendering to image."""
    mock_page = Mock()
    mock_pix = Mock()
    mock_pix.tobytes.return_value = b"PNG_IMAGE_DATA"
    mock_page.get_pixmap.return_value = mock_pix
    
    image_bytes = pdf_parser._render_page_image(mock_page, dpi=150)
    
    assert image_bytes == b"PNG_IMAGE_DATA"
    mock_page.get_pixmap.assert_called_once()


def test_extract_metadata(pdf_parser):
    """Test metadata extraction."""
    mock_doc = Mock()
    mock_doc.metadata = {
        "title": "Test Title",
        "author": "Test Author",
        "subject": "Test Subject",
    }
    
    metadata = pdf_parser._extract_metadata(mock_doc)
    
    assert metadata["title"] == "Test Title"
    assert metadata["author"] == "Test Author"
    assert metadata["subject"] == "Test Subject"


def test_crop_region():
    """Test cropping region from image."""
    from app.utils.pdf_parser import pdf_parser
    from PIL import Image
    import io
    
    # Create test image
    img = Image.new('RGB', (100, 100), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()
    
    # Crop region
    cropped = pdf_parser.crop_region(img_bytes, (10, 10, 50, 50))
    
    assert isinstance(cropped, bytes)
    assert len(cropped) > 0
