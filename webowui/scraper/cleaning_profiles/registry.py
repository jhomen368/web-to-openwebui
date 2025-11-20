"""
Registry for discovering and managing cleaning profiles.
"""

import logging

from .base import BaseCleaningProfile

logger = logging.getLogger(__name__)


class CleaningProfileRegistry:
    """Registry for discovering and managing cleaning profiles."""

    _profiles: dict[str, type[BaseCleaningProfile]] = {}

    @classmethod
    def register(cls, profile_class: type[BaseCleaningProfile]):
        """
        Register a cleaning profile.

        Args:
            profile_class: The profile class to register
        """
        name = profile_class.get_profile_name()
        cls._profiles[name] = profile_class
        logger.debug(f"Registered cleaning profile: {name}")

    @classmethod
    def get_profile(cls, name: str, config: dict | None = None) -> BaseCleaningProfile:
        """
        Get instance of registered profile.

        Args:
            name: Profile name
            config: Optional configuration for the profile

        Returns:
            Instance of the requested profile

        Raises:
            ValueError: If profile not found
        """
        if name not in cls._profiles:
            available = list(cls._profiles.keys())
            raise ValueError(f"Unknown profile: '{name}'. Available profiles: {available}")

        profile_class = cls._profiles[name]
        return profile_class(config)

    @classmethod
    def list_profiles(cls) -> list[dict[str, str]]:
        """
        List all available profiles.

        Returns:
            List of dictionaries with profile information
        """
        return [
            {"name": name, "description": profile_class.get_description()}
            for name, profile_class in cls._profiles.items()
        ]

    @classmethod
    def has_profile(cls, name: str) -> bool:
        """
        Check if a profile is registered.

        Args:
            name: Profile name to check

        Returns:
            True if profile exists
        """
        return name in cls._profiles

    @classmethod
    def clear(cls):
        """Clear all registered profiles (mainly for testing)."""
        cls._profiles.clear()
