"""
Open Web UI API client for uploading scraped content.
"""

import asyncio
import json
import logging
import urllib.parse
from pathlib import Path
from typing import cast

import aiohttp
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

logger = logging.getLogger(__name__)


class OpenWebUIClient:
    """Client for interacting with Open Web UI API."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
        }

    async def upload_files(
        self,
        file_paths: list[Path],
        site_name: str | None = None,
        base_content_dir: Path | None = None,
        batch_size: int = 10,
    ) -> list[dict]:
        """
        Upload files to Open Web UI and return file info with IDs.
        Files are uploaded to /api/v1/files/ endpoint.

        Args:
            file_paths: List of file paths to upload
            site_name: Optional site identifier for folder prefix
            base_content_dir: Base directory to calculate relative paths from
            batch_size: Number of files to upload per batch

        Returns:
            List of dicts with 'file_id', 'path', 'filename', and 'upload_filename'
        """
        if site_name:
            logger.info(f"Uploading {len(file_paths)} files to {site_name}/ folder")
        else:
            logger.info(f"Uploading {len(file_paths)} files to Open Web UI")

        file_results = []

        async with aiohttp.ClientSession() as session:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            ) as progress:
                task = progress.add_task("Uploading files...", total=len(file_paths))

                # Process in batches
                for i in range(0, len(file_paths), batch_size):
                    batch = file_paths[i : i + batch_size]

                    # Upload batch concurrently with site prefix
                    tasks = [
                        self._upload_file(session, fp, site_name, base_content_dir) for fp in batch
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for fp, result in zip(batch, results, strict=False):
                        if isinstance(result, Exception):
                            logger.error(f"Upload error for {fp.name}: {result}")
                        elif result:
                            # Calculate upload filename for tracking
                            # Use underscores instead of forward slashes to match upload behavior
                            if site_name and base_content_dir:
                                try:
                                    relative_path = fp.relative_to(base_content_dir)
                                    upload_filename = f"{site_name}_{relative_path}".replace(
                                        "\\", "_"
                                    ).replace("/", "_")
                                except ValueError:
                                    upload_filename = f"{site_name}_{fp.name}"
                            else:
                                upload_filename = fp.name

                            file_results.append(
                                {
                                    "file_id": result,
                                    "path": str(fp),
                                    "filename": fp.name,
                                    "upload_filename": upload_filename,
                                }
                            )

                    progress.update(task, advance=len(batch))

                    # Small delay between batches
                    await asyncio.sleep(0.5)

        logger.info(f"Successfully uploaded {len(file_results)}/{len(file_paths)} files")
        return file_results

    async def _upload_file(
        self,
        session: aiohttp.ClientSession,
        file_path: Path,
        site_name: str | None = None,
        base_content_dir: Path | None = None,
    ) -> str | None:
        """
        Upload a single file to /api/v1/files/ and return the file_id.

        Args:
            session: aiohttp session
            file_path: Path to the file to upload
            site_name: Optional site identifier for folder prefix
            base_content_dir: Base directory to calculate relative paths from

        Returns:
            file_id if successful, None otherwise
        """
        try:
            url = f"{self.base_url}/api/v1/files/"

            # Construct filename with site folder if provided
            # Note: OpenWebUI URL-encodes forward slashes, so use underscores for folder structure
            if site_name and base_content_dir:
                # Get relative path from content directory for nested structure
                try:
                    relative_path = file_path.relative_to(base_content_dir)
                    # Replace path separators with underscores to preserve folder hierarchy
                    # This prevents OpenWebUI from URL-encoding forward slashes as %2F
                    upload_filename = f"{site_name}_{relative_path}".replace("\\", "_").replace(
                        "/", "_"
                    )
                except ValueError:
                    # Not relative to base_content_dir, use plain filename with site prefix
                    upload_filename = f"{site_name}_{file_path.name}"
            else:
                upload_filename = file_path.name

            # Create multipart form data with file
            data = aiohttp.FormData()
            content = file_path.read_bytes()
            data.add_field("file", content, filename=upload_filename, content_type="text/markdown")

            async with session.post(url, headers=self.headers, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    file_id = cast(str | None, result.get("id"))
                    logger.debug(f"✓ Uploaded: {upload_filename} (ID: {file_id})")
                    return file_id
                else:
                    error_text = await response.text()
                    logger.error(
                        f"✗ Failed to upload {upload_filename}: {response.status} - {error_text}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error uploading {file_path}: {e}")
            return None

    async def update_file_content(self, file_id: str, file_path: Path) -> bool:
        """
        Update an existing file's content.
        Uses /api/v1/files/{id}/data/content/update endpoint.
        """
        try:
            url = f"{self.base_url}/api/v1/files/{file_id}/data/content/update"

            # Read new content
            content = file_path.read_text(encoding="utf-8")

            payload = {"content": content}

            async with (
                aiohttp.ClientSession() as session,
                session.post(url, headers=self.headers, json=payload) as response,
            ):
                if response.status == 200:
                    logger.debug(f"✓ Updated file {file_id}: {file_path.name}")
                    return True
                elif response.status == 404:
                    logger.warning(f"⚠ File {file_id} not found (deleted externally)")
                    return False  # Caller will re-upload as new
                else:
                    error_text = await response.text()
                    logger.error(
                        f"✗ Failed to update file {file_id}: {response.status} - {error_text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error updating file {file_id}: {e}")
            return False

    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from Open Web UI.
        Uses DELETE /api/v1/files/{id} endpoint.
        """
        try:
            url = f"{self.base_url}/api/v1/files/{file_id}"

            async with (
                aiohttp.ClientSession() as session,
                session.delete(url, headers=self.headers) as response,
            ):
                if response.status == 200:
                    logger.debug(f"✓ Deleted file {file_id}")
                    return True
                elif response.status == 404:
                    logger.debug(f"⚠ File {file_id} already deleted (OK)")
                    return True  # Consider success - file is gone
                else:
                    error_text = await response.text()
                    logger.error(
                        f"✗ Failed to delete file {file_id}: {response.status} - {error_text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            return False

    async def verify_file_exists(self, file_id: str) -> bool:
        """
        Check if a file exists in OpenWebUI storage.

        Args:
            file_id: File ID to check

        Returns:
            True if file exists, False if deleted (404)
        """
        try:
            url = f"{self.base_url}/api/v1/files/{file_id}"

            async with (
                aiohttp.ClientSession() as session,
                session.get(url, headers=self.headers) as response,
            ):
                if response.status == 200:
                    return True
                elif response.status == 404:
                    return False
                else:
                    # Other errors - assume file might exist to avoid false deletions
                    logger.warning(f"Unexpected status {response.status} checking file {file_id}")
                    return True
        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return True  # Assume exists on error to avoid false deletions

    async def get_file_process_status(self, file_id: str) -> dict | None:
        """
        Get file processing status.
        Uses GET /api/v1/files/{id}/process/status endpoint.
        """
        try:
            url = f"{self.base_url}/api/v1/files/{file_id}/process/status"

            async with (
                aiohttp.ClientSession() as session,
                session.get(url, headers=self.headers) as response,
            ):
                if response.status == 200:
                    return cast(dict | None, await response.json())
                else:
                    logger.debug(f"Could not get status for file {file_id}")
                    return None

        except Exception as e:
            logger.debug(f"Error getting file status {file_id}: {e}")
            return None

    async def create_knowledge(self, name: str, description: str = "") -> dict | None:
        """
        Create or get existing knowledge collection.
        Returns knowledge dict with id.
        """
        try:
            # First, try to list existing knowledge to see if it exists
            existing = await self._get_knowledge_by_name(name)
            if existing:
                logger.info(f"Using existing knowledge: {name} (ID: {existing['id']})")
                return existing

            # Create new knowledge
            url = f"{self.base_url}/api/v1/knowledge/create"

            payload = {
                "name": name,
                "description": description,
            }

            async with (
                aiohttp.ClientSession() as session,
                session.post(url, headers=self.headers, json=payload) as response,
            ):
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Created knowledge: {name} (ID: {result.get('id')})")
                    return cast(dict | None, result)
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create knowledge: {response.status} - {error_text}")
                    return None

        except Exception as e:
            logger.error(f"Error creating knowledge: {e}")
            return None

    async def _get_knowledge_by_name(self, name: str) -> dict | None:
        """Try to find existing knowledge by name."""
        try:
            url = f"{self.base_url}/api/v1/knowledge/"

            async with (
                aiohttp.ClientSession() as session,
                session.get(url, headers=self.headers) as response,
            ):
                if response.status == 200:
                    result = await response.json()
                    # Response is a list of knowledge items
                    if isinstance(result, list):
                        knowledge_list = result
                    else:
                        knowledge_list = result.get("data") or result.get("items", [])

                    for item in knowledge_list:
                        if item.get("name") == name:
                            return cast(dict | None, item)
                    return None
                else:
                    return None

        except Exception as e:
            logger.debug(f"Could not fetch existing knowledge: {e}")
            return None

    async def find_knowledge_by_content(self, site_name: str, knowledge_name: str) -> str | None:
        """
        Find knowledge base ID by checking which one contains files from this site.

        This is used for automated disaster recovery when knowledge_id is not configured.
        Since OpenWebUI allows duplicate knowledge base names, we identify the correct KB
        by checking which one actually contains our site's files.

        Args:
            site_name: Site name to look for (folder prefix)
            knowledge_name: Knowledge base name to search for

        Returns:
            knowledge_id if found, None otherwise
        """
        try:
            # Get all knowledge bases
            url = f"{self.base_url}/api/v1/knowledge/"

            async with (
                aiohttp.ClientSession() as session,
                session.get(url, headers=self.headers) as response,
            ):
                if response.status != 200:
                    return None

                result = await response.json()
                if isinstance(result, list):
                    knowledge_list = result
                else:
                    knowledge_list = result.get("data") or result.get("items", [])

                # Find all KBs with matching name
                matching_kbs = [kb for kb in knowledge_list if kb.get("name") == knowledge_name]

                if len(matching_kbs) == 0:
                    logger.debug(f"No knowledge bases found with name: {knowledge_name}")
                    return None

                if len(matching_kbs) == 1:
                    # Only one match, use it
                    kb_id = cast(str, matching_kbs[0]["id"])
                    logger.info(f"Found unique knowledge base: {knowledge_name} (ID: {kb_id})")
                    return kb_id

                # Multiple KBs with same name - find by content
                logger.info(
                    f"Found {len(matching_kbs)} knowledge bases named '{knowledge_name}', checking content..."
                )

                for kb in matching_kbs:
                    kb_id = cast(str, kb["id"])
                    # Check if this KB has files in our site folder
                    files = await self.get_knowledge_files(kb_id, site_folder=site_name)

                    if files and len(files) > 0:
                        logger.info(
                            f"Found knowledge base with {len(files)} files in {site_name}/ folder (ID: {kb_id})"
                        )
                        return kb_id

                # None of the KBs have our files - use first one as default
                logger.warning(
                    f"No knowledge base contains files from {site_name}/, using first match"
                )
                return cast(str, matching_kbs[0]["id"])

        except Exception as e:
            logger.error(f"Error finding knowledge by content: {e}")
            return None

    async def add_files_to_knowledge_batch(self, knowledge_id: str, file_ids: list[str]) -> dict:
        """
        Add uploaded files to a knowledge collection in batch.
        Uses POST /api/v1/knowledge/{id}/files/batch/add endpoint.
        """
        logger.info(f"Adding {len(file_ids)} files to knowledge {knowledge_id} (batch)")

        try:
            url = f"{self.base_url}/api/v1/knowledge/{knowledge_id}/files/batch/add"

            # API expects a list of objects with file_id field
            payload = [{"file_id": fid} for fid in file_ids]

            async with (
                aiohttp.ClientSession() as session,
                session.post(url, headers=self.headers, json=payload) as response,
            ):
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✓ Batch added {len(file_ids)} files to knowledge")
                    return {
                        "success": True,
                        "knowledge_id": knowledge_id,
                        "files_added": len(file_ids),
                        "result": result,
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"✗ Failed batch add: {response.status} - {error_text}")
                    # Fall back to individual adds
                    return await self._add_files_individually(knowledge_id, file_ids)

        except Exception as e:
            logger.error(f"Error in batch add, falling back to individual: {e}")
            return await self._add_files_individually(knowledge_id, file_ids)

    async def _add_files_individually(self, knowledge_id: str, file_ids: list[str]) -> dict:
        """Fallback: Add files individually (legacy method)."""
        logger.info(f"Adding {len(file_ids)} files individually (fallback)")

        success_count = 0
        failed_count = 0

        async with aiohttp.ClientSession() as session:
            for file_id in file_ids:
                success = await self._add_file_to_knowledge(session, knowledge_id, file_id)
                if success:
                    success_count += 1
                else:
                    failed_count += 1

                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)

        logger.info(f"Added {success_count}/{len(file_ids)} files to knowledge")

        return {
            "success": success_count > 0,
            "knowledge_id": knowledge_id,
            "files_added": success_count,
            "files_failed": failed_count,
        }

    async def add_files_to_knowledge(self, knowledge_id: str, file_ids: list[str]) -> dict:
        """Add uploaded files to a knowledge collection."""
        logger.info(f"Adding {len(file_ids)} files to knowledge {knowledge_id}")

        success_count = 0
        failed_count = 0

        async with aiohttp.ClientSession() as session:
            for file_id in file_ids:
                success = await self._add_file_to_knowledge(session, knowledge_id, file_id)
                if success:
                    success_count += 1
                else:
                    failed_count += 1

                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)

        logger.info(f"Added {success_count}/{len(file_ids)} files to knowledge")

        return {
            "knowledge_id": knowledge_id,
            "total_files": len(file_ids),
            "success": success_count,
            "failed": failed_count,
        }

    async def _add_file_to_knowledge(
        self, session: aiohttp.ClientSession, knowledge_id: str, file_id: str
    ) -> bool:
        """Add a single file to knowledge collection."""
        try:
            url = f"{self.base_url}/api/v1/knowledge/{knowledge_id}/file/add"

            payload = {"file_id": file_id}

            async with session.post(url, headers=self.headers, json=payload) as response:
                if response.status == 200:
                    logger.debug(f"✓ Added file {file_id} to knowledge")
                    return True
                else:
                    error_text = await response.text()
                    logger.warning(
                        f"Failed to add file {file_id}: {response.status} - {error_text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error adding file {file_id} to knowledge: {e}")
            return False

    async def remove_file_from_knowledge(self, knowledge_id: str, file_id: str) -> bool:
        """
        Remove a file from knowledge collection.
        Uses POST /api/v1/knowledge/{id}/file/remove endpoint.

        Note: In current OpenWebUI, this also deletes the file from storage.
        """
        try:
            url = f"{self.base_url}/api/v1/knowledge/{knowledge_id}/file/remove"

            payload = {"file_id": file_id}

            async with (
                aiohttp.ClientSession() as session,
                session.post(url, headers=self.headers, json=payload) as response,
            ):
                if response.status == 200:
                    logger.debug(f"✓ Removed file {file_id} from knowledge")
                    return True
                elif response.status == 404:
                    logger.debug(f"⚠ File {file_id} already gone (OK)")
                    return True  # Consider success - file is already removed
                else:
                    error_text = await response.text()
                    logger.warning(
                        f"Failed to remove file {file_id}: {response.status} - {error_text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error removing file {file_id} from knowledge: {e}")
            return False

    async def get_knowledge_files(
        self, knowledge_id: str, include_hashes: bool = False, site_folder: str | None = None
    ) -> list[dict] | None:
        """
        Get list of files currently in a knowledge base.

        Args:
            knowledge_id: Knowledge base ID
            include_hashes: If True, fetch detailed file info including hashes
            site_folder: If provided, only return files in this folder (e.g., 'monsterhunter/')

        Returns:
            List of file dicts with id, filename, hash (if requested), etc., or None on error
        """
        try:
            # Updated endpoint for retrieving files
            url = f"{self.base_url}/api/v1/knowledge/{knowledge_id}/files"

            async with (
                aiohttp.ClientSession() as session,
                session.get(url, headers=self.headers) as response,
            ):
                if response.status == 200:
                    result = await response.json()
                    # Extract file list from response (new format: {"items": [...]})
                    # Fallback to "files" for backward compatibility if needed
                    files = result.get("items") or result.get("files")

                    if isinstance(files, dict):
                        files = files.get("data", []) if files else []
                    elif not isinstance(files, list):
                        files = []

                    # If hashes requested, fetch detailed info for each file
                    if include_hashes and files:
                        detailed_files = []
                        for f in files:
                            file_id = f.get("id")
                            if file_id:
                                detailed = await self._get_file_details(session, file_id)
                                if detailed:
                                    detailed_files.append(detailed)
                                else:
                                    # Fall back to basic info if detailed fetch fails
                                    detailed_files.append(f)
                        files = detailed_files

                    # Filter by site folder if specified
                    if site_folder:
                        # Normalize folder format (ensure trailing underscore for new format)
                        if not site_folder.endswith("_"):
                            site_folder = f"{site_folder}_"

                        filtered_files = []
                        # Add None check before iteration
                        if files is not None:
                            for f in files:
                                # Get filename from meta.name and decode it
                                filename_encoded = f.get("meta", {}).get(
                                    "name", f.get("filename", "")
                                )
                                filename = (
                                    urllib.parse.unquote(filename_encoded)
                                    if filename_encoded
                                    else ""
                                )

                                # Check if file is in the specified folder (underscore-based naming)
                                if filename.startswith(site_folder):
                                    # Store decoded filename for easier comparison
                                    f["decoded_filename"] = filename
                                    filtered_files.append(f)

                            logger.debug(
                                f"Filtered {len(filtered_files)}/{len(files)} files in folder {site_folder}"
                            )
                            return filtered_files
                        return []

                    return cast(list[dict] | None, files)
                else:
                    logger.warning(f"Failed to get knowledge files: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting knowledge files: {e}")
            return None

    async def _get_file_details(self, session: aiohttp.ClientSession, file_id: str) -> dict | None:
        """
        Get detailed file information including hash.

        Args:
            session: aiohttp session
            file_id: File ID to fetch

        Returns:
            File dict with all details including hash, or None on error
        """
        try:
            url = f"{self.base_url}/api/v1/files/{file_id}"

            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    file_data = await response.json()
                    return cast(dict | None, file_data)
                else:
                    logger.debug(f"Could not get details for file {file_id}: {response.status}")
                    return None
        except Exception as e:
            logger.debug(f"Error getting file details {file_id}: {e}")
            return None

    async def check_state_health(
        self, knowledge_id: str, site_name: str, local_metadata: dict | None = None
    ) -> dict:
        """
        Check health of local upload state vs remote OpenWebUI state.

        Args:
            knowledge_id: Knowledge base ID to check
            site_name: Site name for folder filtering
            local_metadata: Optional local metadata dict (from current/metadata.json)

        Returns:
            Dict with health status, including:
            - status: 'healthy', 'missing', 'corrupted', 'degraded'
            - needs_rebuild: bool
            - issues: list of issues found
            - remote_file_count: count of remote files
            - local_file_count: count of local files (if metadata provided)
        """
        logger.info(f"Checking state health for {site_name}...")

        issues = []

        # Check if we can access remote knowledge base
        remote_files = await self.get_knowledge_files(
            knowledge_id, include_hashes=True, site_folder=site_name
        )

        if remote_files is None:
            return {
                "status": "error",
                "needs_rebuild": False,
                "issues": ["Cannot access remote knowledge base"],
                "remote_file_count": 0,
                "local_file_count": 0,
            }

        remote_count = len(remote_files)
        logger.info(f"Remote: {remote_count} files in {site_name}/ folder")

        # If no local metadata provided, state is missing
        if not local_metadata:
            return {
                "status": "missing",
                "needs_rebuild": True,
                "issues": ["Local upload_status.json is missing"],
                "remote_file_count": remote_count,
                "local_file_count": 0,
                "recommendation": "Run rebuild-state to reconstruct from remote",
            }

        local_files = local_metadata.get("files", [])
        local_count = len(local_files)
        logger.info(f"Local: {local_count} files tracked")

        # Build maps for comparison
        local_file_ids = {f.get("file_id") for f in local_files if "file_id" in f}
        remote_file_ids = {f["id"] for f in remote_files}

        # Check for discrepancies
        missing_remote = local_file_ids - remote_file_ids
        extra_remote = remote_file_ids - local_file_ids

        if missing_remote:
            issues.append(f"{len(missing_remote)} files in local state but missing from remote")

        if extra_remote:
            issues.append(f"{len(extra_remote)} files in remote but not in local state")

        # Determine overall health
        if not issues:
            status = "healthy"
            needs_rebuild = False
        elif len(missing_remote) == local_count:
            # All local files are missing - complete state loss
            status = "corrupted"
            needs_rebuild = True
        elif missing_remote or extra_remote:
            status = "degraded"
            needs_rebuild = False  # Can be fixed with sync, not full rebuild
        else:
            status = "healthy"
            needs_rebuild = False

        return {
            "status": status,
            "needs_rebuild": needs_rebuild,
            "issues": issues,
            "remote_file_count": remote_count,
            "local_file_count": local_count,
            "missing_remote": len(missing_remote),
            "extra_remote": len(extra_remote),
            "recommendation": (
                "Run rebuild-state command" if needs_rebuild else "Run sync --fix to resolve"
            ),
        }

    async def match_and_reconcile(
        self, knowledge_id: str, site_name: str, local_metadata: dict
    ) -> dict:
        """
        Match remote files with local files using hash comparison.
        Reconstructs file_id mappings from OpenWebUI state.

        Args:
            knowledge_id: Knowledge base ID
            site_name: Site name for folder filtering
            local_metadata: Local metadata dict with file info and hashes

        Returns:
            Dict with:
            - success: bool
            - file_id_map: Dict mapping URLs to file_ids
            - matched_count: Number of files matched by hash
            - unmatched_local: Files in local but not found in remote
            - unmatched_remote: Files in remote but not in local
            - confidence: 'high', 'medium', 'low' based on match rate
        """
        logger.info(f"Matching local files with remote state for {site_name}...")

        # Get remote files with hashes
        remote_files = await self.get_knowledge_files(
            knowledge_id, include_hashes=True, site_folder=site_name
        )

        if remote_files is None:
            return {
                "success": False,
                "error": "Failed to fetch remote files",
                "file_id_map": {},
                "matched_count": 0,
                "confidence": "none",
            }

        logger.info(f"Found {len(remote_files)} remote files")

        # Build hash -> file_id map from remote
        remote_hash_map = {}
        for f in remote_files:
            file_hash = f.get("hash")
            file_id = f.get("id")
            if file_hash and file_id:
                remote_hash_map[file_hash] = {
                    "file_id": file_id,
                    "filename": f.get("decoded_filename", f.get("filename", "unknown")),
                }

        logger.info(f"Built hash map for {len(remote_hash_map)} remote files")

        # Build filename -> file_id map from remote (for Pass 2)
        remote_filename_map = {}
        for f in remote_files:
            file_id = f.get("id")
            filename_decoded = f.get("decoded_filename", "")
            if filename_decoded and file_id:
                # Strip site folder prefix to get relative path
                relative_filename = filename_decoded.removeprefix(f"{site_name}/")
                remote_filename_map[relative_filename] = {
                    "file_id": file_id,
                    "hash": f.get("hash"),
                    "filename": filename_decoded,
                }

        logger.info(f"Built filename map for {len(remote_filename_map)} remote files")

        # Pass 1: Match local files by hash (perfect matches)
        local_files = local_metadata.get("files", [])
        file_id_map = {}
        matched_count = 0
        unmatched_local = []

        for local_file in local_files:
            url = local_file.get("url")
            local_hash = local_file.get("checksum")

            if not url or not local_hash:
                continue

            # Try to match by hash
            if local_hash in remote_hash_map:
                file_id = remote_hash_map[local_hash]["file_id"]
                file_id_map[url] = file_id
                matched_count += 1
                logger.debug(f"✓ Hash matched: {local_file.get('filename')} -> {file_id}")
            else:
                unmatched_local.append(local_file)

        # Pass 2: Match remaining files by filename (content drift)
        filename_matched_count = 0
        still_unmatched = []

        for local_file in unmatched_local:
            url = local_file.get("url")
            local_filename = local_file.get("filename")

            if not url or not local_filename:
                still_unmatched.append(
                    {
                        "url": url,
                        "filename": local_filename,
                        "hash": local_file.get("checksum"),
                        "reason": "missing_url_or_filename",
                    }
                )
                continue

            # Try to match by filename
            if local_filename in remote_filename_map:
                remote_info = remote_filename_map[local_filename]
                file_id = remote_info["file_id"]
                file_id_map[url] = file_id
                filename_matched_count += 1
                matched_count += 1
                logger.debug(
                    f"✓ Filename matched (hash differs): {local_filename} -> {file_id}\n"
                    f"  Local hash:  {local_file.get('checksum', 'unknown')[:16]}...\n"
                    f"  Remote hash: {remote_info.get('hash', 'unknown')[:16]}...\n"
                    f"  Will be updated on next incremental upload"
                )
            else:
                still_unmatched.append(
                    {
                        "url": url,
                        "filename": local_filename,
                        "hash": local_file.get("checksum"),
                        "reason": "no_match",
                    }
                )

        # Update unmatched_local to only truly unmatched files
        unmatched_local = still_unmatched

        # Check for unmatched remote files
        matched_file_ids = set(file_id_map.values())
        unmatched_remote = []

        for remote_hash, info in remote_hash_map.items():
            if info["file_id"] not in matched_file_ids:
                unmatched_remote.append(
                    {"file_id": info["file_id"], "filename": info["filename"], "hash": remote_hash}
                )

        # Calculate confidence based on total matches
        total_local = len(local_files)
        match_rate = matched_count / total_local if total_local > 0 else 0
        hash_only_count = matched_count - filename_matched_count

        if match_rate >= 0.95:
            confidence = "high"
        elif match_rate >= 0.75:
            confidence = "medium"
        elif match_rate >= 0.5:
            confidence = "low"
        else:
            confidence = "very_low"

        logger.info("Matching complete:")
        logger.info(f"  Total matched: {matched_count}/{total_local} files ({match_rate*100:.1f}%)")
        logger.info(f"  - Hash matched: {hash_only_count} (perfect sync)")
        logger.info(f"  - Filename matched: {filename_matched_count} (will update)")
        logger.info(f"  Unmatched local: {len(unmatched_local)}")
        logger.info(f"  Unmatched remote: {len(unmatched_remote)}")
        logger.info(f"  Confidence: {confidence}")

        return {
            "success": True,
            "file_id_map": file_id_map,
            "matched_count": matched_count,
            "total_local": total_local,
            "match_rate": match_rate,
            "unmatched_local": unmatched_local,
            "unmatched_remote": unmatched_remote,
            "confidence": confidence,
        }

    async def _rebuild_state_inline(
        self,
        knowledge_id: str,
        site_name: str,
        local_metadata: dict,
        min_confidence: str = "medium",
    ) -> dict | None:
        """
        Rebuild upload state inline during upload operation.
        Called automatically when upload_status.json is missing.

        Args:
            knowledge_id: Knowledge base ID
            site_name: Site name for folder filtering
            local_metadata: Local metadata dict with file info and hashes
            min_confidence: Minimum confidence level required ('high', 'medium', 'low')

        Returns:
            Reconstructed upload_status dict if successful, None if confidence too low
        """
        logger.info(f"Attempting to rebuild state from remote for {site_name}...")

        # Match files by hash
        match_result = await self.match_and_reconcile(knowledge_id, site_name, local_metadata)

        if not match_result["success"]:
            logger.error("Failed to match files with remote state")
            return None

        # Check confidence level
        confidence = match_result["confidence"]
        confidence_levels = ["very_low", "low", "medium", "high"]

        min_level_idx = (
            confidence_levels.index(min_confidence) if min_confidence in confidence_levels else 1
        )
        actual_level_idx = (
            confidence_levels.index(confidence) if confidence in confidence_levels else 0
        )

        if actual_level_idx < min_level_idx:
            logger.warning(
                f"Match confidence '{confidence}' is below threshold '{min_confidence}'\n"
                f"  Matched: {match_result['matched_count']}/{match_result['total_local']} files\n"
                f"  To proceed anyway, use: --rebuild or rebuild-state command"
            )
            return None

        logger.info(
            f"✓ State reconstruction successful!\n"
            f"  Confidence: {confidence}\n"
            f"  Matched: {match_result['matched_count']}/{match_result['total_local']} files"
        )

        # Build upload_status dict
        import datetime

        upload_status = {
            "last_upload": datetime.datetime.now().isoformat(),
            "knowledge_id": knowledge_id,
            "knowledge_name": local_metadata.get("site", {}).get("display_name", site_name),
            "site_name": site_name,
            "site_folder": f"{site_name}/",
            "files_uploaded": match_result["matched_count"],
            "files_updated": 0,
            "files_deleted": 0,
            "source_timestamp": local_metadata.get("current_state", {}).get(
                "source_timestamp", "unknown"
            ),
            "rebuilt_from_remote": True,
            "rebuild_confidence": confidence,
            "rebuild_match_rate": match_result["match_rate"],
            "file_id_map": match_result["file_id_map"],
            "files": [],
        }

        # Build remote hash lookup for filename-matched files
        remote_files_list = await self.get_knowledge_files(
            knowledge_id, include_hashes=True, site_folder=site_name
        )

        remote_hash_by_filename = {}
        if remote_files_list:
            for rf in remote_files_list:
                decoded_filename = rf.get("decoded_filename", "")
                relative_filename = decoded_filename.removeprefix(f"{site_name}/")
                if relative_filename and rf.get("hash"):
                    remote_hash_by_filename[relative_filename] = rf["hash"]

        # Convert file_id_map to files list format
        file_id_map = match_result["file_id_map"]
        for local_file in local_metadata.get("files", []):
            url = local_file.get("url")
            if url and url in file_id_map:
                # Preserve all original fields from local_file
                file_entry = local_file.copy()
                # Add the matched file_id
                file_entry["file_id"] = file_id_map[url]
                # Add reference to decoded filename we've matched it to
                file_entry["matched_filename"] = local_file.get("filename")

                # CRITICAL: For filename matches, use remote hash so update is detected
                local_filename = local_file.get("filename")
                local_hash = local_file.get("checksum")

                if local_filename in remote_hash_by_filename:
                    remote_hash = remote_hash_by_filename[local_filename]
                    if local_hash != remote_hash:
                        # Filename match with hash diff - use remote hash
                        file_entry["checksum"] = remote_hash
                        logger.debug(f"Using remote hash for {local_filename} to trigger update")

                upload_status["files"].append(file_entry)

        logger.info(f"Reconstructed upload_status:\n{json.dumps(upload_status, indent=2)}")

        return upload_status

    async def reindex_knowledge(self, knowledge_id: str) -> bool:
        """
        Reindex knowledge base files.
        Uses POST /api/v1/knowledge/reindex endpoint.
        """
        try:
            url = f"{self.base_url}/api/v1/knowledge/reindex"

            payload = {"knowledge_id": knowledge_id}

            async with (
                aiohttp.ClientSession() as session,
                session.post(url, headers=self.headers, json=payload) as response,
            ):
                if response.status == 200:
                    logger.info(f"✓ Triggered reindex for knowledge {knowledge_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.warning(f"Failed to reindex: {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"Error reindexing knowledge: {e}")
            return False

    async def upload_scrape_incrementally(
        self,
        scrape_dir: Path,
        site_name: str,
        knowledge_name: str,
        files_to_upload: list[dict],
        files_to_delete: list[str],
        previous_file_map: dict[str, str] | None = None,
        description: str = "",
        batch_size: int = 10,
        knowledge_id: str | None = None,
        keep_files: bool = False,
        verify_before_update: bool = True,  # Enable reconciliation by default
        cleanup_untracked: bool = False,  # NEW: Opt-in for safety (default OFF)
    ) -> dict:
        """
        Perform incremental upload with add/update/delete operations.
        Files are uploaded with site folder prefix for multi-site organization.

        Args:
            scrape_dir: Directory containing scraped markdown files
            site_name: Site identifier for folder prefix (e.g., 'monsterhunter')
            knowledge_name: Name of the knowledge base
            files_to_upload: List of file info dicts to upload (new or modified)
            files_to_delete: List of URLs to delete
            previous_file_map: Dict mapping URLs to file_ids from previous upload
            description: Description of the knowledge base
            batch_size: Number of files to upload per batch
            knowledge_id: If provided, use existing knowledge
            keep_files: If True, only remove from knowledge, don't delete files
            verify_before_update: If True, verify files exist before updating (reconciliation)
            cleanup_untracked: If True, delete untracked files in site folder (default)

        Returns:
            Summary of upload operation with file_id mappings and reconciliation stats
        """
        logger.info(f"Incremental upload to knowledge: {knowledge_name}")
        logger.info(f"  Site folder: {site_name}/")
        logger.info(f"  Upload: {len(files_to_upload)} files")
        logger.info(f"  Delete: {len(files_to_delete)} files")
        if keep_files:
            logger.info("  Keep files mode: Files will not be deleted from storage")
        if verify_before_update:
            logger.info("  Reconciliation enabled: Will verify files before update")
        if cleanup_untracked:
            logger.info(f"  Cleanup enabled: Will remove untracked files from {site_name}/ folder")

        # Get or create knowledge
        if knowledge_id:
            logger.info(f"Using existing knowledge: {knowledge_id}")
            knowledge: dict | None = {"id": knowledge_id, "name": knowledge_name}
        else:
            knowledge = await self.create_knowledge(knowledge_name, description)
            if not knowledge:
                return {"error": f"Failed to create knowledge: {knowledge_name}"}
            logger.info(f"Created/found knowledge: {knowledge.get('id')}")

        assert knowledge is not None
        knowledge_id = cast(str, knowledge["id"])
        knowledge_name = knowledge.get("name", knowledge_name)

        previous_file_map = previous_file_map or {}
        new_file_map = {}

        # Phase 1: Delete removed files
        deleted_count = 0
        removed_count = 0
        if files_to_delete and previous_file_map:
            action = "Removing" if keep_files else "Deleting"
            logger.info(f"{action} {len(files_to_delete)} files...")
            for url in files_to_delete:
                file_id = previous_file_map.get(url)
                if file_id and await self.remove_file_from_knowledge(knowledge_id, file_id):
                    removed_count += 1
                    # Only delete file if keep_files is False
                    if not keep_files and await self.delete_file(file_id):
                        deleted_count += 1
                await asyncio.sleep(0.1)

        # Phase 2: Process files to upload (new and modified)
        new_files = []
        modified_files = []

        for file_info in files_to_upload:
            url = file_info["url"]
            file_path = scrape_dir / file_info["filename"]

            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue

            if url in previous_file_map:
                # Modified file - update content
                modified_files.append((previous_file_map[url], file_path, file_info))
            else:
                # New file - upload
                new_files.append((file_path, file_info))

        # NEW: Pre-verify modified files exist before updating (reconciliation)
        externally_deleted = []
        if verify_before_update and modified_files:
            logger.info(f"Verifying {len(modified_files)} files exist before update...")
            verified_modified = []

            for file_id, file_path, file_info in modified_files:
                if await self.verify_file_exists(file_id):
                    verified_modified.append((file_id, file_path, file_info))
                else:
                    logger.warning(
                        f"⚠ File {file_id} was deleted externally, will re-upload as new"
                    )
                    externally_deleted.append((file_path, file_info))

            # Re-upload externally deleted files as NEW (can't reuse old file_id)
            if externally_deleted:
                logger.info(f"Re-uploading {len(externally_deleted)} externally deleted files...")
                new_files.extend(externally_deleted)

            modified_files = verified_modified

        # Upload new files with site folder prefix
        uploaded_count = 0
        new_file_ids: list[str] = []

        if new_files:
            logger.info(f"Uploading {len(new_files)} new files to {site_name}/...")
            file_paths = [fp for fp, _ in new_files]

            # Pass site_name and scrape_dir for folder organization
            upload_results = await self.upload_files(
                file_paths, site_name=site_name, base_content_dir=scrape_dir, batch_size=batch_size
            )

            # Map results to new_file_map and collect file_ids
            new_file_ids = []
            for result in upload_results:
                file_id = result.get("file_id")
                if file_id:
                    new_file_ids.append(cast(str, file_id))

                    # Find which new_file this result corresponds to
                    for file_path, file_info in new_files:
                        if file_path.name == result.get("filename"):
                            new_file_map[file_info["url"]] = cast(str, file_id)
                            break

            uploaded_count = len(new_file_ids)

            # Wait for files to be processed
            if new_file_ids:
                await self._wait_for_file_processing(new_file_ids)

        # Update modified files
        updated_count = 0
        if modified_files:
            logger.info(f"Updating {len(modified_files)} modified files...")
            for file_id, file_path, file_info in modified_files:
                if await self.update_file_content(file_id, file_path):
                    updated_count += 1
                    new_file_map[file_info["url"]] = file_id
                else:
                    # Update failed (likely 404) - file was deleted after verification
                    logger.warning(
                        f"Failed to update {file_info['url']}, file may have been deleted during upload"
                    )
                await asyncio.sleep(0.1)

        # Phase 3: Add new files to knowledge (batch)
        if new_file_ids:
            logger.info(f"Adding {len(new_file_ids)} new files to knowledge...")
            await self.add_files_to_knowledge_batch(knowledge_id, new_file_ids)

        # Preserve file IDs for unchanged files
        for url, file_id in previous_file_map.items():
            if url not in new_file_map and url not in files_to_delete:
                new_file_map[url] = file_id

        # NEW: Phase 4: Cleanup untracked files in site folder
        deleted_untracked = 0
        if cleanup_untracked and not keep_files:
            logger.info(f"Checking for untracked files in {site_name}/ folder...")
            remote_files = await self.get_knowledge_files(knowledge_id)

            if remote_files:
                # Filter to only files in this site's folder
                import urllib.parse

                site_folder = f"{site_name}/"
                untracked_file_ids = []

                for f in remote_files:
                    file_id = f["id"]
                    # Get filename and decode it
                    filename_encoded = f.get("meta", {}).get("name", "")
                    filename = urllib.parse.unquote(filename_encoded) if filename_encoded else ""

                    # Check if in our folder and not in our tracking
                    if filename.startswith(site_folder) and file_id not in new_file_map.values():
                        untracked_file_ids.append((file_id, filename))

                if untracked_file_ids:
                    logger.info(
                        f"Found {len(untracked_file_ids)} untracked files in {site_name}/ folder, deleting..."
                    )
                    for file_id, filename in untracked_file_ids:
                        # Remove from knowledge and delete file
                        if (
                            file_id
                            and await self.remove_file_from_knowledge(knowledge_id, file_id)
                            and await self.delete_file(file_id)
                        ):
                            deleted_untracked += 1
                            logger.debug(f"✓ Deleted untracked: {filename}")
                        await asyncio.sleep(0.1)

                    logger.info(f"✓ Cleaned up {deleted_untracked} untracked files")

        # Optional: Reindex if there were significant changes
        total_changes = uploaded_count + updated_count + deleted_count + deleted_untracked
        if total_changes > 10:
            logger.info("Triggering reindex due to significant changes...")
            await self.reindex_knowledge(knowledge_id)

        return {
            "success": True,
            "knowledge_id": knowledge_id,
            "knowledge_name": knowledge_name,
            "site_name": site_name,
            "site_folder": f"{site_name}/",
            "files_uploaded": uploaded_count,
            "files_updated": updated_count,
            "files_deleted": deleted_count,
            "files_reuploaded": len(externally_deleted) if verify_before_update else 0,
            "files_deleted_untracked": deleted_untracked,  # NEW
            "file_id_map": new_file_map,  # NEW
            "summary": f"Uploaded: {uploaded_count}, Updated: {updated_count}, Deleted: {deleted_count}",
        }

    async def _wait_for_file_processing(self, file_ids: list[str], timeout: int = 60):
        """
        Wait for files to finish processing before adding to knowledge.

        Args:
            file_ids: List of file IDs to check
            timeout: Maximum seconds to wait
        """
        logger.info(f"Waiting for {len(file_ids)} files to be processed...")

        start_time = asyncio.get_event_loop().time()
        pending_files = set(file_ids)

        while pending_files and (asyncio.get_event_loop().time() - start_time) < timeout:
            completed = set()

            for file_id in list(pending_files):
                status = await self.get_file_process_status(file_id)

                if status:
                    # Check if processing is complete
                    # Status could be: "completed", "processing", "failed", etc.
                    state = status.get("status", status.get("state", "unknown"))

                    if state in ["completed", "success", "done"]:
                        logger.debug(f"✓ File {file_id} processed successfully")
                        completed.add(file_id)
                    elif state in ["failed", "error"]:
                        logger.warning(f"✗ File {file_id} processing failed")
                        completed.add(file_id)  # Remove from pending even if failed
                else:
                    # If we can't get status, assume it's ready after a short wait
                    await asyncio.sleep(1)
                    completed.add(file_id)

            pending_files -= completed

            if pending_files:
                logger.debug(f"Waiting for {len(pending_files)} files to complete processing...")
                await asyncio.sleep(2)

        if pending_files:
            logger.warning(f"Timeout waiting for {len(pending_files)} files to process")
        else:
            logger.info("✓ All files processed successfully")

    async def test_connection(self) -> bool:
        """
        Test connection to Open Web UI API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            url = f"{self.base_url}/api/v1/knowledge/"

            async with (
                aiohttp.ClientSession() as session,
                session.get(url, headers=self.headers) as response,
            ):
                if response.status == 200:
                    logger.debug("✓ Successfully connected to Open Web UI API")
                    return True
                else:
                    logger.error(f"Failed to connect: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    async def upload_scrape_to_knowledge(
        self,
        scrape_dir: Path,
        site_name: str,
        knowledge_name: str,
        description: str = "",
        batch_size: int = 10,
        knowledge_id: str | None = None,
        specific_files: list[Path] | None = None,
        shuffle: bool = False,
        **mode_info,
    ) -> dict:
        """
        Upload all files from a scrape to a knowledge collection.
        Files are uploaded with site folder prefix for multi-site organization.

        Args:
            scrape_dir: Directory containing scraped Markdown files
            site_name: Site identifier for folder prefix
            knowledge_name: Name of the knowledge base
            description: Description of the knowledge base
            batch_size: Number of files to upload per batch
            knowledge_id: If provided, use existing knowledge
            specific_files: If provided, only upload these files
            shuffle: Whether to shuffle files before upload
            **mode_info: Additional mode configuration (for special upload modes)

        Returns:
            Summary of upload operation with file_id mappings
        """
        logger.info(f"Full upload to knowledge: {knowledge_name}")
        logger.info(f"  Site folder: {site_name}/")

        # Get files to upload
        file_paths = specific_files or list(scrape_dir.rglob("*.md"))

        if not file_paths:
            return {"error": "No markdown files found to upload"}

        # Get or create knowledge
        if knowledge_id:
            logger.info(f"Using existing knowledge: {knowledge_id}")
            knowledge: dict | None = {"id": knowledge_id}
        else:
            knowledge = await self.create_knowledge(knowledge_name, description)
            if not knowledge:
                return {"error": f"Failed to create knowledge: {knowledge_name}"}
            logger.info(f"Created new knowledge: {knowledge.get('id')}")

        assert knowledge is not None
        knowledge_id = cast(str, knowledge["id"])
        knowledge_name = knowledge["name"]

        # Upload files with site folder prefix
        upload_results = await self.upload_files(
            file_paths, site_name=site_name, base_content_dir=scrape_dir, batch_size=batch_size
        )

        if not upload_results:
            return {"error": "Failed to upload files"}

        file_ids = [
            cast(str, r["file_id"]) for r in upload_results if "file_id" in r and r["file_id"]
        ]

        # Wait for files to be processed
        if file_ids:
            await self._wait_for_file_processing(file_ids)

        # Add files to knowledge (batch)
        add_result = await self.add_files_to_knowledge_batch(knowledge_id, file_ids)

        # Build file_id_map for tracking
        file_id_map = {}
        for result in upload_results:
            # Try to extract URL from upload_filename
            upload_filename = result.get("upload_filename", "")
            # Remove site prefix to get relative path
            relative_path = upload_filename.removeprefix(f"{site_name}/")
            # Construct URL (this is approximate - real URL might differ)
            url = f"{relative_path}"  # Placeholder URL
            file_id_map[url] = result.get("file_id")

        return {
            "success": True,
            "knowledge_id": knowledge_id,
            "knowledge_name": knowledge_name,
            "site_name": site_name,
            "site_folder": f"{site_name}/",
            "files_uploaded": len(file_ids),
            "files_added_to_knowledge": add_result.get("files_added", 0),
            "file_id_map": file_id_map,
            "summary": f"Uploaded {len(file_ids)} files to {knowledge_name}",
        }
