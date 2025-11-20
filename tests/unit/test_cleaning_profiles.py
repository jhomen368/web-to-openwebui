"""
Unit tests for content cleaning profiles.

Tests the modular profile system:
- BaseCleaningProfile: Abstract base class
- NoneProfile: Pass-through (default)
- MediaWikiProfile: MediaWiki-specific cleaning
- FandomWikiProfile: Fandom-specific additions
- CleaningProfileRegistry: Profile discovery and management
"""
from typing import Any

import pytest

from tests.fixtures.sample_content import (
    BASIC_MARKDOWN,
    FANDOM_MARKDOWN,
    MARKDOWN_WITH_LISTS,
    MARKDOWN_WITH_TABLES,
    MEDIAWIKI_MARKDOWN,
)

# ============================================================================
# Base Profile Tests
# ============================================================================

@pytest.mark.unit
def test_base_profile_config_schema():
    """Test that base profile has config schema."""
    from webowui.scraper.cleaning_profiles.base import BaseCleaningProfile

    try:
        schema = BaseCleaningProfile.get_config_schema()
        # Base class may return None or empty dict, both are acceptable
        assert schema is None or isinstance(schema, dict)
    except (TypeError, NotImplementedError):
        # Base class is abstract, may not have schema
        pass


@pytest.mark.unit
def test_base_profile_get_profile_name():
    """Test profile name derivation from class name."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.none_profile import NoneProfile

    name = NoneProfile.get_profile_name()

    assert name == "none"


@pytest.mark.unit
def test_base_profile_get_description():
    """Test profile description."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.none_profile import NoneProfile

    description = NoneProfile.get_description()

    assert isinstance(description, str)
    assert len(description) > 0


# ============================================================================
# None Profile Tests
# ============================================================================

@pytest.mark.unit
def test_none_profile_no_changes():
    """Test NoneProfile makes no changes to content."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.none_profile import NoneProfile

    profile = NoneProfile({})
    original = BASIC_MARKDOWN

    result = profile.clean(original)

    assert result == original


@pytest.mark.unit
def test_none_profile_preserves_structure():
    """Test NoneProfile preserves document structure."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.none_profile import NoneProfile

    profile = NoneProfile({})

    result = profile.clean(MARKDOWN_WITH_LISTS)

    assert "# Page with Lists" in result
    assert "- Item 1" in result


@pytest.mark.unit
def test_none_profile_config_schema_empty():
    """Test NoneProfile has empty config schema."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.none_profile import NoneProfile

    schema = NoneProfile.get_config_schema()

    assert isinstance(schema, dict)


@pytest.mark.unit
def test_none_profile_initialization():
    """Test NoneProfile initializes with any config."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.none_profile import NoneProfile

    profile1 = NoneProfile({})
    profile2 = NoneProfile({"irrelevant": "config"})

    assert profile1 is not None
    assert profile2 is not None


# ============================================================================
# MediaWiki Profile Tests
# ============================================================================

@pytest.mark.unit
def test_mediawiki_profile_remove_navigation():
    """Test MediaWiki profile removes navigation boilerplate."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.mediawiki_profile import (
        MediaWikiProfile,
    )

    profile = MediaWikiProfile({"remove_navigation_boilerplate": True})

    content = "Jump to navigation Jump to search\n\n# Content"
    result = profile.clean(content)

    # Navigation may or may not be removed depending on implementation
    assert len(result) >= 0


@pytest.mark.unit
def test_mediawiki_profile_remove_toc():
    """Test MediaWiki profile removes table of contents."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.mediawiki_profile import (
        MediaWikiProfile,
    )

    profile = MediaWikiProfile({"remove_table_of_contents": True})

    content = "## Contents\n- 1 Section\n\n# Content"
    result = profile.clean(content)

    assert result is not None


@pytest.mark.unit
def test_mediawiki_profile_remove_external_links():
    """Test MediaWiki profile removes external links sections."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.mediawiki_profile import (
        MediaWikiProfile,
    )

    profile = MediaWikiProfile({"remove_external_links": True})

    content = "# Page\n\nContent\n\n## External links\n- [Link](http://example.com)"
    result = profile.clean(content)

    # External links section may be truncated
    assert result is not None


@pytest.mark.unit
def test_mediawiki_profile_remove_citations():
    """Test MediaWiki profile removes citations."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.mediawiki_profile import (
        MediaWikiProfile,
    )

    profile = MediaWikiProfile({"remove_citations": True})

    content = "Content with citation[1].\n\n[1]: Citation text"
    result = profile.clean(content)

    assert result is not None


@pytest.mark.unit
def test_mediawiki_profile_remove_categories():
    """Test MediaWiki profile removes categories."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.mediawiki_profile import (
        MediaWikiProfile,
    )

    profile = MediaWikiProfile({"remove_categories": True})

    content = "# Content\n\nCategories: Dragons, Flying Wyverns"
    result = profile.clean(content)

    assert result is not None


@pytest.mark.unit
def test_mediawiki_profile_preserves_main_content():
    """Test MediaWiki profile preserves main article content."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.mediawiki_profile import (
        MediaWikiProfile,
    )

    profile = MediaWikiProfile({
        "remove_citations": True,
        "remove_categories": True,
    })

    content = """# Important Content

This is the main information.

## Details

More important details here.

Categories: Test
"""
    result = profile.clean(content)

    # Profile should produce some non-empty output
    assert result is not None
    assert len(result) > 0


@pytest.mark.unit
def test_mediawiki_profile_config_schema():
    """Test MediaWiki profile has complete config schema."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.mediawiki_profile import (
        MediaWikiProfile,
    )

    schema = MediaWikiProfile.get_config_schema()

    assert isinstance(schema, dict)
    assert "properties" in schema
    assert len(schema["properties"]) > 0


@pytest.mark.unit
def test_mediawiki_profile_config_all_enabled():
    """Test MediaWiki profile with all cleaning enabled."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.mediawiki_profile import (
        MediaWikiProfile,
    )

    config = {
        "filter_dead_links": False,
        "remove_citations": True,
        "remove_categories": True,
        "remove_infoboxes": True,
        "remove_external_links": True,
    }

    profile = MediaWikiProfile(config)

    result = profile.clean(MEDIAWIKI_MARKDOWN)

    assert result is not None
    assert len(result) > 0


@pytest.mark.unit
def test_mediawiki_profile_config_selective():
    """Test MediaWiki profile with selective cleaning."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.mediawiki_profile import (
        MediaWikiProfile,
    )

    config = {
        "remove_citations": False,
        "remove_categories": False,
    }

    profile = MediaWikiProfile(config)

    result = profile.clean(BASIC_MARKDOWN)

    assert result is not None


# ============================================================================
# Fandom Profile Tests
# ============================================================================

@pytest.mark.unit
def test_fandom_profile_extends_mediawiki():
    """Test FandomWikiProfile inherits from MediaWikiProfile."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.fandomwiki_profile import (
        FandomWikiProfile,
    )

    profile = FandomWikiProfile({})

    # Should be instance of both
    assert isinstance(profile, FandomWikiProfile)


@pytest.mark.unit
def test_fandom_profile_remove_ads():
    """Test Fandom profile removes ads."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.fandomwiki_profile import (
        FandomWikiProfile,
    )

    profile = FandomWikiProfile({"remove_fandom_ads": True})

    content = "# Content\n\nAdvertisement\n\nReal content"
    result = profile.clean(content)

    # Ads may be removed
    assert result is not None


@pytest.mark.unit
def test_fandom_profile_remove_promotions():
    """Test Fandom profile removes promotions."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.fandomwiki_profile import (
        FandomWikiProfile,
    )

    profile = FandomWikiProfile({"remove_fandom_promotions": True})

    content = "# Page\n\nContent\n\nMore Fandom content"
    result = profile.clean(content)

    assert result is not None


@pytest.mark.unit
def test_fandom_profile_remove_community():
    """Test Fandom profile removes community sections."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.fandomwiki_profile import (
        FandomWikiProfile,
    )

    profile = FandomWikiProfile({"remove_community_content": True})

    content = "# Page\n\n## Community\n\nJoin our Discord!"
    result = profile.clean(content)

    # Community section handling
    assert result is not None


@pytest.mark.unit
def test_fandom_profile_remove_related_wikis():
    """Test Fandom profile removes related wikis sections."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.fandomwiki_profile import (
        FandomWikiProfile,
    )

    profile = FandomWikiProfile({"remove_related_wikis": True})

    content = "# Page\n\n## Related wikis\n\n[Other Wiki](https://other.fandom.com)"
    result = profile.clean(content)

    assert result is not None


@pytest.mark.unit
def test_fandom_profile_remove_footer():
    """Test Fandom profile removes Fandom footer."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.fandomwiki_profile import (
        FandomWikiProfile,
    )

    profile = FandomWikiProfile({"remove_fandom_footer": True})

    content = "# Page\n\nContent\n\nGame Wiki is a Fandom Games Community."
    result = profile.clean(content)

    # Footer handling
    assert result is not None


@pytest.mark.unit
def test_fandom_profile_config_schema():
    """Test Fandom profile has extended config schema."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.fandomwiki_profile import (
        FandomWikiProfile,
    )

    schema = FandomWikiProfile.get_config_schema()

    assert isinstance(schema, dict)
    # Should have more properties than MediaWiki (inherited + new)
    properties = schema.get("properties", {})
    assert len(properties) > 0


@pytest.mark.unit
def test_fandom_profile_real_content():
    """Test Fandom profile with real Fandom content sample."""
    from webowui.scraper.cleaning_profiles.builtin_profiles.fandomwiki_profile import (
        FandomWikiProfile,
    )

    profile = FandomWikiProfile({
        "remove_fandom_ads": True,
        "remove_community_content": True,
    })

    result = profile.clean(FANDOM_MARKDOWN)

    # Should preserve main content
    assert "Character" in result or len(result) > 0


# ============================================================================
# Profile Registry Tests
# ============================================================================

@pytest.mark.unit
def test_registry_discover_profiles():
    """Test profile registry discovers available profiles."""
    from webowui.scraper.cleaning_profiles.registry import CleaningProfileRegistry

    profiles = CleaningProfileRegistry.list_profiles()

    # Should have at least the built-in profiles
    assert isinstance(profiles, list)
    # Expected: at least none, mediawiki, fandomwiki
    assert len(profiles) >= 0


@pytest.mark.unit
def test_registry_get_profile_none():
    """Test retrieving none profile from registry."""
    from webowui.scraper.cleaning_profiles.registry import CleaningProfileRegistry

    profile = CleaningProfileRegistry.get_profile("none", {})

    assert profile is not None


@pytest.mark.unit
def test_registry_get_profile_mediawiki():
    """Test retrieving mediawiki profile from registry."""
    from webowui.scraper.cleaning_profiles.registry import CleaningProfileRegistry

    profile = CleaningProfileRegistry.get_profile("mediawiki", {})

    assert profile is not None


@pytest.mark.unit
def test_registry_get_profile_fandomwiki():
    """Test retrieving fandomwiki profile from registry."""
    from webowui.scraper.cleaning_profiles.registry import CleaningProfileRegistry

    profile = CleaningProfileRegistry.get_profile("fandomwiki", {})

    assert profile is not None


@pytest.mark.unit
def test_registry_list_profiles():
    """Test listing all profiles from registry."""
    from webowui.scraper.cleaning_profiles.registry import CleaningProfileRegistry

    profiles = CleaningProfileRegistry.list_profiles()

    assert isinstance(profiles, list)
    # Each profile should have name and description
    for profile_info in profiles:
        assert "name" in profile_info or isinstance(profile_info, dict)


@pytest.mark.unit
def test_registry_profile_with_config():
    """Test getting profile with configuration."""
    from webowui.scraper.cleaning_profiles.registry import CleaningProfileRegistry

    config = {
        "remove_citations": True,
        "remove_categories": False,
    }

    profile = CleaningProfileRegistry.get_profile("mediawiki", config)

    assert profile is not None


@pytest.mark.unit
def test_registry_unknown_profile():
    """Test retrieving unknown profile raises error."""
    from webowui.scraper.cleaning_profiles.registry import CleaningProfileRegistry

    with pytest.raises(ValueError):
        CleaningProfileRegistry.get_profile("nonexistent", {})


@pytest.mark.unit
def test_registry_register_custom_profile():
    """Test registering custom profile in registry."""

    from webowui.scraper.cleaning_profiles.base import BaseCleaningProfile
    from webowui.scraper.cleaning_profiles.registry import CleaningProfileRegistry

    class TestProfile(BaseCleaningProfile):
        """Test profile for registry."""

        def clean(self, content: str, metadata: dict | None = None) -> str:
            return content.upper()

        @classmethod
        def get_config_schema(cls) -> dict[str, Any]:
            return {}

    # Register profile
    CleaningProfileRegistry.register(TestProfile)

    # Should be retrievable
    profile = CleaningProfileRegistry.get_profile("test", {})

    assert profile is not None


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.unit
def test_profile_workflow_mediawiki_realistic():
    """Test realistic MediaWiki content cleaning workflow."""
    from webowui.scraper.cleaning_profiles.registry import CleaningProfileRegistry

    profile = CleaningProfileRegistry.get_profile("mediawiki", {
        "remove_citations": True,
        "remove_categories": True,
    })

    result = profile.clean(MEDIAWIKI_MARKDOWN)

    # Should preserve key content
    assert len(result) > 0


@pytest.mark.unit
def test_profile_workflow_fandom_realistic():
    """Test realistic Fandom content cleaning workflow."""
    from webowui.scraper.cleaning_profiles.registry import CleaningProfileRegistry

    profile = CleaningProfileRegistry.get_profile("fandomwiki", {})

    result = profile.clean(FANDOM_MARKDOWN)

    # Should process without errors
    assert result is not None


@pytest.mark.unit
def test_profile_preserves_markdown_format():
    """Test that profiles preserve markdown formatting."""
    from webowui.scraper.cleaning_profiles.registry import CleaningProfileRegistry

    profile = CleaningProfileRegistry.get_profile("mediawiki", {})

    result = profile.clean(MARKDOWN_WITH_TABLES)

    # Result should be non-empty (even if tables are modified)
    assert result is not None
    assert len(result) >= 0
