"""Input validation and sanitization utilities."""

import re
from typing import Optional, Tuple
import magic
from app.core.config import PDF_MIME_TYPE, MAX_FILE_SIZE_BYTES
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class FileValidator:
    """Validator for uploaded files."""
    
    @staticmethod
    def validate_file_type(file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file is a PDF using MIME type detection.
        
        Args:
            file_content: File bytes
            filename: Original filename
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file extension
        if not filename.lower().endswith('.pdf'):
            return False, "File must have .pdf extension"
        
        # Detect MIME type using python-magic
        try:
            mime = magic.from_buffer(file_content, mime=True)
            if mime != PDF_MIME_TYPE and mime != "application/x-pdf":
                return False, f"Invalid file type: {mime}. Expected PDF"
            return True, None
        except Exception as e:
            logger.warning(f"MIME type detection failed, checking magic bytes: {e}")
            
            # Fallback: check magic bytes
            if file_content.startswith(b"%PDF"):
                return True, None
            return False, "Invalid PDF file"
    
    @staticmethod
    def validate_file_size(file_size: int) -> Tuple[bool, Optional[str]]:
        """
        Validate file size is within limits.
        
        Args:
            file_size: File size in bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if file_size > MAX_FILE_SIZE_BYTES:
            max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
            return False, f"File size exceeds {max_mb}MB limit"
        
        if file_size == 0:
            return False, "File is empty"
        
        return True, None
    
    @staticmethod
    def scan_for_malware(file_content: bytes) -> Tuple[bool, Optional[str]]:
        """
        Scan file for malware (placeholder for actual scanner integration).
        
        In production, integrate with ClamAV or similar.
        
        Args:
            file_content: File bytes
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        # TODO: Integrate with actual malware scanner (e.g., ClamAV)
        # For now, just log and return safe
        logger.info("Malware scan placeholder - integrate ClamAV in production")
        return True, None


class QueryValidator:
    """Validator for user queries."""
    
    # Patterns that might indicate injection attempts
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(;|\-\-|\/\*|\*\/|xp_|sp_)",
        r"(\bOR\b.*=.*\bOR\b)",
        r"(\bAND\b.*=.*\bAND\b)",
    ]
    
    # HTML/Script patterns
    HTML_SCRIPT_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"<iframe[^>]*>.*?</iframe>",
        r"javascript:",
        r"on\w+\s*=",
        r"<.*?>",
    ]
    
    @staticmethod
    def sanitize_query(query: str) -> str:
        """
        Sanitize user query to prevent injection attacks.
        
        Args:
            query: Raw user query
            
        Returns:
            Sanitized query
        """
        # Strip leading/trailing whitespace
        query = query.strip()
        
        # Remove HTML tags
        for pattern in QueryValidator.HTML_SCRIPT_PATTERNS:
            query = re.sub(pattern, "", query, flags=re.IGNORECASE)
        
        # Remove null bytes
        query = query.replace("\x00", "")
        
        # Limit length
        max_length = 500
        if len(query) > max_length:
            logger.warning(f"Query truncated from {len(query)} to {max_length} chars")
            query = query[:max_length]
        
        return query
    
    @staticmethod
    def detect_sql_injection(query: str) -> bool:
        """
        Detect potential SQL injection patterns.
        
        Args:
            query: User query
            
        Returns:
            True if suspicious patterns detected
        """
        for pattern in QueryValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected in query")
                return True
        return False
    
    @staticmethod
    def validate_query(query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate and sanitize user query.
        
        Args:
            query: User query
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if empty
        if not query or not query.strip():
            return False, "Query cannot be empty"
        
        # Sanitize
        sanitized = QueryValidator.sanitize_query(query)
        
        # Check for injection attempts
        if QueryValidator.detect_sql_injection(sanitized):
            return False, "Query contains suspicious patterns"
        
        # Check length after sanitization
        if len(sanitized) == 0:
            return False, "Query is empty after sanitization"
        
        return True, None


class InputSanitizer:
    """General input sanitization utilities."""
    
    @staticmethod
    def escape_html(text: str) -> str:
        """
        Escape HTML special characters.
        
        Args:
            text: Input text
            
        Returns:
            Escaped text
        """
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&#x27;",
            ">": "&gt;",
            "<": "&lt;",
        }
        return "".join(html_escape_table.get(c, c) for c in text)
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal.
        
        Args:
            filename: Original filename
            
        Returns:
            Safe filename
        """
        # Remove path separators
        filename = filename.replace("/", "_").replace("\\", "_")
        
        # Remove null bytes
        filename = filename.replace("\x00", "")
        
        # Remove leading dots (hidden files)
        filename = filename.lstrip(".")
        
        # Limit length
        max_length = 255
        if len(filename) > max_length:
            name, ext = filename.rsplit(".", 1)
            filename = name[:max_length - len(ext) - 1] + "." + ext
        
        return filename
    
    @staticmethod
    def sanitize_metadata(metadata: dict) -> dict:
        """
        Sanitize metadata dictionary.
        
        Args:
            metadata: Input metadata
            
        Returns:
            Sanitized metadata
        """
        sanitized = {}
        
        for key, value in metadata.items():
            # Sanitize key
            safe_key = re.sub(r'[^a-zA-Z0-9_-]', '', str(key))
            
            # Sanitize value if string
            if isinstance(value, str):
                safe_value = InputSanitizer.escape_html(value)
            else:
                safe_value = value
            
            sanitized[safe_key] = safe_value
        
        return sanitized


# Global validator instances
file_validator = FileValidator()
query_validator = QueryValidator()
input_sanitizer = InputSanitizer()
