"""
Sample test content data.

Provides predefined test content including markdown, HTML, and metadata
for use in content cleaning and processor tests.
"""

import json
from typing import Any

# ============================================================================
# Markdown Content Samples
# ============================================================================

MINIMAL_MARKDOWN = """# Page Title

This is minimal content."""


BASIC_MARKDOWN = """---
url: https://example.com/page
title: Sample Page
scraped_at: 2025-11-20T01:15:00Z
---

# Sample Page

This is a basic page with some content.

## Section 1

Content for section 1.

## Section 2

Content for section 2.
"""


MARKDOWN_WITH_LISTS = """# Page with Lists

## Unordered List

- Item 1
- Item 2
  - Nested item 2.1
  - Nested item 2.2
- Item 3

## Ordered List

1. First
2. Second
3. Third

## Definition List

term 1
: definition 1

term 2
: definition 2
"""


MARKDOWN_WITH_TABLES = """# Page with Tables

## Simple Table

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |

## Complex Table

| Header 1 | Header 2 | Header 3 |
|:---------|:--------:|---------:|
| Left     | Center   | Right    |
| A        | B        | C        |
"""


MARKDOWN_WITH_CODE = """# Page with Code

## Python Code

```python
def hello_world():
    '''Say hello'''
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
```

## JavaScript Code

```javascript
function greet(name) {
  console.log(`Hello, ${name}!`);
}

greet("World");
```

## Inline Code

Use `const x = 5;` in your JavaScript.
"""


MARKDOWN_WITH_LINKS = """# Page with Links

## External Links

- [Python Documentation](https://docs.python.org)
- [GitHub](https://github.com)
- [OpenWebUI](https://openwebui.com)

## Image Link

![Sample Image](https://example.com/image.png)

## Link with Title

[Link with title](https://example.com "This is a title")

## Bare URL Reference

https://example.com
"""


MARKDOWN_WITH_REFERENCES = """# Page with References

This page contains references[^1] and citations[^2].

Some content here with inline references.

## References

[^1]: This is the first reference note.
[^2]: This is the second reference note with more detail.

## External Links

- See also: [Related Page](https://example.com/related)
- More info: [Another Page](https://example.com/info)

## Navigation

[Previous](https://example.com/prev) | [Next](https://example.com/next)
"""


MEDIAWIKI_MARKDOWN = """---
url: https://wiki.example.com/wiki/Sample
title: Sample Page
source: MediaWiki
---

The wiki is currently a work in progress.

# Sample Page

Rathalos is a dragon-type monster.

Jump to navigation Jump to search

## Contents
- 1 Description
- 2 Behavior
- 3 Habitats

## Description

Rathalos is a blue and red dragon known for its aerial combat.

### Combat Behavior

It uses both fire and wind-based attacks.

## Habitats

Ancient Forest
Coral Highlands
Wildspire Waste

## See also

- Rathian
- Pink Rathian

Retrieved from "https://wiki.example.com/wiki/Sample"

Categories: Dragons, Flying Wyverns
"""


FANDOM_MARKDOWN = """---
url: https://game.fandom.com/wiki/Character
title: Character Page
source: Fandom Wiki
---

# Character

This is a character page.

Advertisement

## Overview

A skilled warrior known for combat prowess.

## Background

Story and lore information.

## Related wikis

[Related Wiki 1](https://other.fandom.com)
[Related Wiki 2](https://another.fandom.com)

## Community

Join our Discord server!

Community content is available under CC BY-NC-SA unless otherwise noted.

Game Wiki is a Fandom Games Community.
"""


# ============================================================================
# HTML Content Samples
# ============================================================================

BASIC_HTML = """<!DOCTYPE html>
<html>
<head><title>Sample Page</title></head>
<body>
<h1>Sample Page</h1>
<p>This is a paragraph.</p>
<p>This is another paragraph.</p>
</body>
</html>
"""


MEDIAWIKI_HTML = """<!DOCTYPE html>
<html>
<head><title>Sample - Wiki</title></head>
<body>
<div id="mw-page-base" class="noprint"></div>
<div class="mw-parser-output">
  <div class="mw-parser-output">
    <h1>Sample</h1>
    <p>This is the main content.</p>
    <h2>Section 1</h2>
    <p>Section 1 content.</p>
    <h2>External links</h2>
    <ul>
      <li><a href="https://example.com">Example</a></li>
    </ul>
  </div>
</div>
<div class="navbox">Navigation boxes</div>
<div id="footer">Footer content</div>
</body>
</html>
"""


FANDOM_HTML = """<!DOCTYPE html>
<html>
<head><title>Character - Game Wiki | Fandom</title></head>
<body>
<div class="page-header">
  <h1>Character</h1>
</div>
<div class="wikia-article">
  <div class="ad-slot">Advertisement</div>
  <p>Character description.</p>
  <h2>Background</h2>
  <p>Background story.</p>
  <div class="related-wikis">
    <h3>Related Wikis</h3>
    <ul>
      <li><a href="https://other.fandom.com">Other Wiki</a></li>
    </ul>
  </div>
  <div class="footer">
    <p>This is a Fandom Games Community</p>
  </div>
</div>
</body>
</html>
"""


# ============================================================================
# Metadata Sample Data
# ============================================================================

SAMPLE_SCRAPE_METADATA: dict[str, Any] = {
    "site": {
        "name": "example_wiki",
        "display_name": "Example Wiki",
        "base_url": "https://example.com",
    },
    "scrape": {
        "timestamp": "2025-11-20_01-15-00",
        "duration_seconds": 45.3,
        "total_pages": 10,
        "successful_pages": 10,
        "failed_pages": 0,
        "skipped_pages": 0,
    },
    "files": [
        {
            "url": "https://example.com/page1",
            "filepath": "content/page1.md",
            "filename": "page1.md",
            "checksum": "abc123def456",
            "size": 2048,
            "scraped_at": "2025-11-20T01:15:10Z",
            "status": "success",
        },
        {
            "url": "https://example.com/page2",
            "filepath": "content/page2.md",
            "filename": "page2.md",
            "checksum": "xyz789uvw012",
            "size": 1536,
            "scraped_at": "2025-11-20T01:15:20Z",
            "status": "success",
        },
    ],
}


SAMPLE_UPLOAD_STATUS: dict[str, Any] = {
    "site_name": "example_wiki",
    "knowledge_id": "kb-example-123",
    "knowledge_name": "Example Knowledge",
    "last_upload": "2025-11-20T01:16:00Z",
    "last_timestamp": "2025-11-20_01-15-00",
    "files": [
        {
            "url": "https://example.com/page1",
            "filename": "page1.md",
            "filepath": "content/page1.md",
            "file_id": "file-abc123",
            "checksum": "abc123def456",
            "uploaded_at": "2025-11-20T01:16:10Z",
            "status": "success",
        },
        {
            "url": "https://example.com/page2",
            "filename": "page2.md",
            "filepath": "content/page2.md",
            "file_id": "file-xyz789",
            "checksum": "xyz789uvw012",
            "uploaded_at": "2025-11-20T01:16:20Z",
            "status": "success",
        },
    ],
}


DELTA_LOG_ENTRY: dict[str, Any] = {
    "timestamp": "2025-11-20_01-15-00",
    "operation": "update",
    "changes": {
        "added": 2,
        "modified": 1,
        "removed": 0,
    },
    "details": {
        "added": [
            "https://example.com/new1",
            "https://example.com/new2",
        ],
        "modified": [
            "https://example.com/updated",
        ],
        "removed": [],
    },
}


# ============================================================================
# Content Variation Samples
# ============================================================================

CONTENT_VARIATIONS: dict[str, str] = {
    "empty": "",
    "whitespace_only": "   \n\n   \t\t",
    "single_line": "Just a single line.",
    "heading_only": "# Heading\n",
    "heading_no_content": "# Heading\n\nNo body content.",
    "with_unicode": "# 日本語（にほんご）\n\nCyrillic: Привет\n\nEmoji: 🎉",
    "very_long_heading": "# " + "A" * 200,
    "nested_lists": "- Item 1\n  - Sub 1\n    - Sub Sub 1\n  - Sub 2\n- Item 2",
    "mixed_content": (
        "# Title\n\n"
        "Paragraph with **bold** and *italic*.\n\n"
        "```code\nblock\n```\n\n"
        "[Link](https://example.com)\n\n"
        "| A | B |\n|---|---|\n| 1 | 2 |"
    ),
}


# ============================================================================
# Corrupted/Edge Case Content
# ============================================================================

CORRUPTED_MARKDOWN = """---
url: https://example.com/bad
title: Corrupted Page
---

[Unclosed link](https://example.com

# Heading without closing

| Table | Header |
| incomplete

```code without closing

Text with unmatched **bold or *italic*.
"""


EDGE_CASE_CONTENT: dict[str, str] = {
    "null_bytes": "Content with null\x00byte",
    "high_unicode": "Content with high unicode: \U0001f600",
    "control_chars": "Content\x01\x02\x03with control chars",
    "bom_header": "\ufeffContent with BOM",
    "mixed_line_endings": "Line 1\rLine 2\nLine 3\r\nLine 4",
}


# ============================================================================
# Helper Functions
# ============================================================================


def get_markdown_variation(name: str) -> str:
    """
    Get a markdown content variation by name.

    Args:
        name: Variation name (basic, with_code, with_tables, etc.)

    Returns:
        str: Markdown content

    Raises:
        KeyError: If variation not found
    """
    variations = {
        "minimal": MINIMAL_MARKDOWN,
        "basic": BASIC_MARKDOWN,
        "with_lists": MARKDOWN_WITH_LISTS,
        "with_tables": MARKDOWN_WITH_TABLES,
        "with_code": MARKDOWN_WITH_CODE,
        "with_links": MARKDOWN_WITH_LINKS,
        "with_references": MARKDOWN_WITH_REFERENCES,
        "mediawiki": MEDIAWIKI_MARKDOWN,
        "fandom": FANDOM_MARKDOWN,
    }

    if name not in variations:
        raise KeyError(
            f"Unknown markdown variation: {name}. " f"Available: {', '.join(variations.keys())}"
        )

    return variations[name]


def get_html_sample(name: str) -> str:
    """
    Get an HTML content sample by name.

    Args:
        name: Sample name (basic, mediawiki, fandom)

    Returns:
        str: HTML content

    Raises:
        KeyError: If sample not found
    """
    samples = {
        "basic": BASIC_HTML,
        "mediawiki": MEDIAWIKI_HTML,
        "fandom": FANDOM_HTML,
    }

    if name not in samples:
        raise KeyError(f"Unknown HTML sample: {name}. " f"Available: {', '.join(samples.keys())}")

    return samples[name]


def get_metadata_json_string(name: str = "scrape") -> str:
    """
    Get metadata as JSON string.

    Args:
        name: Type of metadata (scrape, upload, delta)

    Returns:
        str: JSON string

    Raises:
        KeyError: If metadata type not found
    """
    metadata_map = {
        "scrape": SAMPLE_SCRAPE_METADATA,
        "upload": SAMPLE_UPLOAD_STATUS,
        "delta": DELTA_LOG_ENTRY,
    }

    if name not in metadata_map:
        raise KeyError(
            f"Unknown metadata type: {name}. " f"Available: {', '.join(metadata_map.keys())}"
        )

    return json.dumps(metadata_map[name], indent=2)
