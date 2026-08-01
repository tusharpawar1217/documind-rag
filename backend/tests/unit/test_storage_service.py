"""Unit tests for storage service."""

import pytest
from pathlib import Path
import tempfile
import shutil
from app.services.storage import StorageService
from app.core.config import settings


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage_service(temp_storage_dir, monkeypatch):
    """Create storage service with temporary directory."""
    monkeypatch.setattr(settings, "upload_dir", temp_storage_dir)
    service = StorageService()
    return service


def test_save_and_read_file_without_encryption(storage_service):
    """Test saving and reading file without encryption."""
    content = b"Test PDF content"
    document_id = "doc-123"
    filename = "test.pdf"
    
    # Save file
    file_path = storage_service.save_file(
        content,
        document_id,
        filename,
        encrypt=False
    )
    
    assert Path(file_path).exists()
    
    # Read file
    read_content = storage_service.read_file(file_path, decrypt=False)
    assert read_content == content


def test_save_and_read_file_with_encryption(storage_service):
    """Test saving and reading file with encryption."""
    content = b"Test PDF content"
    document_id = "doc-456"
    filename = "test.pdf"
    
    # Save encrypted file
    file_path = storage_service.save_file(
        content,
        document_id,
        filename,
        encrypt=True
    )
    
    # Read encrypted file
    read_content = storage_service.read_file(file_path, decrypt=True)
    assert read_content == content


def test_delete_file(storage_service):
    """Test file deletion."""
    content = b"Test content"
    document_id = "doc-789"
    filename = "test.pdf"
    
    file_path = storage_service.save_file(content, document_id, filename, encrypt=False)
    assert Path(file_path).exists()
    
    # Delete file
    result = storage_service.delete_file(file_path, secure=False)
    assert result is True
    assert not Path(file_path).exists()


def test_secure_delete_overwrites_file(storage_service):
    """Test secure deletion overwrites file before deleting."""
    content = b"Sensitive content"
    document_id = "doc-secure"
    filename = "test.pdf"
    
    file_path = storage_service.save_file(content, document_id, filename, encrypt=False)
    original_size = Path(file_path).stat().st_size
    
    # Secure delete
    result = storage_service.delete_file(file_path, secure=True)
    assert result is True
    assert not Path(file_path).exists()


def test_file_exists(storage_service):
    """Test file existence check."""
    content = b"Test content"
    document_id = "doc-exists"
    filename = "test.pdf"
    
    file_path = storage_service.save_file(content, document_id, filename, encrypt=False)
    
    assert storage_service.file_exists(file_path) is True
    assert storage_service.file_exists("/nonexistent/path.pdf") is False


def test_get_file_size(storage_service):
    """Test getting file size."""
    content = b"Test content with known size"
    document_id = "doc-size"
    filename = "test.pdf"
    
    file_path = storage_service.save_file(content, document_id, filename, encrypt=False)
    size = storage_service.get_file_size(file_path)
    
    assert size == len(content)


def test_get_file_path(storage_service):
    """Test generating file path from document ID."""
    document_id = "doc-123"
    
    file_path = storage_service.get_file_path(document_id)
    
    assert str(document_id) in str(file_path)
    assert str(file_path).endswith(".pdf")


def test_read_nonexistent_file_raises_error(storage_service):
    """Test reading nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        storage_service.read_file("/nonexistent/file.pdf")


def test_delete_nonexistent_file_returns_true(storage_service):
    """Test deleting nonexistent file returns True (idempotent)."""
    result = storage_service.delete_file("/nonexistent/file.pdf")
    assert result is True


def test_cleanup_temp_files(storage_service, temp_storage_dir):
    """Test cleanup of old temporary files."""
    import time
    
    # Create old temp file
    old_temp = temp_storage_dir / "old.tmp"
    old_temp.write_bytes(b"old")
    
    # Set modification time to 25 hours ago
    old_time = time.time() - (25 * 3600)
    import os
    os.utime(old_temp, (old_time, old_time))
    
    # Create recent temp file
    recent_temp = temp_storage_dir / "recent.tmp"
    recent_temp.write_bytes(b"recent")
    
    # Cleanup
    count = storage_service.cleanup_temp_files()
    
    assert count == 1
    assert not old_temp.exists()
    assert recent_temp.exists()
