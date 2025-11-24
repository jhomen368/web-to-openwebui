"""
Unit tests for logging configuration.
"""

import logging
import logging.handlers
from unittest.mock import MagicMock, patch

from webowui.logging_config import setup_logging


def test_setup_logging(tmp_path):
    """Test that logging is configured correctly."""
    logs_dir = tmp_path / "logs"

    # Mock logging.getLogger to avoid modifying global state
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        setup_logging(logs_dir, "DEBUG")

        # Verify directory creation
        assert logs_dir.exists()

        # Verify logger configuration
        mock_logger.setLevel.assert_called_with(logging.DEBUG)
        mock_logger.handlers.clear.assert_called_once()

        # Verify handlers added
        assert mock_logger.addHandler.call_count == 2

        # Verify handlers types
        handlers = [call.args[0] for call in mock_logger.addHandler.call_args_list]

        # Check for RichHandler (console)
        has_rich = any("RichHandler" in str(type(h)) for h in handlers)
        assert has_rich

        # Check for TimedRotatingFileHandler (file)
        has_file = any(isinstance(h, logging.handlers.TimedRotatingFileHandler) for h in handlers)
        assert has_file

        # Verify file handler configuration
        file_handler = next(
            h for h in handlers if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        )
        assert file_handler.baseFilename == str(logs_dir / "app.log")
        assert file_handler.when == "MIDNIGHT"
        assert file_handler.interval == 1 or file_handler.interval == 86400
        assert file_handler.backupCount == 14
        assert file_handler.encoding == "utf-8"
