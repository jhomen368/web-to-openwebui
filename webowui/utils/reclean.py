"""
Utility to re-clean existing scraped files with updated ContentCleaner.
"""

import sys
from pathlib import Path

from ..scraper.cleaning_profiles import CleaningProfileRegistry


def reclean_file(filepath: Path, profile_name: str = "mediawiki") -> tuple[int, int]:
    """Re-clean a single file. Returns (before_lines, after_lines)."""
    content = filepath.read_text(encoding="utf-8")

    # Count original non-frontmatter lines
    original_lines = [line for line in content.split("\n")[7:] if line.strip()]

    # Get profile
    try:
        profile = CleaningProfileRegistry.get_profile(profile_name)
    except ValueError:
        print(f"Warning: Profile '{profile_name}' not found, using 'mediawiki'")
        profile = CleaningProfileRegistry.get_profile("mediawiki")

    # Separate frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = "---" + parts[1] + "---"
            body = parts[2]
        else:
            frontmatter = ""
            body = content
    else:
        frontmatter = ""
        body = content

    # Apply new cleaner
    cleaned_body = profile.clean(body)

    new_content = frontmatter + "\n\n" + cleaned_body

    # Write back
    filepath.write_text(new_content, encoding="utf-8")

    new_lines = [line for line in cleaned_body.split("\n") if line.strip()]

    return len(original_lines), len(new_lines)


def reclean_directory(directory: Path, profile_name: str = "mediawiki"):
    """Re-clean all markdown files in a directory."""
    md_files = list(directory.rglob("*.md"))

    print(f"Found {len(md_files)} files to re-clean using profile '{profile_name}'")

    total_before = 0
    total_after = 0

    for filepath in md_files:
        before, after = reclean_file(filepath, profile_name)
        total_before += before
        total_after += after

        removed = before - after
        if removed > 0:
            print(f"✓ {filepath.name}: {before} → {after} lines (-{removed})")
        else:
            print(f"  {filepath.name}: {after} lines (no change)")

    print("\nTotal:")
    print(f"  Before: {total_before} lines")
    print(f"  After: {total_after} lines")
    print(f"  Removed: {total_before - total_after} lines of noise/dead links")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m webowui.utils.reclean <directory> [profile_name]")
        print(
            "Example: python -m webowui.utils.reclean outputs/monsterhunter_test/2025-11-14_13-20-38/content mediawiki"
        )
        sys.exit(1)

    directory = Path(sys.argv[1])
    profile_name = sys.argv[2] if len(sys.argv) > 2 else "mediawiki"

    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)

    reclean_directory(directory, profile_name)
