import logging
import tempfile
from pathlib import Path

import pytest

from webowui.config import ensure_example_configs

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.unit
def test_ensure_example_configs_real_files():
    """
    Test ensure_example_configs using the actual files in the package.
    This verifies that the package structure is correct and files can be found.
    """
    # Create a temporary directory to act as the 'data/config/sites' directory
    with tempfile.TemporaryDirectory() as temp_dir:
        sites_dir = Path(temp_dir)

        # Verify it's empty initially
        initial_files = list(sites_dir.glob("*"))
        assert len(initial_files) == 0

        # Run the function
        ensure_example_configs(sites_dir)

        # Check results
        final_files = list(sites_dir.glob("*"))
        final_filenames = [f.name for f in final_files]

        # We expect at least the .yml.example files and README.md
        expected_files = [
            "example_site.yml.example",
            "mediawiki.yml.example",
            "simple_test.yml.example",
            "README.md",
        ]

        for expected in expected_files:
            assert expected in final_filenames, f"Missing expected file: {expected}"

        # Verify content is not empty
        for filename in final_filenames:
            assert (sites_dir / filename).stat().st_size > 0


@pytest.mark.unit
def test_ensure_example_configs_preserves_existing():
    """Test that existing files are not overwritten."""
    with tempfile.TemporaryDirectory() as temp_dir:
        sites_dir = Path(temp_dir)

        # Create a dummy file that conflicts with an example
        dummy_file = sites_dir / "example_site.yml.example"
        dummy_content = "DUMMY CONTENT"
        dummy_file.write_text(dummy_content)

        # Run the function
        ensure_example_configs(sites_dir)

        # Verify content was NOT changed
        assert dummy_file.read_text() == dummy_content

        # Verify other files were copied
        assert (sites_dir / "mediawiki.yml.example").exists()
