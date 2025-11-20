"""
Base abstract class for content cleaning profiles.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseCleaningProfile(ABC):
    """Base class for content cleaning profiles."""

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize with optional configuration.

        Args:
            config: Profile-specific configuration dictionary
        """
        self.config = config or {}
        self.validate_config(self.config)

    @abstractmethod
    def clean(self, content: str, metadata: dict | None = None) -> str:
        """
        Clean content according to profile rules.

        Args:
            content: Raw scraped content
            metadata: Optional metadata (url, site_config, etc.)

        Returns:
            Cleaned content ready for embedding
        """
        pass

    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """
        Return JSON schema for profile configuration.

        Returns:
            Dictionary containing the schema definition
        """
        pass

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> bool:
        """
        Validate configuration against schema.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, raises ValueError if invalid
        """
        # Basic validation - can be enhanced with jsonschema library
        schema = cls.get_config_schema()
        if not schema:
            return True

        # Check required properties
        properties = schema.get("properties", {})
        for key, prop_schema in properties.items():
            if key in config:
                # Type checking
                expected_type = prop_schema.get("type")
                actual_value = config[key]

                if expected_type == "boolean" and not isinstance(actual_value, bool):
                    raise ValueError(
                        f"Config '{key}' must be boolean, got {type(actual_value).__name__}"
                    )
                elif expected_type == "string" and not isinstance(actual_value, str):
                    raise ValueError(
                        f"Config '{key}' must be string, got {type(actual_value).__name__}"
                    )
                elif expected_type == "number" and not isinstance(actual_value, (int, float)):
                    raise ValueError(
                        f"Config '{key}' must be number, got {type(actual_value).__name__}"
                    )

        return True

    @classmethod
    def get_profile_name(cls) -> str:
        """
        Return profile identifier (e.g., 'mediawiki' from MediaWikiProfile).

        Returns:
            Profile name as lowercase string
        """
        name = cls.__name__.replace("Profile", "").lower()
        return name

    @classmethod
    def get_description(cls) -> str:
        """
        Return human-readable description.

        Returns:
            Profile description from docstring or default message
        """
        return cls.__doc__ or "No description available"
