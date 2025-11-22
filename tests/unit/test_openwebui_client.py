"""
Unit tests for OpenWebUI client.

Tests the OpenWebUIClient class with mock responses, covering:
- Initialization and validation
- Connection testing
- File upload operations
- Knowledge base management
- File operations and updates
- Incremental upload workflow
- Error handling and edge cases
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientSession

from webowui.uploader.openwebui_client import OpenWebUIClient

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client():
    """Create an OpenWebUIClient instance."""
    return OpenWebUIClient("http://localhost:8000", "test-key-123")


@pytest.fixture
def mock_session():
    """Mock aiohttp.ClientSession."""
    with patch("aiohttp.ClientSession") as mock:
        session = AsyncMock(spec=ClientSession)
        mock.return_value.__aenter__.return_value = session
        yield session


# ============================================================================
# Initialization Tests
# ============================================================================


@pytest.mark.unit
def test_client_init():
    """Test basic client initialization with valid parameters."""
    client = OpenWebUIClient("http://localhost:8000", "test-key-123")

    assert client.base_url == "http://localhost:8000"
    assert client.api_key == "test-key-123"
    assert client.headers["Authorization"] == "Bearer test-key-123"


@pytest.mark.unit
def test_client_init_strip_slash():
    """Test that trailing slash is stripped from base_url."""
    client = OpenWebUIClient("http://localhost:8000/", "test-key-123")
    assert client.base_url == "http://localhost:8000"


# ============================================================================
# Connection Testing
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_test_connection_success(client, mock_session):
    """Test successful connection to OpenWebUI."""
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await client.test_connection()

    assert result is True
    mock_session.get.assert_called_once()
    args, kwargs = mock_session.get.call_args
    assert args[0] == "http://localhost:8000/api/v1/knowledge/list"
    assert kwargs["headers"] == client.headers


@pytest.mark.unit
@pytest.mark.asyncio
async def test_test_connection_failure(client, mock_session):
    """Test connection failure."""
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.status = 401
    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await client.test_connection()

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_test_connection_exception(client, mock_session):
    """Test connection exception."""
    mock_session.get.side_effect = Exception("Connection error")

    result = await client.test_connection()

    assert result is False


# ============================================================================
# Knowledge Base Creation Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_knowledge_new(client, mock_session):
    """Test creating a new knowledge base."""
    # Mock _get_knowledge_by_name to return None (not found)
    # We need to mock the session for both calls: list (get) and create (post)

    # Setup list response (empty)
    mock_list_response = AsyncMock()
    mock_list_response.status = 200
    mock_list_response.json.return_value = []

    # Setup create response
    mock_create_response = AsyncMock()
    mock_create_response.status = 200
    mock_create_response.json.return_value = {"id": "kb-123", "name": "Test KB"}

    # Configure side_effect for get (list) and post (create)
    mock_session.get.return_value.__aenter__.return_value = mock_list_response
    mock_session.post.return_value.__aenter__.return_value = mock_create_response

    result = await client.create_knowledge("Test KB", "Test description")

    assert result is not None
    assert result["id"] == "kb-123"
    assert result["name"] == "Test KB"

    # Verify calls
    mock_session.get.assert_called_once()  # Check existence
    mock_session.post.assert_called_once()  # Create

    # Verify create payload
    args, kwargs = mock_session.post.call_args
    assert args[0] == "http://localhost:8000/api/v1/knowledge/create"
    assert kwargs["json"] == {"name": "Test KB", "description": "Test description"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_knowledge_existing(client, mock_session):
    """Test getting an existing knowledge base."""
    # Setup list response with existing KB
    mock_list_response = AsyncMock()
    mock_list_response.status = 200
    mock_list_response.json.return_value = [{"id": "kb-123", "name": "Test KB"}]

    mock_session.get.return_value.__aenter__.return_value = mock_list_response

    result = await client.create_knowledge("Test KB", "Test description")

    assert result is not None
    assert result["id"] == "kb-123"

    # Verify calls
    mock_session.get.assert_called_once()
    mock_session.post.assert_not_called()  # Should not create new


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_knowledge_failure(client, mock_session):
    """Test knowledge base creation failure."""
    # Setup list response (empty)
    mock_list_response = AsyncMock()
    mock_list_response.status = 200
    mock_list_response.json.return_value = []

    # Setup create response (failure)
    mock_create_response = AsyncMock()
    mock_create_response.status = 400
    mock_create_response.text.return_value = "Bad Request"

    mock_session.get.return_value.__aenter__.return_value = mock_list_response
    mock_session.post.return_value.__aenter__.return_value = mock_create_response

    result = await client.create_knowledge("Test KB")

    assert result is None


# ============================================================================
# Knowledge Discovery Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_knowledge_by_content_single_match(client, mock_session):
    """Test finding knowledge base with single name match."""
    # Setup list response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = [{"id": "kb-1", "name": "Test KB"}]
    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await client.find_knowledge_by_content("site", "Test KB")

    assert result == "kb-1"
    mock_session.get.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_knowledge_by_content_multiple_matches(client, mock_session):
    """Test finding knowledge base with multiple name matches (content check)."""
    # Setup list response
    mock_list_response = AsyncMock()
    mock_list_response.status = 200
    mock_list_response.json.return_value = [
        {"id": "kb-1", "name": "Test KB"},
        {"id": "kb-2", "name": "Test KB"},
    ]

    # Setup content check responses
    # KB-1: No files
    mock_kb1_response = AsyncMock()
    mock_kb1_response.status = 200
    mock_kb1_response.json.return_value = {"files": []}

    # KB-2: Has files
    mock_kb2_response = AsyncMock()
    mock_kb2_response.status = 200
    mock_kb2_response.json.return_value = {
        "files": [{"id": "file-1", "meta": {"name": "site/test.md"}}]
    }

    mock_session.get.return_value.__aenter__.side_effect = [
        mock_list_response,
        mock_kb1_response,
        mock_kb2_response,
    ]

    result = await client.find_knowledge_by_content("site", "Test KB")

    assert result == "kb-2"
    assert mock_session.get.call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_knowledge_by_content_no_match(client, mock_session):
    """Test finding knowledge base with no name matches."""
    # Setup list response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = []
    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await client.find_knowledge_by_content("site", "Test KB")

    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_knowledge_by_content_api_error(client, mock_session):
    """Test finding knowledge base with API error."""
    # Setup list response
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await client.find_knowledge_by_content("site", "Test KB")

    assert result is None


# ============================================================================
# File Upload Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_files_single(client, mock_session, tmp_dir: Path):
    """Test uploading a single file."""
    file_path = tmp_dir / "test.md"
    file_path.write_text("# Test Content")

    # Setup mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"id": "file-123"}
    mock_session.post.return_value.__aenter__.return_value = mock_response

    result = await client.upload_files([file_path])

    assert len(result) == 1
    assert result[0]["file_id"] == "file-123"
    assert result[0]["filename"] == "test.md"

    mock_session.post.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_files_batch(client, mock_session, tmp_dir: Path):
    """Test uploading multiple files in batch."""
    file_paths = [tmp_dir / f"test{i}.md" for i in range(3)]
    for path in file_paths:
        path.write_text(f"# Content {path.name}")

    # Setup mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    # We need to return different IDs for each call
    mock_response.json.side_effect = [{"id": f"file-{i}"} for i in range(3)]
    mock_session.post.return_value.__aenter__.return_value = mock_response

    result = await client.upload_files(file_paths, batch_size=2)

    assert len(result) == 3
    assert result[0]["file_id"] == "file-0"
    assert result[1]["file_id"] == "file-1"
    assert result[2]["file_id"] == "file-2"

    assert mock_session.post.call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_files_empty_list(client):
    """Test uploading empty file list."""
    result = await client.upload_files([])

    assert result is not None
    assert len(result) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_files_failure(client, mock_session, tmp_dir: Path):
    """Test file upload failure."""
    file_path = tmp_dir / "test.md"
    file_path.write_text("# Test Content")

    # Setup mock response
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text.return_value = "Server Error"
    mock_session.post.return_value.__aenter__.return_value = mock_response

    result = await client.upload_files([file_path])

    assert len(result) == 0  # No successful results


# ============================================================================
# Knowledge Base File Operations
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_files_to_knowledge_batch(client, mock_session):
    """Test adding multiple files to knowledge base."""
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"success": True}
    mock_session.post.return_value.__aenter__.return_value = mock_response

    result = await client.add_files_to_knowledge_batch("kb-123", ["file-1", "file-2"])

    assert result["success"] is True
    assert result["files_added"] == 2

    mock_session.post.assert_called_once()
    args, kwargs = mock_session.post.call_args
    assert args[0] == "http://localhost:8000/api/v1/knowledge/kb-123/files/batch/add"
    assert kwargs["json"] == [{"file_id": "file-1"}, {"file_id": "file-2"}]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_files_to_knowledge_batch_fallback(client, mock_session):
    """Test batch add failure falls back to individual."""
    # Setup mock responses
    # First call (batch) fails
    mock_batch_response = AsyncMock()
    mock_batch_response.status = 400
    mock_batch_response.text.return_value = "Batch failed"

    # Subsequent calls (individual) succeed
    mock_indiv_response = AsyncMock()
    mock_indiv_response.status = 200

    mock_session.post.return_value.__aenter__.side_effect = [
        mock_batch_response,
        mock_indiv_response,
        mock_indiv_response,
    ]

    result = await client.add_files_to_knowledge_batch("kb-123", ["file-1", "file-2"])

    assert result["success"] is True
    assert result["files_added"] == 2
    assert mock_session.post.call_count == 3  # 1 batch + 2 individual


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_files_to_knowledge_batch_exception(client, mock_session):
    """Test batch add exception falls back to individual."""
    # Setup mock responses
    # First call (batch) raises exception
    mock_session.post.return_value.__aenter__.side_effect = [
        Exception("Network error"),
        AsyncMock(status=200),  # Individual 1
        AsyncMock(status=200),  # Individual 2
    ]

    result = await client.add_files_to_knowledge_batch("kb-123", ["file-1", "file-2"])

    assert result["success"] is True
    assert result["files_added"] == 2
    assert mock_session.post.call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_files_individually_partial_success(client, mock_session):
    """Test individual file addition with partial success."""
    # Setup mock responses
    mock_success = AsyncMock(status=200)
    mock_failure = AsyncMock(status=500)
    mock_failure.text.return_value = "Error"

    mock_session.post.return_value.__aenter__.side_effect = [
        mock_success,  # file-1
        mock_failure,  # file-2
    ]

    result = await client._add_files_individually("kb-123", ["file-1", "file-2"])

    assert result["success"] is True  # At least one succeeded
    assert result["files_added"] == 1
    assert result["files_failed"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_files_individually_all_failures(client, mock_session):
    """Test individual file addition with all failures."""
    # Setup mock responses
    mock_failure = AsyncMock(status=500)
    mock_failure.text.return_value = "Error"

    mock_session.post.return_value.__aenter__.return_value = mock_failure

    result = await client._add_files_individually("kb-123", ["file-1", "file-2"])

    assert result["success"] is False
    assert result["files_added"] == 0
    assert result["files_failed"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_knowledge_files(client, mock_session):
    """Test retrieving files from knowledge base."""
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "files": [
            {"id": "file-1", "filename": "test1.md"},
            {"id": "file-2", "filename": "test2.md"},
        ]
    }
    mock_session.get.return_value.__aenter__.return_value = mock_response

    files = await client.get_knowledge_files("kb-123")

    assert len(files) == 2
    assert files[0]["id"] == "file-1"

    mock_session.get.assert_called_once()
    args, _ = mock_session.get.call_args
    assert args[0] == "http://localhost:8000/api/v1/knowledge/kb-123"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_remove_file_from_knowledge(client, mock_session):
    """Test removing file from knowledge base."""
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_session.post.return_value.__aenter__.return_value = mock_response

    result = await client.remove_file_from_knowledge("kb-123", "file-1")

    assert result is True

    mock_session.post.assert_called_once()
    args, kwargs = mock_session.post.call_args
    assert args[0] == "http://localhost:8000/api/v1/knowledge/kb-123/file/remove"
    assert kwargs["json"] == {"file_id": "file-1"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_remove_file_from_knowledge_404(client, mock_session):
    """Test removing file that is already gone (404)."""
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_session.post.return_value.__aenter__.return_value = mock_response

    result = await client.remove_file_from_knowledge("kb-123", "file-1")

    assert result is True  # Should return True for 404


@pytest.mark.unit
@pytest.mark.asyncio
async def test_remove_file_from_knowledge_failure(client, mock_session):
    """Test removing file failure."""
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text.return_value = "Server Error"
    mock_session.post.return_value.__aenter__.return_value = mock_response

    result = await client.remove_file_from_knowledge("kb-1", "file-1")

    assert result is False


# ============================================================================
# File Operations Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_file_exists_true(client, mock_session):
    """Test verifying that file exists."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await client.verify_file_exists("file-123")

    assert result is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_file_exists_false(client, mock_session):
    """Test verifying non-existent file."""
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await client.verify_file_exists("file-123")

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_file_content(client, mock_session, tmp_dir: Path):
    """Test updating file content."""
    file_path = tmp_dir / "updated.md"
    file_path.write_text("# Updated Content")

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_session.post.return_value.__aenter__.return_value = mock_response

    result = await client.update_file_content("file-123", file_path)

    assert result is True

    mock_session.post.assert_called_once()
    args, kwargs = mock_session.post.call_args
    assert args[0] == "http://localhost:8000/api/v1/files/file-123/data/content/update"
    assert kwargs["json"]["content"] == "# Updated Content"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_file_content_404(client, mock_session, tmp_dir: Path):
    """Test updating non-existent file (404)."""
    file_path = tmp_dir / "updated.md"
    file_path.write_text("# Updated Content")

    mock_response = AsyncMock()
    mock_response.status = 404
    mock_session.post.return_value.__aenter__.return_value = mock_response

    result = await client.update_file_content("file-123", file_path)

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_file(client, mock_session):
    """Test deleting a file."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_session.delete.return_value.__aenter__.return_value = mock_response

    result = await client.delete_file("file-123")

    assert result is True

    mock_session.delete.assert_called_once()
    args, _ = mock_session.delete.call_args
    assert args[0] == "http://localhost:8000/api/v1/files/file-123"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_file_404(client, mock_session):
    """Test deleting non-existent file."""
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_session.delete.return_value.__aenter__.return_value = mock_response

    result = await client.delete_file("file-123")

    assert result is True  # Should return True for 404


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_file_process_status(client, mock_session):
    """Test getting file processing status."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"status": "completed"}
    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await client.get_file_process_status("file-123")

    assert result is not None
    assert result["status"] == "completed"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_file_process_status_not_found(client, mock_session):
    """Test getting status for non-existent file."""
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await client.get_file_process_status("non-existent")

    assert result is None


# ============================================================================
# Incremental Upload Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_scrape_incrementally_new(client, mock_session, tmp_dir: Path):
    """Test incremental upload with new files."""
    # Setup files
    file_path = tmp_dir / "test.md"
    file_path.write_text("# Test")

    files_to_upload = [{"url": "http://test.com/page", "filename": "test.md"}]

    # Mock responses
    # 1. Create KB
    mock_list_kb = AsyncMock(status=200)
    mock_list_kb.json.return_value = []
    mock_create_kb = AsyncMock(status=200)
    mock_create_kb.json.return_value = {"id": "kb-1", "name": "Test KB"}

    # 2. Upload file
    mock_upload = AsyncMock(status=200)
    mock_upload.json.return_value = {"id": "file-1"}

    # 3. Get process status (wait)
    mock_status = AsyncMock(status=200)
    mock_status.json.return_value = {"status": "completed"}

    # 4. Add to KB
    mock_add = AsyncMock(status=200)
    mock_add.json.return_value = {"success": True}

    # Configure side effects
    mock_session.get.return_value.__aenter__.side_effect = [
        mock_list_kb,  # Check KB existence
        mock_status,  # Check file status
    ]
    mock_session.post.return_value.__aenter__.side_effect = [
        mock_create_kb,  # Create KB
        mock_upload,  # Upload file
        mock_add,  # Add to KB
    ]

    result = await client.upload_scrape_incrementally(
        scrape_dir=tmp_dir,
        site_name="test-site",
        knowledge_name="Test KB",
        files_to_upload=files_to_upload,
        files_to_delete=[],
        previous_file_map={},
    )

    assert result["success"] is True
    assert result["files_uploaded"] == 1
    assert result["file_id_map"]["http://test.com/page"] == "file-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_scrape_incrementally_update(client, mock_session, tmp_dir: Path):
    """Test incremental upload with updated files."""
    # Setup files
    file_path = tmp_dir / "test.md"
    file_path.write_text("# Updated")

    files_to_upload = [{"url": "http://test.com/page", "filename": "test.md"}]
    previous_map = {"http://test.com/page": "file-1"}

    # Mock responses
    # 1. Create KB (or get existing)
    mock_list_kb = AsyncMock(status=200)
    mock_list_kb.json.return_value = [{"id": "kb-1", "name": "Test KB"}]

    # 2. Verify file exists
    mock_verify = AsyncMock(status=200)

    # 3. Update file content
    mock_update = AsyncMock(status=200)

    # Configure side effects
    mock_session.get.return_value.__aenter__.side_effect = [
        mock_list_kb,  # Check KB existence
        mock_verify,  # Verify file exists
    ]
    mock_session.post.return_value.__aenter__.side_effect = [
        # No create KB (found existing)
        mock_update,  # Update content
    ]

    result = await client.upload_scrape_incrementally(
        scrape_dir=tmp_dir,
        site_name="test-site",
        knowledge_name="Test KB",
        files_to_upload=files_to_upload,
        files_to_delete=[],
        previous_file_map=previous_map,
    )

    assert result["success"] is True
    assert result["files_updated"] == 1
    assert result["file_id_map"]["http://test.com/page"] == "file-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_scrape_incrementally_delete(client, mock_session, tmp_dir: Path):
    """Test incremental upload with deletions."""
    files_to_delete = ["http://test.com/page"]
    previous_map = {"http://test.com/page": "file-1"}

    # Mock responses
    # 1. Create KB (or get existing)
    mock_list_kb = AsyncMock(status=200)
    mock_list_kb.json.return_value = [{"id": "kb-1", "name": "Test KB"}]

    # 2. Remove from KB
    mock_remove = AsyncMock(status=200)

    # 3. Delete file
    mock_delete = AsyncMock(status=200)

    mock_session.get.return_value.__aenter__.return_value = mock_list_kb
    mock_session.post.return_value.__aenter__.return_value = mock_remove
    mock_session.delete.return_value.__aenter__.return_value = mock_delete

    result = await client.upload_scrape_incrementally(
        scrape_dir=tmp_dir,
        site_name="test-site",
        knowledge_name="Test KB",
        files_to_upload=[],
        files_to_delete=files_to_delete,
        previous_file_map=previous_map,
    )

    assert result["success"] is True
    assert result["files_deleted"] == 1
    assert "http://test.com/page" not in result["file_id_map"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_scrape_incrementally_cleanup_untracked(client, mock_session, tmp_dir: Path):
    """Test incremental upload with cleanup of untracked files."""
    # Mock responses
    # 1. Create KB
    mock_list_kb = AsyncMock(status=200)
    mock_list_kb.json.return_value = [{"id": "kb-1", "name": "Test KB"}]

    # 2. Get knowledge files (find untracked)
    mock_files = AsyncMock(status=200)
    mock_files.json.return_value = {
        "files": [{"id": "file-1", "meta": {"name": "test-site/untracked.md"}}]
    }

    # 3. Remove from KB
    mock_remove = AsyncMock(status=200)

    # 4. Delete file
    mock_delete = AsyncMock(status=200)

    mock_session.get.return_value.__aenter__.side_effect = [
        mock_list_kb,  # Check KB
        mock_files,  # Get files for cleanup
    ]
    mock_session.post.return_value.__aenter__.return_value = mock_remove
    mock_session.delete.return_value.__aenter__.return_value = mock_delete

    result = await client.upload_scrape_incrementally(
        scrape_dir=tmp_dir,
        site_name="test-site",
        knowledge_name="Test KB",
        files_to_upload=[],
        files_to_delete=[],
        cleanup_untracked=True,
    )

    assert result["success"] is True
    assert result["files_deleted_untracked"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_scrape_incrementally_verification_fail(client, mock_session, tmp_dir: Path):
    """Test incremental upload where file verification fails (external delete)."""
    # Setup files
    file_path = tmp_dir / "test.md"
    file_path.write_text("# Updated")

    files_to_upload = [{"url": "http://test.com/page", "filename": "test.md"}]
    previous_map = {"http://test.com/page": "file-1"}

    # Mock responses
    # 1. Create KB
    mock_list_kb = AsyncMock(status=200)
    mock_list_kb.json.return_value = [{"id": "kb-1", "name": "Test KB"}]

    # 2. Verify file exists (FAIL - 404)
    mock_verify = AsyncMock(status=404)

    # 3. Upload as NEW file (since update verification failed)
    mock_upload = AsyncMock(status=200)
    mock_upload.json.return_value = {"id": "file-2"}

    # 4. Get status
    mock_status = AsyncMock(status=200)
    mock_status.json.return_value = {"status": "completed"}

    # 5. Add to KB
    mock_add = AsyncMock(status=200)
    mock_add.json.return_value = {"success": True}

    mock_session.get.return_value.__aenter__.side_effect = [
        mock_list_kb,  # Check KB
        mock_verify,  # Verify file (fails)
        mock_status,  # Check status
    ]
    mock_session.post.return_value.__aenter__.side_effect = [
        mock_upload,  # Upload new
        mock_add,  # Add to KB
    ]

    result = await client.upload_scrape_incrementally(
        scrape_dir=tmp_dir,
        site_name="test-site",
        knowledge_name="Test KB",
        files_to_upload=files_to_upload,
        files_to_delete=[],
        previous_file_map=previous_map,
        verify_before_update=True,
    )

    assert result["success"] is True
    assert result["files_reuploaded"] == 1
    assert result["file_id_map"]["http://test.com/page"] == "file-2"


# ============================================================================
# File Processing Wait Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wait_for_file_processing_success(client, mock_session):
    """Test waiting for file processing success."""
    # Mock status responses: processing -> completed
    mock_processing = AsyncMock(status=200)
    mock_processing.json.return_value = {"status": "processing"}

    mock_completed = AsyncMock(status=200)
    mock_completed.json.return_value = {"status": "completed"}

    mock_session.get.return_value.__aenter__.side_effect = [mock_processing, mock_completed]

    # Use a short timeout and sleep to make test fast
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await client._wait_for_file_processing(["file-1"], timeout=5)

    assert mock_session.get.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wait_for_file_processing_failure(client, mock_session):
    """Test waiting for file processing failure."""
    mock_failed = AsyncMock(status=200)
    mock_failed.json.return_value = {"status": "failed"}

    mock_session.get.return_value.__aenter__.return_value = mock_failed

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await client._wait_for_file_processing(["file-1"], timeout=5)

    # Should log warning but not raise exception
    mock_session.get.assert_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wait_for_file_processing_timeout(client, mock_session):
    """Test waiting for file processing timeout."""
    mock_processing = AsyncMock(status=200)
    mock_processing.json.return_value = {"status": "processing"}

    mock_session.get.return_value.__aenter__.return_value = mock_processing

    # Mock time to simulate timeout
    with patch("asyncio.get_event_loop") as mock_loop:
        # Start time 0, then 1, 2... until > timeout
        mock_loop.return_value.time.side_effect = [0, 1, 10, 20]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await client._wait_for_file_processing(["file-1"], timeout=5)

    # Should log warning about timeout
    mock_session.get.assert_called()


# ============================================================================
# State Reconciliation Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_match_and_reconcile_hash_match(client, mock_session):
    """Test matching files by hash (perfect match)."""
    local_metadata = {
        "files": [
            {"url": "http://test.com/1", "filename": "test1.md", "checksum": "hash1"},
            {"url": "http://test.com/2", "filename": "test2.md", "checksum": "hash2"},
        ]
    }

    # Mock remote files
    mock_response = AsyncMock(status=200)
    mock_response.json.return_value = {
        "files": [
            {"id": "file-1", "filename": "test1.md", "meta": {"name": "site/test1.md"}},
            {"id": "file-2", "filename": "test2.md", "meta": {"name": "site/test2.md"}},
        ]
    }

    # Mock file details (hashes)
    mock_details_1 = AsyncMock(status=200)
    mock_details_1.json.return_value = {
        "id": "file-1",
        "hash": "hash1",
        "meta": {"name": "site/test1.md"},
    }
    mock_details_2 = AsyncMock(status=200)
    mock_details_2.json.return_value = {
        "id": "file-2",
        "hash": "hash2",
        "meta": {"name": "site/test2.md"},
    }

    mock_session.get.return_value.__aenter__.side_effect = [
        mock_response,  # get_knowledge_files
        mock_details_1,  # get_file_details 1
        mock_details_2,  # get_file_details 2
    ]

    result = await client.match_and_reconcile("kb-1", "site", local_metadata)

    assert result["success"] is True
    assert result["matched_count"] == 2
    assert result["confidence"] == "high"
    assert result["file_id_map"]["http://test.com/1"] == "file-1"
    assert result["file_id_map"]["http://test.com/2"] == "file-2"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_match_and_reconcile_filename_match(client, mock_session):
    """Test matching files by filename (content changed)."""
    local_metadata = {
        "files": [{"url": "http://test.com/1", "filename": "test1.md", "checksum": "new_hash"}]
    }

    # Mock remote files
    mock_response = AsyncMock(status=200)
    mock_response.json.return_value = {
        "files": [{"id": "file-1", "filename": "test1.md", "meta": {"name": "site/test1.md"}}]
    }

    # Mock file details (old hash)
    mock_details = AsyncMock(status=200)
    mock_details.json.return_value = {
        "id": "file-1",
        "hash": "old_hash",
        "meta": {"name": "site/test1.md"},
    }

    mock_session.get.return_value.__aenter__.side_effect = [mock_response, mock_details]

    result = await client.match_and_reconcile("kb-1", "site", local_metadata)

    assert result["success"] is True
    assert result["matched_count"] == 1
    assert result["file_id_map"]["http://test.com/1"] == "file-1"
    # Should still be high confidence because we matched 100% of files
    assert result["confidence"] == "high"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_match_and_reconcile_no_match(client, mock_session):
    """Test no matches found."""
    local_metadata = {
        "files": [{"url": "http://test.com/1", "filename": "test1.md", "checksum": "hash1"}]
    }

    # Mock remote files (empty or different)
    mock_response = AsyncMock(status=200)
    mock_response.json.return_value = {"files": []}

    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await client.match_and_reconcile("kb-1", "site", local_metadata)

    assert result["success"] is True
    assert result["matched_count"] == 0
    assert result["confidence"] == "very_low"
    assert len(result["unmatched_local"]) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rebuild_state_inline_high_confidence(client, mock_session):
    """Test state rebuild with high confidence match."""
    local_metadata = {
        "files": [{"url": "http://test.com/1", "filename": "test1.md", "checksum": "hash1"}]
    }

    # Mock match_and_reconcile success
    with patch.object(client, "match_and_reconcile") as mock_match:
        mock_match.return_value = {
            "success": True,
            "confidence": "high",
            "matched_count": 1,
            "total_local": 1,
            "match_rate": 1.0,
            "file_id_map": {"http://test.com/1": "file-1"},
        }

        # Mock get_knowledge_files for hash lookup
        with patch.object(client, "get_knowledge_files") as mock_get_files:
            mock_get_files.return_value = [
                {"id": "file-1", "hash": "hash1", "decoded_filename": "site/test1.md"}
            ]

            result = await client._rebuild_state_inline("kb-1", "site", local_metadata)

            assert result is not None
            assert result["rebuild_confidence"] == "high"
            assert result["files_uploaded"] == 1
            assert len(result["files"]) == 1
            assert result["files"][0]["file_id"] == "file-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rebuild_state_inline_low_confidence_fail(client, mock_session):
    """Test state rebuild fails when confidence is too low."""
    local_metadata = {"files": []}

    # Mock match_and_reconcile with low confidence
    with patch.object(client, "match_and_reconcile") as mock_match:
        mock_match.return_value = {
            "success": True,
            "confidence": "low",
            "matched_count": 1,
            "total_local": 2,
        }

        # Require medium confidence (default)
        result = await client._rebuild_state_inline(
            "kb-1", "site", local_metadata, min_confidence="medium"
        )

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rebuild_state_inline_match_failure(client, mock_session):
    """Test state rebuild when matching fails."""
    local_metadata = {"files": []}

    with patch.object(client, "match_and_reconcile") as mock_match:
        mock_match.return_value = {"success": False}

        result = await client._rebuild_state_inline("kb-1", "site", local_metadata)

        assert result is None


# ============================================================================
# State Health Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_state_health_healthy(client, mock_session):
    """Test healthy state check."""
    local_metadata = {
        "files": [
            {"file_id": "file-1", "filename": "test1.md"},
            {"file_id": "file-2", "filename": "test2.md"},
        ]
    }

    # Mock remote files
    mock_response = AsyncMock(status=200)
    mock_response.json.return_value = {
        "files": [
            {"id": "file-1", "filename": "test1.md", "meta": {"name": "site/test1.md"}},
            {"id": "file-2", "filename": "test2.md", "meta": {"name": "site/test2.md"}},
        ]
    }

    # Mock file details
    mock_details_1 = AsyncMock(status=200)
    mock_details_1.json.return_value = {"id": "file-1", "meta": {"name": "site/test1.md"}}
    mock_details_2 = AsyncMock(status=200)
    mock_details_2.json.return_value = {"id": "file-2", "meta": {"name": "site/test2.md"}}

    mock_session.get.return_value.__aenter__.side_effect = [
        mock_response,
        mock_details_1,
        mock_details_2,
    ]

    result = await client.check_state_health("kb-1", "site", local_metadata)

    assert result["status"] == "healthy"
    assert result["needs_rebuild"] is False
    assert len(result["issues"]) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_state_health_missing_local(client, mock_session):
    """Test missing local state."""
    # Mock remote files
    mock_response = AsyncMock(status=200)
    mock_response.json.return_value = {"files": [{"id": "file-1"}]}
    mock_details = AsyncMock(status=200)
    mock_details.json.return_value = {"id": "file-1"}

    mock_session.get.return_value.__aenter__.side_effect = [mock_response, mock_details]

    result = await client.check_state_health("kb-1", "site", None)

    assert result["status"] == "missing"
    assert result["needs_rebuild"] is True
    assert "Local upload_status.json is missing" in result["issues"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_state_health_corrupted(client, mock_session):
    """Test corrupted state (all local files missing from remote)."""
    local_metadata = {"files": [{"file_id": "file-1", "filename": "test1.md"}]}

    # Mock remote files (empty)
    mock_response = AsyncMock(status=200)
    mock_response.json.return_value = {"files": []}

    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await client.check_state_health("kb-1", "site", local_metadata)

    assert result["status"] == "corrupted"
    assert result["needs_rebuild"] is True
    assert result["missing_remote"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_state_health_degraded(client, mock_session):
    """Test degraded state (some files missing/extra)."""
    local_metadata = {
        "files": [
            {"file_id": "file-1", "filename": "test1.md"},
            {"file_id": "file-2", "filename": "test2.md"},
        ]
    }

    # Mock remote files (file-1 missing, file-3 extra)
    mock_response = AsyncMock(status=200)
    mock_response.json.return_value = {
        "files": [
            {"id": "file-2", "filename": "test2.md", "meta": {"name": "site/test2.md"}},
            {"id": "file-3", "filename": "test3.md", "meta": {"name": "site/test3.md"}},
        ]
    }

    mock_details_2 = AsyncMock(status=200)
    mock_details_2.json.return_value = {"id": "file-2", "meta": {"name": "site/test2.md"}}
    mock_details_3 = AsyncMock(status=200)
    mock_details_3.json.return_value = {"id": "file-3", "meta": {"name": "site/test3.md"}}

    mock_session.get.return_value.__aenter__.side_effect = [
        mock_response,
        mock_details_2,
        mock_details_3,
    ]

    result = await client.check_state_health("kb-1", "site", local_metadata)

    assert result["status"] == "degraded"
    assert result["needs_rebuild"] is False
    assert result["missing_remote"] == 1  # file-1
    assert result["extra_remote"] == 1  # file-3


# ============================================================================
# Full Upload Workflow Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_scrape_to_knowledge_success(client, mock_session, tmp_dir: Path):
    """Test full upload workflow success."""
    # Setup files
    file_path = tmp_dir / "test.md"
    file_path.write_text("# Test")

    # Mock responses
    # 1. Create KB
    mock_list_kb = AsyncMock(status=200)
    mock_list_kb.json.return_value = []
    mock_create_kb = AsyncMock(status=200)
    mock_create_kb.json.return_value = {"id": "kb-1", "name": "Test KB"}

    # 2. Upload file
    mock_upload = AsyncMock(status=200)
    mock_upload.json.return_value = {"id": "file-1"}

    # 3. Get process status
    mock_status = AsyncMock(status=200)
    mock_status.json.return_value = {"status": "completed"}

    # 4. Add to KB
    mock_add = AsyncMock(status=200)
    mock_add.json.return_value = {"success": True, "files_added": 1}

    mock_session.get.return_value.__aenter__.side_effect = [
        mock_list_kb,  # Check KB existence
        mock_status,  # Check file status
    ]
    mock_session.post.return_value.__aenter__.side_effect = [
        mock_create_kb,  # Create KB
        mock_upload,  # Upload file
        mock_add,  # Add to KB
    ]

    result = await client.upload_scrape_to_knowledge(
        scrape_dir=tmp_dir, site_name="test-site", knowledge_name="Test KB"
    )

    assert result["success"] is True
    assert result["files_uploaded"] == 1
    assert result["files_added_to_knowledge"] == 1
    assert result["knowledge_id"] == "kb-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_scrape_to_knowledge_no_files(client, tmp_dir: Path):
    """Test full upload with no files."""
    result = await client.upload_scrape_to_knowledge(
        scrape_dir=tmp_dir, site_name="test-site", knowledge_name="Test KB"
    )

    assert "error" in result
    assert result["error"] == "No markdown files found to upload"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_scrape_to_knowledge_upload_fail(client, mock_session, tmp_dir: Path):
    """Test full upload with file upload failure."""
    file_path = tmp_dir / "test.md"
    file_path.write_text("# Test")

    # Mock responses
    # 1. Create KB
    mock_list_kb = AsyncMock(status=200)
    mock_list_kb.json.return_value = []
    mock_create_kb = AsyncMock(status=200)
    mock_create_kb.json.return_value = {"id": "kb-1", "name": "Test KB"}

    # 2. Upload file (fail)
    mock_upload = AsyncMock(status=500)
    mock_upload.text.return_value = "Error"

    mock_session.get.return_value.__aenter__.return_value = mock_list_kb
    mock_session.post.return_value.__aenter__.side_effect = [mock_create_kb, mock_upload]

    result = await client.upload_scrape_to_knowledge(
        scrape_dir=tmp_dir, site_name="test-site", knowledge_name="Test KB"
    )

    assert "error" in result
    assert result["error"] == "Failed to upload files"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upload_scrape_to_knowledge_processing_timeout(client, mock_session, tmp_dir: Path):
    """Test full upload with processing timeout."""
    file_path = tmp_dir / "test.md"
    file_path.write_text("# Test")

    # Mock responses
    # 1. Create KB
    mock_create_kb = AsyncMock(status=200)
    mock_create_kb.json.return_value = {"id": "kb-1", "name": "Test KB"}

    # 2. Upload file
    mock_upload = AsyncMock(status=200)
    mock_upload.json.return_value = {"id": "file-1"}

    # 3. Processing status (stuck in processing)
    mock_status = AsyncMock(status=200)
    mock_status.json.return_value = {"status": "processing"}

    # 4. Add to KB (should still happen)
    mock_add = AsyncMock(status=200)
    mock_add.json.return_value = {"success": True}

    # Configure side effects
    mock_session.get.return_value.__aenter__.side_effect = [
        AsyncMock(status=200, json=AsyncMock(return_value=[])),  # List KB
        mock_status,  # Check status (repeated)
    ]
    mock_session.post.return_value.__aenter__.side_effect = [
        mock_create_kb,
        mock_upload,
        mock_add,
    ]

    # Mock time and sleep to simulate timeout
    with patch("asyncio.get_event_loop") as mock_loop:
        mock_loop.return_value.time.side_effect = [0, 100]  # Immediate timeout
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.upload_scrape_to_knowledge(
                scrape_dir=tmp_dir, site_name="test-site", knowledge_name="Test KB"
            )

    assert result["success"] is True
    assert result["files_uploaded"] == 1


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_404_handling(client, mock_session):
    """Test handling of 404 API errors."""
    mock_response = AsyncMock(status=404)
    mock_session.get.return_value.__aenter__.return_value = mock_response

    # Should return None/False, not raise exception
    assert await client.get_knowledge_files("kb-1") is None
    assert await client.verify_file_exists("file-1") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_500_handling(client, mock_session):
    """Test handling of 500 API errors."""
    mock_response = AsyncMock(status=500)
    mock_response.text.return_value = "Internal Server Error"
    mock_session.post.return_value.__aenter__.return_value = mock_response

    # Should return None/False and log error
    assert await client.create_knowledge("Test") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_network_timeout_handling(client, mock_session):
    """Test handling of network timeouts."""
    mock_session.get.side_effect = Exception("Timeout")

    assert await client.test_connection() is False
