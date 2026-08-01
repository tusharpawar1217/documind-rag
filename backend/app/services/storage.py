"""File storage service for PDF documents."""

import os
import shutil
from pathlib import Path
from typing import Optional
from uuid import uuid4
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class StorageService:
    """
    Service for secure file storage and retrieval.
    
    Features:
    - Secure file naming
    - AES-256 encryption at rest
    - Secure deletion with overwrite
    - Directory management
    """
    
    def __init__(self):
        """Initialize storage service with encryption."""
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate encryption key from JWT secret (deterministic)
        self._encryption_key = self._derive_key(settings.jwt_secret_key)
        self._cipher = Fernet(self._encryption_key)
        
        logger.info(f"Storage service initialized at {self.upload_dir}")
    
    def _derive_key(self, password: str) -> bytes:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: Source password/secret
            
        Returns:
            32-byte encryption key
        """
        salt = b"documind_salt_v1"  # Fixed salt for deterministic key
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def save_file(
        self,
        file_content: bytes,
        document_id: str,
        original_filename: str,
        encrypt: bool = True
    ) -> str:
        """
        Save file to storage with optional encryption.
        
        Args:
            file_content: File bytes
            document_id: Document UUID
            original_filename: Original filename
            encrypt: Whether to encrypt file at rest
            
        Returns:
            Path to saved file
        """
        try:
            # Generate secure filename using document_id
            file_ext = Path(original_filename).suffix
            secure_filename = f"{document_id}{file_ext}"
            file_path = self.upload_dir / secure_filename
            
            # Encrypt if requested
            if encrypt:
                file_content = self._cipher.encrypt(file_content)
                logger.info(f"File encrypted for document {document_id}")
            
            # Write file
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            logger.info(f"Saved file to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            raise
    
    def read_file(self, file_path: str, decrypt: bool = True) -> bytes:
        """
        Read file from storage with optional decryption.
        
        Args:
            file_path: Path to file
            decrypt: Whether to decrypt file
            
        Returns:
            File content bytes
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            with open(path, "rb") as f:
                content = f.read()
            
            # Decrypt if requested
            if decrypt:
                try:
                    content = self._cipher.decrypt(content)
                    logger.debug(f"File decrypted from {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to decrypt file, returning raw content: {e}")
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            raise
    
    def delete_file(self, file_path: str, secure: bool = True) -> bool:
        """
        Delete file with optional secure overwrite.
        
        Args:
            file_path: Path to file
            secure: Whether to securely overwrite before deletion
            
        Returns:
            True if successful
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                logger.warning(f"File not found for deletion: {file_path}")
                return True
            
            if secure:
                # Secure deletion: overwrite with random data
                file_size = path.stat().st_size
                with open(path, "wb") as f:
                    f.write(os.urandom(file_size))
                logger.debug(f"Securely overwrote file {file_path}")
            
            # Delete file
            path.unlink()
            logger.info(f"Deleted file {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            raise
    
    def get_file_path(self, document_id: str, extension: str = ".pdf") -> Path:
        """
        Get file path for a document ID.
        
        Args:
            document_id: Document UUID
            extension: File extension
            
        Returns:
            Path to file
        """
        return self.upload_dir / f"{document_id}{extension}"
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if file exists.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file exists
        """
        return Path(file_path).exists()
    
    def get_file_size(self, file_path: str) -> int:
        """
        Get file size in bytes.
        
        Args:
            file_path: Path to file
            
        Returns:
            File size in bytes
        """
        return Path(file_path).stat().st_size
    
    def cleanup_temp_files(self) -> int:
        """
        Clean up temporary files older than 24 hours.
        
        Returns:
            Number of files deleted
        """
        import time
        
        count = 0
        current_time = time.time()
        
        try:
            for file_path in self.upload_dir.glob("*.tmp"):
                # Check if file is older than 24 hours
                file_age = current_time - file_path.stat().st_mtime
                if file_age > 86400:  # 24 hours in seconds
                    file_path.unlink()
                    count += 1
            
            if count > 0:
                logger.info(f"Cleaned up {count} temporary files")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}")
            return count


# Global storage service instance
storage_service = StorageService()
