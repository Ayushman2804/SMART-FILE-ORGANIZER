"""Smart File Organizer (Python).

A robust CLI automation tool that systematically categorizes and declutters
directories by file type and modification year, featuring collision safety,
dry-run preview, operation rollback (undo), and self-protection filters.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

# Configure stdout to handle UTF-8 safely on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Base paths resolved relative to this script
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config.json"
DEFAULT_LOG_PATH = BASE_DIR / "organizer_log.json"

# Default fallback categories if config.json is missing or corrupted
FALLBACK_CONFIG: Dict[str, List[str]] = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".pptx", ".xlsx", ".csv"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
    "Music": [".mp3", ".wav", ".flac", ".aac"],
}

# System files, temp files, and extensions to always ignore
IGNORED_FILENAMES: Set[str] = {
    "desktop.ini",
    "thumbs.db",
    ".ds_store",
    "icon\r",
}

IGNORED_EXTENSIONS: Set[str] = {
    ".tmp",
    ".crdownload",  # Chrome in-progress download
    ".part",        # Firefox in-progress download
    ".download",    # Safari in-progress download
    ".partial",     # Generic partial download
}


def load_config(config_path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, List[str]]:
    """Load category mappings from config JSON file, falling back if not found."""
    if not config_path.exists():
        print(f"[!] Warning: Config file not found at '{config_path}'. Using defaults.")
        return FALLBACK_CONFIG

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                # Ensure all extensions are lowercased and prefixed with '.'
                normalized: Dict[str, List[str]] = {}
                for category, exts in data.items():
                    if isinstance(exts, list):
                        normalized[category] = [
                            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                            for ext in exts
                        ]
                return normalized
            print("[!] Warning: Config file format invalid. Using defaults.")
            return FALLBACK_CONFIG
    except (json.JSONDecodeError, OSError) as e:
        print(f"[!] Warning: Failed to parse '{config_path}': {e}. Using defaults.")
        return FALLBACK_CONFIG


def load_log(log_path: Path = DEFAULT_LOG_PATH) -> List[Dict[str, Any]]:
    """Safely load transaction logs for undo operations."""
    if not log_path.exists():
        return []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as e:
        print(f"[!] Error: Could not read transaction log '{log_path}': {e}")
        return []


def save_log(log_data: List[Dict[str, Any]], log_path: Path = DEFAULT_LOG_PATH) -> None:
    """Persist file operations log to enable safe rollback."""
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4)
    except OSError as e:
        print(f"[!] Error saving log to '{log_path}': {e}")


def get_unique_path(dest_folder: Path, filename: str) -> Path:
    """Generate a collision-safe destination path by appending an incremental counter."""
    target_path = dest_folder / filename
    if not target_path.exists():
        return target_path

    # Extract stem and suffix carefully
    stem = target_path.stem
    suffix = target_path.suffix

    counter = 1
    while True:
        candidate = dest_folder / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def is_protected(
    item: Path,
    target_root: Path,
    protected_paths: Set[Path],
    category_names: Set[str],
) -> Tuple[bool, str]:
    """Check if an item should be protected from moving.

    Returns:
        (True, reason) if the item should not be moved, else (False, "").
    """
    # 1. Do not process directories directly (only top-level files)
    if item.is_dir():
        return True, "Directory (not loose file)"

    # 2. Never move the script itself, config, log, or workspace root assets
    resolved_item = item.resolve()
    if resolved_item in protected_paths:
        return True, "Protected script/system file"

    name_lower = item.name.lower()

    # 3. Hidden files (starting with dot)
    if name_lower.startswith("."):
        return True, "Hidden file"

    # 4. Known OS system files
    if name_lower in IGNORED_FILENAMES:
        return True, "System file"

    # 5. Temporary / in-progress downloads
    if any(name_lower.endswith(ext) for ext in IGNORED_EXTENSIONS):
        return True, "In-progress / temporary download"

    # 6. Prevent re-nesting files already inside target category folders
    try:
        relative_parts = item.relative_to(target_root).parts
        if len(relative_parts) > 1 and relative_parts[0] in category_names:
            return True, f"Already organized in '{relative_parts[0]}'"
    except ValueError:
        pass

    return False, ""


def prune_empty_dir_chain(folder: Path, stop_at: Path) -> int:
    """Climb up from folder to stop_at, removing any directory that is completely empty."""
    removed = 0
    current = folder.resolve()
    boundary = stop_at.resolve()

    while current != boundary and current.exists() and current.is_dir():
        try:
            # If directory has contents, stop climbing
            if any(current.iterdir()):
                break
            current.rmdir()
            removed += 1
            current = current.parent
        except OSError:
            break

    return removed


def organize(
    target_dir: Path,
    config: Dict[str, List[str]],
    dry_run: bool = False,
    log_path: Path = DEFAULT_LOG_PATH,
    verbose: bool = False,
) -> None:
    """Scan and organize loose files in target_dir according to category and year."""
    if not target_dir.exists():
        print(f"[x] Error: Target directory '{target_dir}' does not exist.")
        return

    if not target_dir.is_dir():
        print(f"[x] Error: '{target_dir}' is not a directory.")
        return

    target_root = target_dir.resolve()
    print(f"\n[TARGET] {target_root}")
    if dry_run:
        print("[MODE]   DRY RUN (Preview only - no files will be moved)")
    else:
        print("[MODE]   LIVE EXECUTION")

    # Identify protected paths that must never be moved
    protected_paths: Set[Path] = {
        Path(__file__).resolve(),
        DEFAULT_CONFIG_PATH.resolve(),
        log_path.resolve(),
        (BASE_DIR / "README.md").resolve(),
    }

    # All recognized categories + 'Others'
    category_names: Set[str] = set(config.keys()) | {"Others"}

    log_data: List[Dict[str, Any]] = []
    stats: Dict[str, int] = {"moved": 0, "skipped": 0, "errors": 0}
    category_counts: Dict[str, int] = {cat: 0 for cat in category_names}

    try:
        items = list(target_root.iterdir())
    except OSError as e:
        print(f"[x] Error accessing '{target_root}': {e}")
        return

    for item in items:
        # Protection and ignore checks
        should_skip, reason = is_protected(item, target_root, protected_paths, category_names)
        if should_skip:
            stats["skipped"] += 1
            if verbose:
                print(f"  [SKIP] {item.name} ({reason})")
            continue

        # Determine Category
        item_ext = item.suffix.lower()
        matched_category = "Others"

        for category, extensions in config.items():
            if item_ext in extensions:
                matched_category = category
                break

        # Extract modification year
        try:
            mtime = item.stat().st_mtime
            year = datetime.fromtimestamp(mtime).strftime("%Y")
        except OSError:
            year = "Unknown"

        # Construct destination directory: <target>/<Category>/<Year>
        dest_folder = target_root / matched_category / year
        unique_dest_path = get_unique_path(dest_folder, item.name)

        if dry_run:
            print(f"  [DRY RUN] {item.name} -> {matched_category}/{year}/{unique_dest_path.name}")
            stats["moved"] += 1
            category_counts[matched_category] += 1
        else:
            try:
                dest_folder.mkdir(parents=True, exist_ok=True)
                shutil.move(str(item), str(unique_dest_path))
                print(f"  [MOVED]   {item.name} -> {matched_category}/{year}/{unique_dest_path.name}")
                stats["moved"] += 1
                category_counts[matched_category] += 1
                log_data.append({
                    "timestamp": datetime.now().isoformat(),
                    "source": str(item.resolve()),
                    "destination": str(unique_dest_path.resolve()),
                    "original_parent": str(target_root),
                })
            except (PermissionError, OSError) as e:
                print(f"  [ERROR]   Could not move {item.name}: {e}")
                stats["errors"] += 1

    # Save transaction log on successful non-dry runs
    if not dry_run and log_data:
        save_log(log_data, log_path)

    # Output Summary Report
    print("\n" + "=" * 45)
    print("ORGANIZATION SUMMARY")
    print("=" * 45)
    print(f"Total Files Organized: {stats['moved']}")
    for cat, count in category_counts.items():
        if count > 0:
            print(f"  - {cat:12}: {count}")
    print(f"Items Skipped/Ignored: {stats['skipped']}")
    if stats["errors"] > 0:
        print(f"Failed Transfers:      {stats['errors']}")
    print("=" * 45)

    if dry_run:
        print("Tip: Run without --dry-run to apply changes.\n")
    else:
        print("[SUCCESS] Finished successfully! (Use --undo to revert)\n")


def undo(log_path: Path = DEFAULT_LOG_PATH) -> None:
    """Roll back the last organization session using recorded log data."""
    log_data = load_log(log_path)

    if not log_data:
        print("[!] No recorded operations found to undo.")
        return

    print(f"\n[UNDO] Initiating rollback for {len(log_data)} operations...")
    restored = 0
    errors = 0
    affected_dirs: Set[Path] = set()

    for entry in reversed(log_data):
        src_str = entry.get("destination")
        dest_str = entry.get("source")

        if not src_str or not dest_str:
            continue

        src_path = Path(src_str)
        dest_path = Path(dest_str)

        if src_path.exists():
            try:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                # If original filename was renamed on conflict, restore safely
                safe_dest = get_unique_path(dest_path.parent, dest_path.name)
                shutil.move(str(src_path), str(safe_dest))
                print(f"  [RESTORED] {src_path.name} -> {safe_dest.parent}")
                restored += 1
                affected_dirs.add(src_path.parent)
            except (PermissionError, OSError) as e:
                print(f"  [ERROR] Failed to restore {src_path.name}: {e}")
                errors += 1
        else:
            print(f"  [SKIP] File not found (moved or deleted): {src_path.name}")

    # Prune now-empty category and year folders
    pruned_count = 0
    for folder in affected_dirs:
        # Stop at root directory
        stop_boundary = folder.parent.parent if folder.parent and folder.parent.parent else folder.parent
        pruned_count += prune_empty_dir_chain(folder, stop_boundary)

    # Clear log after undo completes
    save_log([], log_path)

    print("\n" + "=" * 45)
    print("UNDO SUMMARY")
    print("=" * 45)
    print(f"Files Restored:        {restored}")
    if pruned_count > 0:
        print(f"Empty Folders Pruned:  {pruned_count}")
    if errors > 0:
        print(f"Errors Encountered:    {errors}")
    print("=" * 45)
    print("[SUCCESS] Undo completed successfully!\n")


def main() -> None:
    """CLI entry point for Smart File Organizer."""
    parser = argparse.ArgumentParser(
        description="Smart File Organizer: Categorize & sort files safely by type and year."
    )
    parser.add_argument(
        "--path",
        "-p",
        help="Target folder path to organize (e.g. ~/Downloads)",
    )
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Simulate the reorganization without moving files",
    )
    parser.add_argument(
        "--undo",
        "-u",
        action="store_true",
        help="Revert the last organization operation",
    )
    parser.add_argument(
        "--config",
        "-c",
        help="Path to custom config.json file",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed skip reasons and debug information",
    )

    args = parser.parse_args()

    # Determine config file path
    config_file = Path(args.config).resolve() if args.config else DEFAULT_CONFIG_PATH
    log_file = DEFAULT_LOG_PATH

    if args.undo:
        undo(log_path=log_file)
        return

    if not args.path:
        parser.print_help()
        print("\n[!] Please specify a folder path using --path / -p")
        sys.exit(1)

    target_path = Path(args.path).expanduser().resolve()
    config = load_config(config_file)
    organize(
        target_dir=target_path,
        config=config,
        dry_run=args.dry_run,
        log_path=log_file,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
