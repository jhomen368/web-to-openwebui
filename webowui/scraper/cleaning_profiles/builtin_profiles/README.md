# Cleaning Profiles

This directory contains content cleaning profiles that transform scraped content for optimal embedding generation.

## What are Cleaning Profiles?

Cleaning profiles remove noise (navigation, footers, citations) from scraped content before it's uploaded to OpenWebUI. This ensures embeddings focus on actual content rather than boilerplate text.

## Two-Stage Filtering Model

Content now goes through two filtering stages:

### Stage 1: Generic HTML Filtering (Optional)
**When:** During HTML → Markdown conversion by crawl4ai
**Configure:** `content_filtering` in site config
**Handles:** Generic elements (nav, footer, ads, social media)

```yaml
content_filtering:
  enabled: true
  excluded_tags: [nav, footer, aside]
  exclude_external_links: false
  exclude_social_media: false
```

### Stage 2: Site-Type Specific Cleaning
**When:** After markdown generation
**Configure:** `cleaning` profile in site config
**Handles:** Site-specific patterns (wiki markup, templates, etc.)

```yaml
cleaning:
  profile: "mediawiki"
  config:
    remove_infoboxes: true
```

**Recommendation:** Enable Stage 1 filtering for best results. Profiles focus on site-specific patterns that crawl4ai can't detect.

## Available Built-in Profiles

### `none` (Default)
- **Description**: Pass-through profile - no cleaning applied
- **Use Case**: When you want raw content or the site has minimal noise
- **Configuration**: None required

### `mediawiki`
- **Description**: Cleaning for MediaWiki-based sites
- **Removes**: Navigation menus, footers, categories, citations
- **Use Case**: Wikipedia, wiki.js, and other MediaWiki installations
- **Configuration**:
  ```yaml
  cleaning:
    profile: "mediawiki"
    config:
      filter_dead_links: true      # Remove links to non-existent pages
      remove_citations: true        # Remove citation markers
      remove_categories: true       # Remove category listings
  ```

### `fandomwiki`

**Description:** Enhanced MediaWiki cleaning specifically for Fandom wiki sites (fandom.com)

**Extends:** MediaWikiProfile (inherits all 8 MediaWiki cleaning methods)

**Why Extend MediaWiki:**
- Fandom wikis use MediaWiki engine as their base
- All MediaWiki cleaning methods work on Fandom content
- FandomWiki adds Fandom-specific cleaning on top

**Total Features:** 13 cleaning options (8 inherited + 5 new)

**Fandom-Specific Cleaning (5 new methods):**

1. **Advertising** (`remove_fandom_ads`)
   - Removes "Advertisement" markers scattered throughout pages
   - Removes ad placeholder text
   - Impact: Eliminates 5-10 lines of ad noise per page

2. **Promotions** (`remove_fandom_promotions`)
   - Removes "FANDOM powered by Wikia" branding
   - Removes "More Fandom" sections
   - Removes "Fan Central" and "Explore Fandom" widgets
   - Impact: Eliminates corporate branding and cross-promotions

3. **Community Content** (`remove_community_content`)
   - Removes Discord widget (200+ lines of user lists and avatars!)
   - Removes "Recent Images" feed
   - Removes community licensing text
   - Truncates at "Community" sections
   - Impact: Massive cleanup - 200+ lines per page

4. **Related Wikis** (`remove_related_wikis`)
   - Removes cross-wiki suggestions
   - Removes "Related wikis" sidebars
   - Removes Fandom discovery widgets
   - Impact: Eliminates cross-promotional content

5. **Fandom Footer** (`remove_fandom_footer`)
   - Removes Fandom global navigation footer
   - Removes "Follow Us" social media sections
   - Removes "Contact • Explore • Advertise" corporate footer
   - Impact: Removes 50+ lines of corporate navigation

**Inherited MediaWiki Features (8 methods):**
- Wiki meta messages
- Navigation boilerplate
- Table of contents
- Infoboxes
- External links sections
- Version history
- Template links ([v], [t], [e])
- Citations and categories (configurable)

**Use Case:** Any wiki hosted on `*.fandom.com`

**Compatible Wikis:**
- Gaming wikis (Escape from Tarkov, Minecraft, Terraria, etc.)
- TV show wikis (Star Wars, Marvel, Doctor Who, etc.)
- Movie wikis (Harry Potter, Lord of the Rings, etc.)
- Anime/Manga wikis (One Piece, Naruto, etc.)
- Book wikis (Game of Thrones, Discworld, etc.)

**Expected Improvement:** 50-60% reduction in noise, 3x better content density

**Simple Configuration (Recommended):**
```yaml
cleaning:
  profile: "fandomwiki"
  # All defaults active: MediaWiki cleaning + Fandom cleaning
```

**Override Specific Options:**
```yaml
cleaning:
  profile: "fandomwiki"
  config:
    # ----- Fandom-Specific Options (5) -----
    remove_fandom_ads: true                  # Remove "Advertisement" markers
    remove_fandom_promotions: true           # Remove Fandom branding
    remove_community_content: true           # Remove Discord widgets
    remove_related_wikis: true               # Remove cross-wiki suggestions
    remove_fandom_footer: true               # Remove Fandom global footer

    # ----- Inherited MediaWiki Options (8) -----
    remove_infoboxes: true                   # Remove metadata tables
    remove_external_links: true              # Remove "External Links" sections
    remove_table_of_contents: true           # Remove auto-generated TOC
    remove_version_history: true             # Remove changelog sections
    remove_wiki_meta: true                   # Remove wiki meta messages
    remove_navigation_boilerplate: true      # Remove "Jump to" links
    remove_template_links: true              # Remove [v], [t], [e] links
    filter_dead_links: false                 # Keep dead links
```

### `maxroll`
- **Description**: Cleaning for Maxroll.gg sites
- **Removes**: Global navigation sidebar, top navigation bar, footer, social media links
- **Use Case**: Maxroll.gg game guides and wikis
- **Configuration**:
  ```yaml
  cleaning:
    profile: "maxroll"
    config:
      remove_nav: true             # Remove global navigation and sidebar
      remove_footer: true          # Remove footer content
  ```

**Before/After Example:**

*Before (escape-from-tarkov-wiki.md):*
```markdown
[Sign In] [Register]
Escaper! You could encounter inaccurate information...
READ MORE
Advertisement
[Jump to navigation] [Jump to search]
## Contents
  * [1 Factions](#Factions)
...actual content...
## Escape from Tarkov Wiki Discord
**6595** Users Online
![](avatar1) User 1
![](avatar2) User 2
[...200+ lines of Discord widget...]
## Recent Images
[...15 lines of recent uploads...]
### Follow Us
[Social media links]
### Advertise
Escape from Tarkov Wiki is a Fandom Games Community.
View Mobile Site
```

*After (FandomWiki profile):*
```markdown
# Escape from Tarkov Wiki
...actual content only...
## Factions
...
```

**Testing Tips:**

1. **Start with depth 1** for testing:
   ```yaml
   crawling:
     max_depth: 1
   ```

2. **Compare before/after**:
   ```bash
   # Scrape with "none" profile first
   webowui scrape --site mysite

   # Change to "fandomwiki" and re-scrape
   webowui scrape --site mysite
   ```

3. **Check content density** - FandomWiki profile should reduce file sizes by 50-60%

4. **Verify main content preserved** - Article headings, paragraphs, tables should remain

**Common Issues:**

**Issue:** Too much removed
**Solution:** Disable specific cleaning methods one at a time to find the culprit

**Issue:** Discord widget remains
**Solution:** Check if `remove_community_content: true` is set

**Issue:** Footer navigation remains
**Solution:** Check if `remove_fandom_footer: true` is set

**Best Practices:**

✅ Use FandomWiki profile for ALL *.fandom.com sites
✅ Keep all default settings enabled (they're optimized)
✅ Test with small scrapes first (depth 1)
✅ Compare cleaned output to verify quality
❌ Don't use MediaWiki profile for Fandom sites (misses 400+ lines of noise)
❌ Don't disable community content removal (huge waste of tokens)

## Creating Custom Profiles

1. **Create a new file** in this directory: `mysite_profile.py`

2. **Use this template**:
```python
from webowui.scraper.cleaning_profiles.base import BaseCleaningProfile
from typing import Dict, Any, Optional
import re

class MySiteProfile(BaseCleaningProfile):
    """Describe what this profile cleans."""

    def clean(self, content: str, metadata: Optional[Dict] = None) -> str:
        """Clean content according to your rules."""
        # Your cleaning logic here
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            # Example: Skip lines containing "Advertisement"
            if "Advertisement" in line:
                continue
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define your configuration options."""
        return {
            "type": "object",
            "properties": {
                "remove_ads": {
                    "type": "boolean",
                    "default": True
                },
                "min_line_length": {
                    "type": "number",
                    "default": 10
                }
            }
        }
```

3. **Reference in your site config**:
```yaml
# config/sites/mysite.yaml
cleaning:
  profile: "mysite"
  config:
    remove_ads: true
    min_line_length: 15
```

4. **Restart or run next scrape** - your profile is automatically discovered!

**See also:** [`webowui/config/examples/README.md`](../../../config/examples/README.md) for site configuration templates.

## Configuration in Site Config

Add to your site's YAML file:

```yaml
cleaning:
  # Profile name (must match *_profile.py filename without "_profile")
  profile: "mediawiki"

  # Profile-specific configuration (optional)
  config:
    filter_dead_links: true
    remove_citations: true
```

If no `cleaning` section exists, defaults to `"none"` profile (no cleaning).

## Tips for Writing Profiles

1. **Start with existing profiles** - Copy and modify `mediawiki_profile.py`
2. **Test incrementally** - Run small scrapes to verify cleaning works
3. **Use metadata** - The `metadata` parameter contains `url` and `site_config`
4. **Handle edge cases** - Some pages might have unusual structure
5. **Document patterns** - Add comments explaining what patterns you're removing

## How Profiles Work

1. **Auto-Discovery**: All `*_profile.py` files are automatically loaded
2. **Registration**: Profile classes are registered by name (e.g., `MySiteProfile` → `"mysite"`)
3. **Instantiation**: When scraping, the configured profile is instantiated with its config
4. **Execution**: The `clean()` method is called for each scraped page
5. **Result**: Cleaned content is saved to the output directory

## Examples

### Removing Specific Sections
```python
def clean(self, content: str, metadata: Optional[Dict] = None) -> str:
    # Remove everything after "## See Also"
    if "## See Also" in content:
        content = content.split("## See Also")[0]
    return content
```

### URL-Specific Cleaning
```python
def clean(self, content: str, metadata: Optional[Dict] = None) -> str:
    url = metadata.get('url', '') if metadata else ''

    # Different cleaning for different URL patterns
    if '/guides/' in url:
        # Remove navigation specific to guides
        content = self._remove_guide_navigation(content)
    elif '/reference/' in url:
        # Keep technical details in reference pages
        pass

    return content
```

### Extending Existing Profiles
```python
from .mediawiki_profile import MediaWikiProfile

class MyWikiProfile(MediaWikiProfile):
    """Extends MediaWiki with custom cleaning."""

    def clean(self, content: str, metadata: Optional[Dict] = None) -> str:
        # First run parent MediaWiki cleaning
        content = super().clean(content, metadata)

        # Then add your custom cleaning
        content = self._remove_custom_elements(content)

        return content
```

## Troubleshooting

**Profile not found**: Ensure filename ends with `_profile.py` and class inherits from `BaseCleaningProfile`

**Config validation error**: Check your config matches the schema in `get_config_schema()`

**Cleaning too aggressive**: Test with small scrapes and adjust patterns gradually

**Want to modify built-in profiles**: Edit them directly! They're copied here for your convenience.

## Best Practices

- ✅ Remove navigation, footers, and boilerplate
- ✅ Keep article structure (headings, lists, tables)
- ✅ Remove citations if they add noise
- ✅ Test with multiple pages from the site
- ❌ Don't remove actual content or headings
- ❌ Don't make cleaning site-specific unless necessary
- ❌ Don't forget to handle edge cases (empty lines, special characters)
