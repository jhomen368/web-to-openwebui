"""
Mock OpenWebUI client for testing.

Provides MockOpenWebUIClient that implements the same interface as the real
OpenWebUIClient but with configurable mock behavior.
"""

from pathlib import Path
from typing import Any


class MockOpenWebUIClient:
    """
    Mock OpenWebUI client for testing.

    Simulates OpenWebUI API responses without requiring a real server.
    Can be configured to return specific responses or raise exceptions.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str = "test-key-123",
        simulate_failures: bool = False,
    ):
        """
        Initialize mock client.

        Args:
            base_url: Base URL (stored but not used)
            api_key: API key (stored but not used)
            simulate_failures: If True, simulate API failures
        """
        self.base_url = base_url
        self.api_key = api_key
        self.simulate_failures = simulate_failures

        # State tracking for tests
        self.call_history: list[dict[str, Any]] = []
        self.files: dict[str, dict[str, Any]] = {}
        self.knowledge_bases: dict[str, dict[str, Any]] = {}
        self.file_id_counter = 0
        self.kb_id_counter = 0

    async def test_connection(self) -> bool:
        """Test connection to OpenWebUI."""
        self._record_call("test_connection")
        return not self.simulate_failures

    async def create_knowledge(
        self,
        name: str,
        description: str = "",
        user_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Create knowledge base.

        Args:
            name: Knowledge base name
            description: Knowledge base description
            user_id: User ID (optional)

        Returns:
            Dict with knowledge_id and metadata, or None on failure
        """
        self._record_call("create_knowledge", {"name": name, "description": description})

        if self.simulate_failures:
            return None

        kb_id = f"kb-{self.kb_id_counter}"
        self.kb_id_counter += 1

        kb_data = {
            "id": kb_id,
            "name": name,
            "description": description,
            "user_id": user_id or "default-user",
        }
        self.knowledge_bases[kb_id] = kb_data
        return kb_data

    async def upload_files(
        self,
        file_paths: list[Path],
        **kwargs,
    ) -> dict[str, Any] | None:
        """
        Upload files.

        Args:
            file_paths: List of file paths to upload
            **kwargs: Additional arguments

        Returns:
            Dict with file_ids and status, or None on failure
        """
        self._record_call("upload_files", {"num_files": len(file_paths)})

        if self.simulate_failures:
            return None

        file_ids = []
        for file_path in file_paths:
            file_id = f"file-{self.file_id_counter}"
            self.file_id_counter += 1

            self.files[file_id] = {
                "id": file_id,
                "name": file_path.name,
                "path": str(file_path),
                "size": 1024,  # Mock size
            }
            file_ids.append(file_id)

        return {
            "file_ids": file_ids,
            "succeeded": len(file_ids),
            "failed": 0,
        }

    async def add_files_to_knowledge_batch(
        self,
        knowledge_id: str,
        file_ids: list[str],
        **kwargs,
    ) -> dict[str, Any]:
        """
        Add files to knowledge base in batch.

        Args:
            knowledge_id: Knowledge base ID
            file_ids: List of file IDs to add
            **kwargs: Additional arguments

        Returns:
            Dict with status and count
        """
        self._record_call(
            "add_files_to_knowledge_batch",
            {"knowledge_id": knowledge_id, "num_files": len(file_ids)},
        )

        if self.simulate_failures:
            return {"succeeded": 0, "failed": len(file_ids)}

        # Track files in knowledge base
        if knowledge_id not in self.knowledge_bases:
            self.knowledge_bases[knowledge_id] = {
                "id": knowledge_id,
                "files": [],
            }

        # Initialize files list if it doesn't exist
        if "files" not in self.knowledge_bases[knowledge_id]:
            self.knowledge_bases[knowledge_id]["files"] = []

        self.knowledge_bases[knowledge_id]["files"].extend(file_ids)

        return {
            "succeeded": len(file_ids),
            "failed": 0,
        }

    async def get_knowledge_files(
        self,
        knowledge_id: str,
    ) -> list[dict[str, Any]] | None:
        """
        Get files in knowledge base.

        Args:
            knowledge_id: Knowledge base ID

        Returns:
            List of file dicts, or None on failure
        """
        self._record_call("get_knowledge_files", {"knowledge_id": knowledge_id})

        if self.simulate_failures:
            return None

        if knowledge_id not in self.knowledge_bases:
            return []

        kb = self.knowledge_bases[knowledge_id]
        files = []
        for file_id in kb.get("files", []):
            if file_id in self.files:
                files.append(self.files[file_id])

        return files

    async def verify_file_exists(self, file_id: str) -> bool:
        """
        Verify file exists.

        Args:
            file_id: File ID to check

        Returns:
            bool: True if file exists
        """
        self._record_call("verify_file_exists", {"file_id": file_id})
        return file_id in self.files

    async def update_file_content(
        self,
        file_id: str,
        file_path: Path,
    ) -> bool:
        """
        Update file content.

        Args:
            file_id: File ID to update
            file_path: Path to new content

        Returns:
            bool: True on success
        """
        self._record_call("update_file_content", {"file_id": file_id})

        if self.simulate_failures or file_id not in self.files:
            return False

        self.files[file_id]["updated"] = True
        return True

    async def remove_file_from_knowledge(
        self,
        knowledge_id: str,
        file_id: str,
    ) -> bool:
        """
        Remove file from knowledge base.

        Args:
            knowledge_id: Knowledge base ID
            file_id: File ID to remove

        Returns:
            bool: True on success
        """
        self._record_call(
            "remove_file_from_knowledge",
            {"knowledge_id": knowledge_id, "file_id": file_id},
        )

        if self.simulate_failures:
            return False

        if knowledge_id in self.knowledge_bases:
            files = self.knowledge_bases[knowledge_id].get("files", [])
            if file_id in files:
                files.remove(file_id)

        return True

    async def delete_file(self, file_id: str) -> bool:
        """
        Delete file.

        Args:
            file_id: File ID to delete

        Returns:
            bool: True on success
        """
        self._record_call("delete_file", {"file_id": file_id})

        if self.simulate_failures or file_id not in self.files:
            return False

        del self.files[file_id]
        return True

    async def get_file_process_status(
        self,
        file_id: str,
    ) -> dict[str, Any] | None:
        """
        Get file processing status.

        Args:
            file_id: File ID to check

        Returns:
            Dict with status info, or None on failure
        """
        self._record_call("get_file_process_status", {"file_id": file_id})

        if self.simulate_failures or file_id not in self.files:
            return None

        return {
            "file_id": file_id,
            "status": "completed",
            "processed_at": "2025-11-20T01:15:00Z",
        }

    def _record_call(self, method_name: str, args: dict[str, Any] | None = None) -> None:
        """
        Record method call for testing.

        Args:
            method_name: Name of method called
            args: Arguments passed to method
        """
        self.call_history.append(
            {
                "method": method_name,
                "args": args or {},
            }
        )

    def get_call_count(self, method_name: str) -> int:
        """
        Get count of calls to a specific method.

        Args:
            method_name: Method name to check

        Returns:
            int: Number of calls
        """
        return sum(1 for call in self.call_history if call["method"] == method_name)

    def get_calls_to(self, method_name: str) -> list[dict[str, Any]]:
        """
        Get all calls to a specific method.

        Args:
            method_name: Method name to check

        Returns:
            List of call records
        """
        return [call for call in self.call_history if call["method"] == method_name]

    def reset(self) -> None:
        """Reset mock state for next test."""
        self.call_history.clear()
        self.files.clear()
        self.knowledge_bases.clear()
        self.file_id_counter = 0
        self.kb_id_counter = 0
