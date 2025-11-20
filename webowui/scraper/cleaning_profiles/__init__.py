"""
Content cleaning profiles package with auto-discovery.
"""

import importlib.util
import inspect
import logging
import shutil
from pathlib import Path

from .base import BaseCleaningProfile
from .registry import CleaningProfileRegistry

logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """
    Get config directory - uses /app/data/config structure.

    Returns:
        Path to config directory
    """
    # Navigate from webowui/scraper/cleaning_profiles/ -> webowui/ -> project root -> data/config/
    app_root = Path(__file__).parent.parent.parent.parent
    return app_root / "data" / "config"


def discover_profiles():
    """Auto-discover all profiles from config/profiles/ directory."""
    config_dir = get_config_dir()
    profiles_dir = config_dir / "profiles"

    # Create directory if missing (first run)
    profiles_dir.mkdir(parents=True, exist_ok=True)

    # Copy built-in profiles on first run
    _ensure_builtin_profiles(profiles_dir)

    # Dynamically load all *_profile.py files
    profile_files = list(profiles_dir.glob("*_profile.py"))
    logger.info(f"Discovering cleaning profiles in {profiles_dir}")

    for profile_file in profile_files:
        try:
            module_name = profile_file.stem

            # Import using importlib with simpler module name
            spec = importlib.util.spec_from_file_location(
                f"_cleaning_profile_{module_name}", profile_file  # Use simple namespace
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Register BaseCleaningProfile subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseCleaningProfile) and obj is not BaseCleaningProfile:
                        CleaningProfileRegistry.register(obj)
                        logger.debug(f"Loaded profile from {profile_file.name}: {name}")
        except Exception as e:
            logger.error(f"Failed to load profile from {profile_file}: {e}")


def _ensure_builtin_profiles(profiles_dir: Path):
    """
    Copy built-in profiles to config/ on first run.

    Args:
        profiles_dir: Target directory for profiles
    """
    builtin_dir = Path(__file__).parent / "builtin_profiles"

    if not builtin_dir.exists():
        logger.warning(f"Built-in profiles directory not found: {builtin_dir}")
        return

    # Copy each built-in profile if it doesn't exist
    for builtin_file in builtin_dir.glob("*_profile.py"):
        target = profiles_dir / builtin_file.name
        if not target.exists():
            try:
                shutil.copy(builtin_file, target)
                logger.info(f"Copied built-in profile: {builtin_file.name}")
            except Exception as e:
                logger.error(f"Failed to copy {builtin_file.name}: {e}")

    # Copy README if it exists and target doesn't
    readme = builtin_dir / "README.md"
    target_readme = profiles_dir / "README.md"
    if readme.exists() and not target_readme.exists():
        try:
            shutil.copy(readme, target_readme)
            logger.info("Copied profiles README.md")
        except Exception as e:
            logger.error(f"Failed to copy README.md: {e}")


# Auto-discover on package import
try:
    discover_profiles()
except Exception as e:
    logger.error(f"Failed to auto-discover profiles: {e}")


# Export main classes
__all__ = ["BaseCleaningProfile", "CleaningProfileRegistry", "discover_profiles"]
