"""Unit tests for validators."""

import pytest
from app.utils.validators import FileValidator, QueryValidator, InputSanitizer


class TestFileValidator:
    """Tests for file validator."""
    
    def test_validate_file_type_valid_pdf(self):
        """Test validation of valid PDF file."""
        pdf_bytes = b"%PDF-1.4\nvalid content"
        
        is_valid, error = FileValidator.validate_file_type(pdf_bytes, "document.pdf")
        
        assert is_valid is True
        assert error is None
    
    def test_validate_file_type_wrong_extension(self):
        """Test validation fails for wrong extension."""
        pdf_bytes = b"%PDF-1.4\nvalid content"
        
        is_valid, error = FileValidator.validate_file_type(pdf_bytes, "document.txt")
        
        assert is_valid is False
        assert "extension" in error.lower()
    
    def test_validate_file_type_invalid_content(self):
        """Test validation fails for non-PDF content."""
        fake_bytes = b"NOT A PDF FILE"
        
        is_valid, error = FileValidator.validate_file_type(fake_bytes, "fake.pdf")
        
        assert is_valid is False
    
    def test_validate_file_size_valid(self):
        """Test validation of file size within limits."""
        size = 10 * 1024 * 1024  # 10MB
        
        is_valid, error = FileValidator.validate_file_size(size)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_file_size_too_large(self):
        """Test validation fails for oversized file."""
        size = 60 * 1024 * 1024  # 60MB
        
        is_valid, error = FileValidator.validate_file_size(size)
        
        assert is_valid is False
        assert "exceeds" in error.lower()
    
    def test_validate_file_size_empty(self):
        """Test validation fails for empty file."""
        is_valid, error = FileValidator.validate_file_size(0)
        
        assert is_valid is False
        assert "empty" in error.lower()


class TestQueryValidator:
    """Tests for query validator."""
    
    def test_sanitize_query_removes_html(self):
        """Test query sanitization removes HTML tags."""
        query = "What is <script>alert('xss')</script> climate change?"
        
        sanitized = QueryValidator.sanitize_query(query)
        
        assert "<script>" not in sanitized
        assert "alert" not in sanitized
    
    def test_sanitize_query_removes_javascript(self):
        """Test query sanitization removes JavaScript."""
        query = "javascript:alert('xss')"
        
        sanitized = QueryValidator.sanitize_query(query)
        
        assert "javascript:" not in sanitized
    
    def test_sanitize_query_truncates_long_text(self):
        """Test query sanitization truncates long queries."""
        query = "a" * 1000
        
        sanitized = QueryValidator.sanitize_query(query)
        
        assert len(sanitized) <= 500
    
    def test_detect_sql_injection_positive(self):
        """Test SQL injection detection catches patterns."""
        queries = [
            "SELECT * FROM users",
            "1' OR '1'='1",
            "'; DROP TABLE users--",
            "EXEC sp_executesql",
        ]
        
        for query in queries:
            assert QueryValidator.detect_sql_injection(query) is True
    
    def test_detect_sql_injection_negative(self):
        """Test SQL injection detection allows normal queries."""
        queries = [
            "What is climate change?",
            "Tell me about renewable energy",
            "How does solar power work?",
        ]
        
        for query in queries:
            assert QueryValidator.detect_sql_injection(query) is False
    
    def test_validate_query_valid(self):
        """Test validation of valid query."""
        query = "What is climate change?"
        
        is_valid, error = QueryValidator.validate_query(query)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_query_empty(self):
        """Test validation fails for empty query."""
        is_valid, error = QueryValidator.validate_query("")
        
        assert is_valid is False
        assert "empty" in error.lower()
    
    def test_validate_query_injection_attempt(self):
        """Test validation fails for injection attempts."""
        query = "'; DROP TABLE users--"
        
        is_valid, error = QueryValidator.validate_query(query)
        
        assert is_valid is False
        assert "suspicious" in error.lower()


class TestInputSanitizer:
    """Tests for input sanitizer."""
    
    def test_escape_html(self):
        """Test HTML escaping."""
        text = "<script>alert('xss')</script>"
        
        escaped = InputSanitizer.escape_html(text)
        
        assert "&lt;" in escaped
        assert "&gt;" in escaped
        assert "<" not in escaped
        assert ">" not in escaped
    
    def test_sanitize_filename_removes_path_separators(self):
        """Test filename sanitization removes path separators."""
        filename = "../../../etc/passwd"
        
        sanitized = InputSanitizer.sanitize_filename(filename)
        
        assert "/" not in sanitized
        assert ".." not in sanitized
    
    def test_sanitize_filename_removes_leading_dots(self):
        """Test filename sanitization removes leading dots."""
        filename = "...hidden.pdf"
        
        sanitized = InputSanitizer.sanitize_filename(filename)
        
        assert not sanitized.startswith(".")
    
    def test_sanitize_filename_truncates_long_names(self):
        """Test filename sanitization truncates long names."""
        filename = "a" * 300 + ".pdf"
        
        sanitized = InputSanitizer.sanitize_filename(filename)
        
        assert len(sanitized) <= 255
        assert sanitized.endswith(".pdf")
    
    def test_sanitize_metadata(self):
        """Test metadata sanitization."""
        metadata = {
            "title<script>": "Test<script>alert('xss')</script>",
            "author": "John Doe",
            "page_count": 10,
        }
        
        sanitized = InputSanitizer.sanitize_metadata(metadata)
        
        assert "script" not in str(sanitized)
        assert sanitized["author"] == "John Doe"
        assert sanitized["page_count"] == 10
