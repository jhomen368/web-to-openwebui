"""
Command-line interface for web-to-openwebui.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import cast

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from .config import SiteConfig, app_config
from .scraper import WikiCrawler
from .state_manager import StateManager
from .storage import CurrentDirectoryManager, MetadataTracker, OutputManager
from .storage.retention_manager import RetentionManager
from .uploader import OpenWebUIClient

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(message)s", handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)

console = Console()


@click.group()
def cli():
    """web-to-openwebui - Web content scraping for OpenWebUI."""
    pass


@cli.command()
@click.option("--site", help="Site name to scrape")
@click.option("--all", "scrape_all", is_flag=True, help="Scrape all configured sites")
@click.option("--upload", is_flag=True, help="Upload after scraping")
def scrape(site, scrape_all, upload):
    """Scrape web content from configured site."""

    if not site and not scrape_all:
        console.print("[red]Error: Specify --site <name> or --all[/red]")
        sys.exit(1)

    sites = app_config.list_sites() if scrape_all else [site]

    if not sites:
        console.print("[red]No sites configured[/red]")
        sys.exit(1)

    for site_name in sites:
        try:
            console.print(f"\n[bold blue]Scraping site: {site_name}[/bold blue]")

            # Load config
            site_config = app_config.load_site_config(site_name)

            # Validate config
            errors = site_config.validate()
            if errors:
                console.print("[red]Configuration errors:[/red]")
                for error in errors:
                    console.print(f"  - {error}")
                continue

            # Run scrape
            asyncio.run(_scrape_site(site_config, upload))

        except FileNotFoundError as e:
            console.print(f"[red]Error: {e}[/red]")
        except Exception as e:
            logger.exception(f"Failed to scrape {site_name}")
            console.print(f"[red]Error: {e}[/red]")


async def _scrape_site(site_config: SiteConfig, do_upload: bool = False):
    """Scrape a single site."""

    # Create crawler
    crawler = WikiCrawler(site_config)

    # Perform crawl
    results = await crawler.crawl()

    # Save results
    output_manager = OutputManager(site_config, app_config.outputs_dir)
    save_info = output_manager.save_results(results)

    # Print stats
    stats = crawler.get_stats()
    console.print("\n[green]✓ Scrape complete![/green]")
    console.print(f"  Pages crawled: {stats['total_crawled']}")
    console.print(f"  Pages failed: {stats['total_failed']}")
    console.print(f"  Output directory: {save_info['output_dir']}")

    # Auto-cleanup if retention is enabled
    if site_config.retention_enabled and site_config.retention_auto_cleanup:
        site_dir = app_config.outputs_dir / site_config.name
        retention_mgr = RetentionManager(site_dir, site_config.retention_keep_backups)

        logger.info("Running retention cleanup...")
        result = retention_mgr.apply_retention(dry_run=False)

        if result["deleted"] > 0:
            console.print(f"\n[yellow]Retention:[/yellow] Deleted {result['deleted']} old backups")
            console.print(f"  Kept: {', '.join(result['kept_timestamps'][:3])}")
            if len(result["kept_timestamps"]) > 3:
                console.print(f"    ... and {len(result['kept_timestamps']) - 3} more")

    # Upload if requested
    if do_upload and site_config.auto_upload:
        console.print("\n[blue]Uploading to OpenWebUI...[/blue]")
        await _upload_scrape(
            site_config.name,
            save_info["timestamp"],
            site_config.knowledge_name,
            site_config.knowledge_description,
            site_config.knowledge_id,
        )


@cli.command()
@click.option("--site", required=True, help="Site name")
@click.option("--from-timestamp", help="Upload from specific timestamp instead of current/")
@click.option(
    "--incremental/--full", default=True, help="Incremental upload (default) or full upload"
)
@click.option(
    "--knowledge-id", help="Specify existing knowledge ID to upload to (overrides config)"
)
@click.option("--knowledge-name", help="Specify knowledge name (overrides config)")
@click.option(
    "--keep-files",
    is_flag=True,
    help="Keep deleted files in OpenWebUI (only remove from knowledge)",
)
@click.option(
    "--cleanup-untracked",
    is_flag=True,
    help="Delete untracked files in site folder (opt-in safety)",
)
def upload(
    site, from_timestamp, incremental, knowledge_id, knowledge_name, keep_files, cleanup_untracked
):
    """Upload scraped content to OpenWebUI (defaults to current/ directory)."""

    try:
        site_config = app_config.load_site_config(site)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    # Override with CLI options if provided
    target_knowledge_id = knowledge_id or site_config.knowledge_id
    target_knowledge_name = knowledge_name or site_config.knowledge_name

    # Determine keep_files: CLI flag overrides config setting
    effective_keep_files = keep_files or site_config.preserve_deleted_files

    # Determine cleanup_untracked: CLI flag overrides config (defaults to False - opt-in)
    effective_cleanup = cleanup_untracked or site_config.cleanup_untracked

    asyncio.run(
        _upload_scrape(
            site,
            from_timestamp,
            incremental,
            target_knowledge_name,
            site_config.knowledge_description,
            target_knowledge_id,
            effective_keep_files,
            effective_cleanup,  # Pass cleanup option
        )
    )


async def _upload_scrape(
    site_name: str,
    from_timestamp: str | None,
    incremental: bool,
    knowledge_name: str,
    knowledge_description: str = "",
    knowledge_id: str | None = None,
    keep_files: bool = False,
    cleanup_untracked: bool = False,
):
    """Upload a scrape to OpenWebUI."""

    # Validate API config
    api_errors = app_config.validate_openwebui_config()
    if api_errors:
        console.print("[red]OpenWebUI configuration errors:[/red]")
        for error in api_errors:
            console.print(f"  - {error}")
        sys.exit(1)

    # Determine upload source
    if from_timestamp:
        # Upload from specific timestamp (always full upload)
        tracker = MetadataTracker(app_config.outputs_dir, site_name)
        scrape = tracker.get_scrape_by_timestamp(from_timestamp)

        if not scrape:
            console.print(f"[red]Scrape not found: {from_timestamp}[/red]")
            sys.exit(1)

        content_dir = Path(scrape["scrape_dir"]) / "content"
        upload_source = from_timestamp
        files_to_upload = None  # Will upload all files
        files_to_delete = []
        previous_file_map = {}
        console.print(f"[blue]Uploading from timestamp: {from_timestamp}[/blue]")
        console.print("  Mode: Full upload")
    else:
        # Upload from current/ directory
        current_manager = CurrentDirectoryManager(app_config.outputs_dir, site_name)
        current_state = current_manager.get_current_state()

        if not current_state:
            console.print(f"[red]Current directory does not exist for {site_name}[/red]")
            console.print(f"  Run: [blue]webowui rebuild-current --site {site_name}[/blue]")
            console.print("  Or use: [blue]--from-timestamp <timestamp>[/blue]")
            sys.exit(1)

        content_dir = current_manager.content_dir
        upload_source = "current"

        # Get files for upload based on mode
        upload_info = current_manager.get_files_for_upload(incremental=incremental)

        files_to_upload = cast(list[dict], upload_info.get("upload", []))
        files_to_delete = upload_info.get("delete", [])
        previous_file_map = upload_info.get("previous_file_map", {})

        # Use knowledge_id from previous upload if available and not overridden
        if not knowledge_id and "knowledge_id" in upload_info:
            knowledge_id = upload_info["knowledge_id"]

        console.print("[blue]Uploading from current/ directory[/blue]")
        console.print(f"  Source timestamp: {current_state['source_timestamp']}")
        console.print(f"  Mode: {'Incremental' if incremental else 'Full'} upload")
        console.print(f"  {upload_info['summary']}")

        if keep_files and files_to_delete:
            console.print(
                "  [yellow]--keep-files enabled: Files will be removed from knowledge but not deleted[/yellow]"
            )

        # Check if no files to process
        if (files_to_upload is None or len(files_to_upload) == 0) and len(files_to_delete) == 0:
            if incremental:
                console.print("\n[yellow]⚠ No changes detected since last upload[/yellow]")
                console.print("  All files are up to date")
            return

        # Show what will be uploaded
        if files_to_upload and len(files_to_upload) > 0:
            console.print("\n[yellow]Files to upload:[/yellow]")
            for file_info in files_to_upload[:5]:
                console.print(f"  • {file_info['filename']}")
            if len(files_to_upload) > 5:
                console.print(f"  ... and {len(files_to_upload) - 5} more")

        if files_to_delete:
            action = "remove from knowledge" if keep_files else "delete"
            console.print(f"\n[yellow]Files to {action}:[/yellow]")
            for url in files_to_delete[:5]:
                console.print(f"  • {url}")
            if len(files_to_delete) > 5:
                console.print(f"  ... and {len(files_to_delete) - 5} more")

    # Check if already uploaded (only for timestamp uploads)
    if from_timestamp:
        tracker = MetadataTracker(app_config.outputs_dir, site_name)
        upload_status = tracker.get_upload_status(from_timestamp)
        if upload_status and upload_status.get("uploaded"):
            console.print(
                f"[yellow]⚠ This scrape was already uploaded on {upload_status['timestamp']}[/yellow]"
            )
            console.print(
                f"  Previous knowledge ID: {upload_status.get('knowledge_id', 'unknown')}"
            )
            if not click.confirm("Upload again?"):
                return

    # Create client and upload
    client = OpenWebUIClient(app_config.openwebui_base_url, app_config.openwebui_api_key)

    # Test connection
    connected = await client.test_connection()
    if not connected:
        console.print("[red]Failed to connect to OpenWebUI API[/red]")
        sys.exit(1)

    # Use StateManager for clean state detection and auto-rebuild
    if from_timestamp is None:
        state_manager = StateManager(current_manager, client)

        needs_rebuild, effective_knowledge_id, rebuilt_status = (
            await state_manager.detect_state_status(
                incremental,
                previous_file_map,
                knowledge_id,
                site_name,
                knowledge_name,
                min_confidence="medium",
            )
        )

        if needs_rebuild:
            if effective_knowledge_id and rebuilt_status:
                # Rebuild succeeded
                console.print(
                    f"[green]✓ State rebuilt successfully ({rebuilt_status['files_uploaded']} files matched)[/green]\n"
                )

                # Re-get upload info with rebuilt state
                upload_info = current_manager.get_files_for_upload(incremental=incremental)
                files_to_upload = cast(list[dict], upload_info.get("upload", []))
                files_to_delete = upload_info.get("delete", [])
                previous_file_map = upload_info.get("previous_file_map", {})
                knowledge_id = effective_knowledge_id
            else:
                # Rebuild failed or no knowledge_id found
                if not effective_knowledge_id:
                    console.print(
                        "\n[yellow]⚠ No upload state found - unable to find existing knowledge base[/yellow]"
                    )
                else:
                    console.print(
                        "\n[yellow]⚠ Auto-rebuild failed - proceeding with full upload[/yellow]"
                    )
                console.print()

    # Display what we're uploading to
    if knowledge_id:
        console.print(f"\n[blue]Uploading to existing knowledge (ID: {knowledge_id})...[/blue]")
    else:
        console.print(f"\n[blue]Uploading to knowledge: {knowledge_name}[/blue]")

    # Perform upload - use optimized incremental upload if available
    if incremental:
        # Ensure files_to_upload is not None (convert to empty list if needed)
        safe_files_to_upload = files_to_upload if files_to_upload is not None else []

        result = await client.upload_scrape_incrementally(
            content_dir,
            site_name,
            knowledge_name,
            safe_files_to_upload,
            files_to_delete,
            previous_file_map,
            knowledge_description,
            batch_size=10,
            knowledge_id=knowledge_id,
            keep_files=keep_files,
            cleanup_untracked=cleanup_untracked,
        )
    else:
        # Full upload - upload all files
        result = await client.upload_scrape_to_knowledge(
            content_dir,
            site_name,
            knowledge_name,
            knowledge_description,
            batch_size=10,
            knowledge_id=knowledge_id,
            specific_files=(
                [content_dir / f["filename"] for f in files_to_upload] if files_to_upload else None
            ),
        )

    if "error" in result:
        console.print(f"[red]Upload failed: {result['error']}[/red]")
        sys.exit(1)

    # Save upload status
    if from_timestamp:
        # Save to timestamp directory
        tracker = MetadataTracker(app_config.outputs_dir, site_name)
        tracker.save_upload_status(from_timestamp, result)
    else:
        # Save to current/ directory (StateManager already saved rebuild metadata if applicable)
        current_manager = CurrentDirectoryManager(app_config.outputs_dir, site_name)
        current_manager.save_upload_status(result)

    # Print results
    console.print("\n[green]✓ Upload complete![/green]")
    console.print(f"  Source: {upload_source}")
    console.print(f"  Knowledge: {result['knowledge_name']}")
    console.print(f"  Knowledge ID: {result['knowledge_id']}")

    # Display stats based on upload type
    if "files_updated" in result:
        # Incremental upload stats
        console.print(f"  Files uploaded: {result.get('files_uploaded', 0)}")
        console.print(f"  Files updated: {result.get('files_updated', 0)}")
        console.print(f"  Files deleted: {result.get('files_deleted', 0)}")
        if result.get("files_reuploaded", 0) > 0:
            console.print(
                f"  Files re-uploaded: {result.get('files_reuploaded', 0)} [yellow](externally deleted)[/yellow]"
            )
        if result.get("files_deleted_untracked", 0) > 0:
            console.print(
                f"  Files cleaned up: {result.get('files_deleted_untracked', 0)} [dim](untracked in folder)[/dim]"
            )
    else:
        # Full upload stats
        console.print(f"  Files uploaded: {result.get('files_uploaded', 0)}")
        console.print(f"  Files in knowledge: {result.get('files_added_to_knowledge', 0)}")


@cli.command(name="list")
@click.option("--site", help="Filter by site name")
def list_sites(site=None):  # Renamed "list" to avoid name collision with built-in list
    """List all scrapes."""

    sites = [site] if site else app_config.list_sites()

    for site_name in sites:
        tracker = MetadataTracker(app_config.outputs_dir, site_name)
        scrapes = tracker.get_all_scrapes()

        if not scrapes:
            continue

        console.print(f"\n[bold]{site_name}[/bold]")

        table = Table(show_header=True)
        table.add_column("Timestamp")
        table.add_column("Pages", justify="right")
        table.add_column("Success", justify="right")
        table.add_column("Failed", justify="right")
        table.add_column("Uploaded", justify="center")

        for scrape in scrapes:
            timestamp = scrape["scrape"]["timestamp"]
            stats = scrape["statistics"]

            upload_status = tracker.get_upload_status(timestamp)
            uploaded = "✓" if upload_status and upload_status.get("uploaded") else "✗"

            table.add_row(
                timestamp,
                str(stats["total_pages"]),
                str(stats["successful"]),
                str(stats["failed"]),
                uploaded,
            )

        console.print(table)


@cli.command()
@click.option("--site", required=True, help="Site name")
@click.option("--old", required=True, help="Old scrape timestamp")
@click.option("--new", required=True, help="New scrape timestamp")
def diff(site, old, new):
    """Compare two scrapes."""

    try:
        app_config.load_site_config(site)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    tracker = MetadataTracker(app_config.outputs_dir, site)
    comparison = tracker.compare_scrapes(old, new)

    if "error" in comparison:
        console.print(f"[red]{comparison['error']}[/red]")
        sys.exit(1)

    console.print(f"\n[bold]Comparison: {old} → {new}[/bold]\n")

    stats = comparison["statistics"]
    console.print(f"Added: {stats['added_count']}")
    console.print(f"Modified: {stats['modified_count']}")
    console.print(f"Removed: {stats['removed_count']}")
    console.print(f"Unchanged: {stats['unchanged_count']}")

    if stats["added_count"] > 0:
        console.print("\n[green]Added URLs:[/green]")
        for url in comparison["changes"]["added"][:10]:
            console.print(f"  + {url}")
        if stats["added_count"] > 10:
            console.print(f"  ... and {stats['added_count'] - 10} more")

    if stats["modified_count"] > 0:
        console.print("\n[yellow]Modified URLs:[/yellow]")
        for url in comparison["changes"]["modified"][:10]:
            console.print(f"  ~ {url}")
        if stats["modified_count"] > 10:
            console.print(f"  ... and {stats['modified_count'] - 10} more")

    if stats["removed_count"] > 0:
        console.print("\n[red]Removed URLs:[/red]")
        for url in comparison["changes"]["removed"][:10]:
            console.print(f"  - {url}")
        if stats["removed_count"] > 10:
            console.print(f"  ... and {stats['removed_count'] - 10} more")


@cli.command()
@click.option("--site", required=True, help="Site name")
@click.option("--list", "list_backups", is_flag=True, help="List available backups")
@click.option("--timestamp", help="Specific timestamp to rollback to")
@click.option("--force", is_flag=True, help="Force rollback without confirmation")
def rollback(site, list_backups, timestamp, force):
    """
    Rollback current/ directory to a previous backup.

    This command restores the current/ directory from a timestamped backup.
    It is useful for reverting accidental changes or corruption.

    Examples:
        # List available backups
        webowui rollback --site monsterhunter --list

        # Rollback to most recent backup
        webowui rollback --site monsterhunter

        # Rollback to specific timestamp
        webowui rollback --site monsterhunter --timestamp 2025-01-15_10-30-00
    """
    try:
        app_config.load_site_config(site)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    site_dir = app_config.outputs_dir / site
    if not site_dir.exists():
        console.print(f"[red]No output directory found for {site}[/red]")
        sys.exit(1)

    retention_mgr = RetentionManager(site_dir)
    backups = retention_mgr.get_scrape_directories()

    if not backups:
        console.print(f"[yellow]No backups found for {site}[/yellow]")
        return

    if list_backups:
        console.print(f"\n[bold]Available Backups for {site}:[/bold]")
        current_source = retention_mgr.get_current_source()

        table = Table(show_header=True)
        table.add_column("Timestamp")
        table.add_column("Status")

        for backup in backups:
            status = "Active Source" if backup.name == current_source else "Backup"
            table.add_row(backup.name, status)

        console.print(table)
        return

    # Determine target timestamp
    target_timestamp = timestamp
    if not target_timestamp:
        # Default to most recent backup
        target_timestamp = backups[0].name
        console.print(f"[blue]Selected most recent backup: {target_timestamp}[/blue]")

    # Verify backup exists
    target_dir = site_dir / target_timestamp
    if not target_dir.exists():
        console.print(f"[red]Backup not found: {target_timestamp}[/red]")
        sys.exit(1)

    # Confirm action
    if not force:
        console.print(
            f"\n[yellow]Warning: This will overwrite the current/ directory with content from {target_timestamp}[/yellow]"
        )
        if not click.confirm("Continue?"):
            console.print("[blue]Cancelled[/blue]")
            return

    # Perform rollback (using CurrentDirectoryManager logic via rebuild-current)
    # We can reuse the rebuild_current command logic or call CurrentDirectoryManager directly
    # Calling CurrentDirectoryManager is cleaner
    current_manager = CurrentDirectoryManager(app_config.outputs_dir, site)
    console.print(f"\n[blue]Rolling back to {target_timestamp}...[/blue]")

    result = current_manager.rebuild_from_timestamp(target_timestamp)

    if "error" in result:
        console.print(f"[red]Rollback failed: {result['error']}[/red]")
        sys.exit(1)

    console.print(f"\n[green]✓ {result['summary']}[/green]")
    console.print(
        f"  Run [blue]webowui upload --site {site} --incremental[/blue] to push changes to OpenWebUI"
    )


@cli.command()
def schedules():
    """List all configured schedules."""

    site_names = app_config.list_sites()

    if not site_names:
        console.print("[yellow]No sites configured[/yellow]")
        return

    table = Table(show_header=True, title="Scheduled Jobs")
    table.add_column("Site")
    table.add_column("Enabled")
    table.add_column("Type")
    table.add_column("Schedule")
    table.add_column("Timezone")
    table.add_column("Auto Upload")

    for site_name in site_names:
        try:
            site_config = app_config.load_site_config(site_name)

            enabled = "✓" if site_config.schedule_enabled else "✗"
            schedule_type = site_config.schedule_type if site_config.schedule_enabled else "-"

            if site_config.schedule_enabled:
                if site_config.schedule_type == "cron":
                    schedule = site_config.schedule_cron
                else:
                    schedule = f"Every {site_config.schedule_interval}"
            else:
                schedule = "-"

            timezone = site_config.schedule_timezone if site_config.schedule_enabled else "-"
            auto_upload = "✓" if site_config.auto_upload else "✗"

            table.add_row(site_name, enabled, schedule_type, schedule, timezone, auto_upload)
        except Exception as e:
            table.add_row(site_name, "ERROR", str(e), "", "", "")

    console.print(table)


@cli.command()
def daemon():
    """Run scheduler daemon (Docker mode)."""
    from .scheduler import ScraperScheduler

    scheduler = ScraperScheduler(app_config.config_dir, app_config.outputs_dir)
    scheduler.start()


@cli.command()
@click.option("--site", help="Site to clean (default: all sites)")
@click.option("--all", "clean_all", is_flag=True, help="Clean all sites")
@click.option("--keep", default=5, help="Number of recent scrapes to keep (default: 5)")
def clean(site, clean_all, keep):
    """Remove old scrapes."""

    if not site and not clean_all:
        console.print("[red]Error: Specify --site <name> or --all[/red]")
        sys.exit(1)

    sites = app_config.list_sites() if clean_all else [site]

    for site_name in sites:
        tracker = MetadataTracker(app_config.outputs_dir, site_name)
        scrapes = tracker.get_all_scrapes()

        if len(scrapes) <= keep:
            console.print(f"[yellow]{site_name}: Only {len(scrapes)} scrapes, skipping[/yellow]")
            continue

        console.print(f"[blue]{site_name}: Removing {len(scrapes) - keep} old scrapes[/blue]")
        tracker.cleanup_old_scrapes(keep)
        console.print(f"[green]✓ Cleaned {site_name}[/green]")


@cli.command()
@click.option("--site", required=True, help="Site name")
@click.option("--timestamp", help="Specific timestamp to reclean (default: current)")
@click.option("--profile", help="Cleaning profile to use (default: from site config)")
def reclean(site, timestamp, profile):
    """
    Re-clean scraped content with updated cleaning profile.

    Useful when you've updated a cleaning profile and want to apply it
    to existing scraped content without re-scraping.
    """
    from .utils.reclean import reclean_directory

    try:
        site_config = app_config.load_site_config(site)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    # Determine directory to clean
    if timestamp:
        tracker = MetadataTracker(app_config.outputs_dir, site)
        scrape = tracker.get_scrape_by_timestamp(timestamp)
        if not scrape:
            console.print(f"[red]Scrape not found: {timestamp}[/red]")
            sys.exit(1)
        content_dir = Path(scrape["scrape_dir"]) / "content"
    else:
        current_manager = CurrentDirectoryManager(app_config.outputs_dir, site)
        current_state = current_manager.get_current_state()
        if not current_state:
            console.print(f"[red]Current directory does not exist for {site}[/red]")
            sys.exit(1)
        content_dir = current_manager.content_dir

    # Determine profile
    profile_name = profile or site_config.cleaning_profile_name

    console.print(f"\n[blue]Re-cleaning content for {site}...[/blue]")
    console.print(f"  Directory: {content_dir}")
    console.print(f"  Profile: {profile_name}")

    reclean_directory(content_dir, profile_name)


@cli.command()
def sites():
    """List all configured sites."""

    site_list = app_config.list_sites()

    if not site_list:
        console.print("[yellow]No sites configured[/yellow]")
        return

    console.print("[bold]Configured Sites:[/bold]")
    console.print("[dim]Use these identifiers with --site parameter[/dim]\n")

    for site_name in site_list:
        try:
            site_config = app_config.load_site_config(site_name)
            console.print(f"  • [bold]{site_name}[/bold]")
            console.print(f"    Name: {site_config.display_name}")
            console.print(f"    URL: {site_config.base_url}")
            if site_config.knowledge_name:
                console.print(f"    KB: {site_config.knowledge_name}")
            console.print(f"    Auto-Upload: {site_config.auto_upload}")
            console.print(f"    Schedule: {site_config.schedule_enabled}\n")
        except Exception:
            console.print(f"  • [bold]{site_name}[/bold] [red](error loading)[/red]\n")


@cli.command()
@click.option("--site", help="Site name to validate (validates all sites if not specified)")
def validate(site):
    """
    Validate site configuration without running a scrape.

    Checks:
    - YAML syntax and structure
    - Required fields present
    - Valid crawling strategy
    - Valid cleaning profile
    - Valid URL patterns
    - OpenWebUI config (if present)

    Examples:
        # Validate specific site
        webowui validate --site monsterhunter

        # Validate all configured sites
        webowui validate
    """

    # Determine which sites to validate
    if site:
        sites_to_validate = [site]
    else:
        sites_to_validate = app_config.list_sites()
        if not sites_to_validate:
            console.print("[yellow]No sites configured[/yellow]")
            return

    # Create table for results
    table = Table(show_header=True, title="Site Configuration Validation")
    table.add_column("Site", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Errors", style="red")

    all_valid = True

    # Validate each site
    for site_name in sites_to_validate:
        try:
            site_config = app_config.load_site_config(site_name)
            errors = site_config.validate()

            if errors:
                all_valid = False
                status = "✗ Errors"
                error_msg = "\n".join(f"• {err}" for err in errors)
                table.add_row(site_name, status, error_msg)
            else:
                status = "✓ Valid"
                table.add_row(site_name, status, "")

        except FileNotFoundError:
            all_valid = False
            status = "✗ Errors"
            table.add_row(site_name, status, "• Config file not found")
        except Exception as e:
            all_valid = False
            status = "✗ Errors"
            table.add_row(site_name, status, f"• {str(e)}")

    # Display results
    console.print()
    console.print(table)
    console.print()

    # Exit with appropriate code
    if all_valid:
        console.print("[green]✓ All configurations valid[/green]\n")
        sys.exit(0)
    else:
        console.print("[red]✗ Some configurations have errors[/red]\n")
        sys.exit(1)


@cli.command(name="rebuild-current")
@click.option("--site", required=True, help="Site name")
@click.option("--timestamp", help="Timestamp to rebuild from (default: latest)")
@click.option("--force", is_flag=True, help="Rebuild even if current exists")
def rebuild_current(site, timestamp, force):
    """
    Rebuild current/ directory from a local scrape timestamp.

    This command creates or updates the current/ directory by copying files
    from a timestamped scrape backup. The current/ directory serves as the
    stable upload source for all incremental uploads to OpenWebUI.

    \b
    Use Cases:
      • Initial setup - create current/ from first scrape
      • Recovery - rebuild after current/ directory corruption
      • Rollback - restore previous version from backup
      • Migration - set up current/ on new system
      • Testing - switch between different scrape versions

    \b
    How It Works:
      1. Reads files from timestamped backup (e.g., 2025-01-15_10-30-00/)
      2. Copies all content to current/ directory
      3. Creates metadata.json with file tracking
      4. Initializes delta_log.json for change history
      5. Updates current/ as the active upload source

    \b
    Examples:
      # Rebuild from latest scrape (most common)
      webowui rebuild-current --site monsterhunter

      # Rebuild from specific timestamp (rollback)
      webowui rebuild-current --site monsterhunter --timestamp 2025-01-15_10-30-00

      # Force rebuild even if current/ exists
      webowui rebuild-current --site monsterhunter --force

      # List available timestamps first
      webowui list --site monsterhunter
      webowui rebuild-current --site monsterhunter --timestamp <chosen>

    \b
    Rollback Workflow:
      1. webowui rollback --site mysite --list    # See available backups
      2. webowui rollback --site mysite           # Rebuild from backup
      3. webowui upload --site mysite --incremental  # Upload restored state

    \b
    Related Commands:
      webowui rollback         # Easier rollback with retention-aware selection
      webowui rebuild-state    # Rebuild from OpenWebUI
      webowui show-current     # View current/ directory status
      webowui verify-current   # Check current/ integrity

    Note: This rebuilds from LOCAL timestamped backups, not from OpenWebUI.
    Use 'rebuild-state' to recover from OpenWebUI's remote state instead.
    """
    try:
        app_config.load_site_config(site)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    current_manager = CurrentDirectoryManager(app_config.outputs_dir, site)

    # Check if current exists
    current_state = current_manager.get_current_state()
    if current_state and not force:
        console.print(f"[yellow]{site}: Current directory already exists[/yellow]")
        console.print(f"  Source: {current_state['source_timestamp']}")
        console.print(f"  Files: {current_state['total_files']}")
        console.print(f"  Last updated: {current_state['last_updated']}")

        if not click.confirm("\nRebuild anyway?"):
            console.print("[blue]Cancelled[/blue]")
            return

    # Determine timestamp to use
    if not timestamp:
        tracker = MetadataTracker(app_config.outputs_dir, site)
        latest = tracker.get_latest_scrape()
        if not latest:
            console.print(f"[red]No scrapes found for {site}[/red]")
            sys.exit(1)
        timestamp = latest["scrape"]["timestamp"]
        console.print(f"[blue]Using latest scrape: {timestamp}[/blue]")

    # Rebuild
    console.print(f"\n[blue]Rebuilding current/ from {timestamp}...[/blue]")
    result = current_manager.rebuild_from_timestamp(timestamp)

    if "error" in result:
        console.print(f"[red]Rebuild failed: {result['error']}[/red]")
        sys.exit(1)

    console.print(f"\n[green]✓ {result['summary']}[/green]")


@cli.command()
def health():
    """Enhanced healthcheck for Docker."""
    import json
    import os
    import sys

    checks = {
        "config_dir": app_config.config_dir.exists(),
        "config_writable": os.access(app_config.config_dir, os.R_OK),
        "outputs_dir": app_config.outputs_dir.exists(),
        "outputs_writable": os.access(app_config.outputs_dir, os.W_OK),
        "sites_configured": len(app_config.list_sites()) > 0,
    }

    # Optional: Check OpenWebUI API connectivity
    if app_config.openwebui_api_key:
        try:
            client = OpenWebUIClient(app_config.openwebui_base_url, app_config.openwebui_api_key)
            checks["api_reachable"] = asyncio.run(client.test_connection())
        except Exception:
            checks["api_reachable"] = False

    healthy = all(checks.values())
    status = "healthy" if healthy else "unhealthy"

    result = {"status": status, "checks": checks}

    console.print(json.dumps(result, indent=2))
    sys.exit(0 if healthy else 1)


@cli.command(name="check-state")
@click.option("--site", required=True, help="Site name")
@click.option("--knowledge-id", help="Knowledge ID to check (uses config if not specified)")
def check_state(site, knowledge_id):
    """
    Check health of local upload state vs remote OpenWebUI state.

    This command verifies that your local tracking (upload_status.json) matches
    what is actually in OpenWebUI. It detects:
    - Missing remote files (deleted externally)
    - Extra remote files (shared knowledge base)
    - Corrupted state (all files missing)

    Use Cases:
    - Before running an incremental upload
    - Troubleshooting "file not found" errors
    - Verifying system integrity

    Examples:
        # Check state health
        webowui check-state --site monsterhunter

        # Check specific knowledge ID
        webowui check-state --site monsterhunter --knowledge-id abc123
    """
    asyncio.run(_check_state(site, knowledge_id))


@cli.command(name="rebuild-state")
@click.option("--site", required=True, help="Site name")
@click.option("--knowledge-id", help="Knowledge ID to rebuild from (uses config if not specified)")
@click.option(
    "--min-confidence",
    type=click.Choice(["high", "medium", "low"], case_sensitive=False),
    default="medium",
    help="Minimum match confidence required (default: medium)",
)
@click.option("--force", is_flag=True, help="Force rebuild even if state exists")
def rebuild_state(site, knowledge_id, min_confidence, force):
    """
    Rebuild upload_status.json from OpenWebUI using hash matching.

    Use Cases:
    - Lost upload_status.json (Docker volume loss, file corruption)
    - Migrating to new system (files exist in OpenWebUI)
    - Recovering from manual OpenWebUI changes

    The system matches local files with remote files using SHA-256
    hashes to reconstruct the file_id mappings.

    Examples:
        # Rebuild from configured knowledge base
        webowui rebuild-state --site monsterhunter

        # Rebuild from specific knowledge (if multiple exist)
        webowui rebuild-state --site monsterhunter --knowledge-id abc123

        # Accept lower confidence matches
        webowui rebuild-state --site monsterhunter --min-confidence low

    Related Commands:
        webowui check-state   # Check health before rebuilding
        webowui sync --fix    # Fix minor discrepancies (simpler)
    """
    asyncio.run(_rebuild_state(site, knowledge_id, min_confidence, force))


@cli.command()
@click.option("--site", required=True, help="Site name")
@click.option("--fix", is_flag=True, help="Automatically fix discrepancies")
@click.option("--knowledge-id", help="Specific knowledge ID to check (optional)")
def sync(site, fix, knowledge_id):
    """
    Reconcile local state with OpenWebUI remote state.

    Checks for:
    - Files in local state that were deleted in OpenWebUI
    - Files in OpenWebUI that aren't in local state (shared KB)
    - Mismatched file_ids

    With --fix flag, automatically corrects discrepancies.

    Use Cases:
    - Files deleted via OpenWebUI GUI
    - API changes or version updates
    - Verifying upload integrity

    Examples:
        # Check sync status
        webowui sync --site monsterhunter

        # Fix discrepancies (remove deleted files from local state)
        webowui sync --site monsterhunter --fix
    """
    asyncio.run(_sync_site(site, fix, knowledge_id))


@cli.command(name="show-current")
@click.option("--site", required=True, help="Site name")
@click.option("--verbose", is_flag=True, help="Show detailed file list")
def show_current(site, verbose):
    """Show current directory status."""

    try:
        app_config.load_site_config(site)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    current_manager = CurrentDirectoryManager(app_config.outputs_dir, site)
    current_state = current_manager.get_current_state()

    if not current_state:
        console.print(f"[yellow]Current directory does not exist for {site}[/yellow]")
        console.print(f"  Run: [blue]webowui rebuild-current --site {site}[/blue]")
        return

    console.print(f"\n[bold]{site} - Current Directory Status[/bold]\n")
    console.print(f"  Source: {current_state['source_timestamp']}")
    console.print(f"  Files: {current_state['total_files']}")
    console.print(f"  Size: {current_state['total_size'] / 1024:.1f} KB")
    console.print(f"  Last updated: {current_state['last_updated']}")

    # Show upload status if available
    upload_status = current_manager.get_upload_status()
    if upload_status:
        console.print("\n[bold]Upload Status:[/bold]")
        console.print(f"  Knowledge ID: {upload_status.get('knowledge_id', 'N/A')}")
        console.print(f"  Last upload: {upload_status.get('last_upload', 'Never')}")
        console.print(f"  Files tracked: {len(upload_status.get('files', []))}")

    if verbose and current_state.get("files"):
        console.print(f"\n[bold]Files ({len(current_state['files'])}):[/bold]")
        for file_info in current_state["files"][:20]:
            console.print(f"  • {file_info['filepath']}")
        if len(current_state["files"]) > 20:
            console.print(f"  ... and {len(current_state['files']) - 20} more")

    console.print()


async def _rebuild_state(
    site_name: str,
    knowledge_id: str | None,
    min_confidence: str,
    force: bool,
):
    """
    Perform state rebuild operation.

    This function rebuilds upload_status.json from OpenWebUI's remote state
    by matching local files with remote files using SHA-256 hash comparison.

    Args:
        site_name: Site name to rebuild state for
        knowledge_id: Optional knowledge ID (uses config if not provided)
        min_confidence: Minimum match confidence ('high', 'medium', 'low')
        force: Force rebuild even if state already exists
    """
    # Load site configuration
    try:
        site_config = app_config.load_site_config(site_name)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    # Validate OpenWebUI connection
    api_errors = app_config.validate_openwebui_config()
    if api_errors:
        console.print("[red]OpenWebUI configuration errors:[/red]")
        for error in api_errors:
            console.print(f"  - {error}")
        sys.exit(1)

    console.print(
        f"\n[bold blue]Rebuilding upload state for {site_config.display_name}[/bold blue]\n"
    )

    # Get current manager
    current_manager = CurrentDirectoryManager(app_config.outputs_dir, site_name)

    # Check if current directory exists
    metadata_file = current_manager.metadata_file
    if not metadata_file.exists():
        console.print("[red]✗ Current directory does not exist[/red]")
        console.print(f"  Run: [blue]webowui rebuild-current --site {site_name}[/blue]")
        sys.exit(1)

    # Check if state already exists
    upload_status = current_manager.get_upload_status()
    if upload_status and not force:
        console.print("[yellow]⚠ Upload state already exists[/yellow]")
        console.print(f"  Knowledge ID: {upload_status.get('knowledge_id')}")
        console.print(f"  Last upload: {upload_status.get('last_upload')}")
        console.print(f"  Files tracked: {len(upload_status.get('files', []))}")

        if not click.confirm("\nRebuild anyway (will overwrite)?"):
            console.print("[blue]Cancelled[/blue]")
            return

    # Determine knowledge_id
    target_kb_id = knowledge_id or site_config.knowledge_id

    # Create client
    client = OpenWebUIClient(app_config.openwebui_base_url, app_config.openwebui_api_key)

    if not await client.test_connection():
        console.print("[red]Failed to connect to OpenWebUI[/red]")
        sys.exit(1)

    if not target_kb_id:
        console.print("\n[dim]Searching for knowledge base by content...[/dim]")
        target_kb_id = await client.find_knowledge_by_content(site_name, site_config.knowledge_name)

        if not target_kb_id:
            console.print("[red]Could not find knowledge base[/red]")
            console.print("  Either:")
            console.print("  - Specify --knowledge-id <id>")
            console.print("  - Set knowledge_id in site config")
            console.print("  - Ensure site files exist in OpenWebUI")
            sys.exit(1)

        console.print(f"[green]✓ Found knowledge base: {target_kb_id}[/green]")

    console.print(f"\nKnowledge ID: {target_kb_id}")
    console.print(f"Site folder: {site_name}/")
    console.print(f"Minimum confidence: {min_confidence}\n")

    # Perform rebuild
    console.print("[dim]Matching local files with OpenWebUI state...[/dim]")
    console.print("[dim]This may take a moment for large knowledge bases...[/dim]\n")

    # Use StateManager for rebuild
    state_manager = StateManager(current_manager, client)
    success, rebuilt_status, rebuild_error = await state_manager.rebuild_from_remote(
        target_kb_id,
        site_name,
        min_confidence=min_confidence,
        auto_save=True,
    )

    if not success or not rebuilt_status:
        console.print(f"\n[red]✗ Rebuild failed: {rebuild_error}[/red]")
        console.print("  Possible reasons:")
        console.print("  - Match confidence below threshold")
        console.print("  - Too few files matched")
        console.print("  - Remote state unavailable")
        console.print("\n[yellow]Try:[/yellow]")
        console.print(
            f"  - Lower confidence: [blue]webowui rebuild-state --site {site_name} --min-confidence low[/blue]"
        )
        console.print(
            f"  - Check state health: [blue]webowui check-state --site {site_name}[/blue]"
        )
        console.print(
            f"  - Verify knowledge ID: [blue]webowui check-state --site {site_name} --knowledge-id <id>[/blue]"
        )
        sys.exit(1)

    # Display results
    console.print("\n[green]✓ State rebuilt successfully![/green]")
    console.print(f"  Knowledge ID: {rebuilt_status['knowledge_id']}")
    console.print(f"  Files matched: {rebuilt_status['files_uploaded']}")
    console.print(f"  Confidence: {rebuilt_status['rebuild_confidence']}")
    console.print(f"  Match rate: {rebuilt_status['rebuild_match_rate']*100:.1f}%")

    # Additional guidance based on confidence
    confidence = rebuilt_status.get("rebuild_confidence")
    if confidence in ["low", "very_low"]:
        console.print("\n[yellow]⚠ Low confidence rebuild[/yellow]")
        console.print("  Some files may have mismatched hashes (content changed)")
        console.print(f"  Verify with: [blue]webowui check-state --site {site_name}[/blue]")
        console.print(
            f"  Then upload: [blue]webowui upload --site {site_name} --incremental[/blue]"
        )
        console.print("  (Incremental upload will detect and update changed files)")
    else:
        console.print("\n[green]Ready to upload:[/green]")
        console.print(f"  [blue]webowui upload --site {site_name} --incremental[/blue]")

    console.print()


async def _check_state(site_name: str, knowledge_id: str | None):
    """Perform state health check."""
    # Load config
    try:
        site_config = app_config.load_site_config(site_name)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    # Validate API
    api_errors = app_config.validate_openwebui_config()
    if api_errors:
        console.print("[red]OpenWebUI configuration errors:[/red]")
        for error in api_errors:
            console.print(f"  - {error}")
        sys.exit(1)

    # Setup components
    current_manager = CurrentDirectoryManager(app_config.outputs_dir, site_name)
    client = OpenWebUIClient(app_config.openwebui_base_url, app_config.openwebui_api_key)
    state_manager = StateManager(current_manager, client)

    if not await client.test_connection():
        console.print("[red]Failed to connect to OpenWebUI[/red]")
        sys.exit(1)

    # Determine knowledge ID
    target_kb_id = knowledge_id
    if not target_kb_id:
        upload_status = current_manager.get_upload_status()
        if upload_status:
            target_kb_id = upload_status.get("knowledge_id")
        else:
            target_kb_id = site_config.knowledge_id

    if not target_kb_id:
        console.print("[red]No knowledge ID found. Cannot check state.[/red]")
        console.print("  Please specify --knowledge-id or configure it in site config.")
        sys.exit(1)

    # Run check
    console.print(f"\n[blue]Checking state health for {site_name}...[/blue]")
    console.print(f"  Knowledge ID: {target_kb_id}")

    health = await state_manager.check_health(target_kb_id, site_name)

    # Display results
    status_color = {
        "healthy": "green",
        "degraded": "yellow",
        "corrupted": "red",
        "missing": "red",
        "error": "red",
    }.get(health["status"], "white")

    console.print(f"\nStatus: [{status_color}]{health['status'].upper()}[/{status_color}]")
    console.print(f"  Local files: {health['local_file_count']}")
    console.print(f"  Remote files: {health['remote_file_count']}")

    if health["issues"]:
        console.print("\n[yellow]Issues Found:[/yellow]")
        for issue in health["issues"]:
            console.print(f"  • {issue}")

    if health.get("recommendation"):
        console.print(f"\n[blue]Recommendation:[/blue] {health['recommendation']}")

    console.print()


async def _sync_site(site_name: str, auto_fix: bool, knowledge_id: str | None):
    """Perform sync operation."""

    # Load config and check OpenWebUI connection
    try:
        app_config.load_site_config(site_name)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    client = OpenWebUIClient(app_config.openwebui_base_url, app_config.openwebui_api_key)

    if not await client.test_connection():
        console.print("[red]Failed to connect to OpenWebUI[/red]")
        sys.exit(1)

    # Setup StateManager
    current_manager = CurrentDirectoryManager(app_config.outputs_dir, site_name)
    state_manager = StateManager(current_manager, client)

    # Run sync via StateManager
    result = await state_manager.sync_state(site_name, knowledge_id, auto_fix)

    if not result["success"]:
        console.print(f"[red]Sync failed: {result.get('error', 'Unknown error')}[/red]")
        sys.exit(1)

    # Display findings
    console.print("[bold]Sync Results:[/bold]\n")
    console.print(f"  Local files: {result['local_count']}")
    console.print(f"  Remote files: {result['remote_count']}")
    console.print(f"  ✓ In sync: {result['in_sync_count']}")

    missing_remote = result["missing_remote"]
    extra_remote = result["extra_remote"]
    local_file_map = result.get("local_file_map", {})
    remote_files = result.get("remote_files", [])

    if missing_remote:
        console.print(
            f"\n[yellow]⚠ Files in local state but missing from OpenWebUI: {len(missing_remote)}[/yellow]"
        )
        for file_id in list(missing_remote)[:10]:
            file_info = local_file_map.get(file_id, {})
            console.print(f"  • {file_info.get('filename', 'unknown')} ({file_id})")
        if len(missing_remote) > 10:
            console.print(f"  ... and {len(missing_remote) - 10} more")

        if result.get("fixed_count", 0) > 0:
            console.print(
                f"\n[green]✓ Fixed: Removed {result['fixed_count']} files from local state[/green]"
            )

    if extra_remote:
        console.print(
            f"\n[yellow]⚠ Files in OpenWebUI but not in local state: {len(extra_remote)}[/yellow]"
        )
        console.print("  (This can happen if knowledge base is shared with other sites)")
        for file_id in list(extra_remote)[:10]:
            # Find file info from remote
            file_info = next((f for f in remote_files if f["id"] == file_id), {})
            filename = file_info.get("filename") if isinstance(file_info, dict) else file_id
            console.print(f"  • {filename}")
        if len(extra_remote) > 10:
            console.print(f"  ... and {len(extra_remote) - 10} more")

    if not missing_remote and not extra_remote:
        console.print("\n[green]✓ Local and remote states are in sync![/green]")

    console.print()
