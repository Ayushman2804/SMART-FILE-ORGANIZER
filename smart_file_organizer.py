"""Smart File Organizer (Python).

A robust CLI automation tool that systematically categorizes and declutters
directories by file type and modification year, featuring collision safety,
SHA-256 byte-level deduplication, content-aware NLP/AI document categorization,
dry-run preview, operation rollback (undo), and self-protection filters.
"""

import argparse
from datetime import datetime
import hashlib
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
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".tiff", ".ico"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".pptx", ".ppt", ".odt", ".rtf", ".md"],
    "Music": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
    "Archives": [".zip", ".tar", ".gz", ".rar", ".7z", ".bz2", ".xz", ".iso"],
    "Data": [".csv", ".xlsx", ".xls", ".json", ".parquet", ".sql", ".tsv", ".xml"],
    "Code": [".py", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".java", ".sh", ".bat", ".ipynb", ".rs", ".go"],
    "Executables": [".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".apk"],
}

# Semantic document classification taxonomy
DOC_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "Invoices_Receipts": {
        "keywords": [
            "invoice", "receipt", "bill to", "billed to", "tax invoice", "subtotal",
            "total amount", "amount due", "payment receipt", "gstin", "order id",
            "payment due", "remit to", "vat", "purchase order", "transaction id",
            "balance due", "unit price"
        ],
    },
    "Resumes_Career": {
        "keywords": [
            "curriculum vitae", "resume", "work experience", "education", "technical skills",
            "projects", "certifications", "job description", "responsibilities", "employment history",
            "qualifications", "internship", "hiring", "applicant", "contact information",
            "b.tech", "bachelor of", "master of"
        ],
    },
    "Research_Academic": {
        "keywords": [
            "abstract", "introduction", "methodology", "literature review", "references",
            "conclusion", "proceedings of", "arxiv", "ieee", "springer", "acm",
            "university", "syllabus", "thesis", "dissertation", "lecture notes",
            "doi:", "experiment", "citation", "conference"
        ],
    },
    "Legal_Contracts": {
        "keywords": [
            "agreement", "contract", "terms and conditions", "terms of service", "privacy policy",
            "non-disclosure", "nda", "confidentiality", "governing law", "jurisdiction",
            "indemnification", "arbitration", "hereby agrees", "parties hereto",
            "intellectual property", "in witness whereof"
        ],
    },
    "Technical_Guides": {
        "keywords": [
            "api documentation", "user manual", "getting started", "installation guide",
            "architecture", "cheatsheet", "release notes", "troubleshooting", "sdk",
            "endpoint", "configuration guide", "developer guide"
        ],
    },
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


def compute_file_hash(file_path: Path, chunk_size: int = 65536) -> Optional[str]:
    """Calculate the SHA-256 checksum of a file efficiently using streamed byte chunks."""
    if not file_path.is_file():
        return None
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (PermissionError, OSError):
        return None


def extract_document_text(file_path: Path, max_chars: int = 4000) -> str:
    """Extract readable text from PDF, DOCX, TXT, or markdown documents."""
    ext = file_path.suffix.lower()

    # Plain text formats
    if ext in {".txt", ".md", ".rtf", ".csv", ".json", ".xml", ".html", ".py"}:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(max_chars)
        except OSError:
            return ""

    # PDF format (uses pypdf if available)
    if ext == ".pdf":
        try:
            import logging
            logging.getLogger("pypdf").setLevel(logging.ERROR)
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            extracted: List[str] = []
            for page in reader.pages[:3]:  # Check first 3 pages
                text = page.extract_text()
                if text:
                    extracted.append(text)
                if sum(len(t) for t in extracted) >= max_chars:
                    break
            if extracted:
                return "\n".join(extracted)[:max_chars]
        except Exception:
            pass

        # Fallback in case of mock or non-standard text streams
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(max_chars)
        except OSError:
            return ""

    # DOCX format (pure stdlib zipfile/xml parser)
    if ext == ".docx":
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(file_path) as z:
                if "word/document.xml" in z.namelist():
                    xml_content = z.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    return "".join(node.text for node in tree.iter() if node.text)[:max_chars]
        except Exception:
            return ""

    return ""


def classify_document(file_path: Path) -> Tuple[str, float]:
    """Analyze document filename and text content to predict its semantic subcategory.

    Returns:
        (subcategory_name, confidence_percent)
    """
    text_content = extract_document_text(file_path).lower()
    name_clean = file_path.stem.lower().replace("_", " ").replace("-", " ")

    scores: Dict[str, float] = {cat: 0.0 for cat in DOC_TAXONOMY}

    for cat, data in DOC_TAXONOMY.items():
        keywords = data["keywords"]
        for kw in keywords:
            # Filename matches provide high confidence
            if kw in name_clean:
                scores[cat] += 3.5

            # Content matches
            if text_content:
                count = text_content.count(kw)
                if count > 0:
                    scores[cat] += min(count, 4) * 1.0

    best_cat, best_score = max(scores.items(), key=lambda x: x[1])

    # Minimum threshold to avoid misclassification
    if best_score >= 2.0:
        confidence = min(round((best_score / (best_score + 3.0)) * 100, 1), 99.0)
        return best_cat, confidence

    return "General", 0.0


def get_unique_path(dest_folder: Path, filename: str) -> Path:
    """Generate a collision-safe destination path by appending an incremental counter."""
    target_path = dest_folder / filename
    if not target_path.exists():
        return target_path

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
    dedup: bool = False,
    dedup_action: str = "move",
    smart_docs: bool = False,
    log_path: Path = DEFAULT_LOG_PATH,
    verbose: bool = False,
) -> None:
    """Scan and organize loose files in target_dir according to category, year, and content."""
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

    if dedup:
        print(f"[DEDUP]  SHA-256 byte deduplication active (Action: {dedup_action.upper()})")
    if smart_docs:
        print("[SMART]  Content-aware document classification enabled")

    # Identify protected paths that must never be moved
    protected_paths: Set[Path] = {
        Path(__file__).resolve(),
        DEFAULT_CONFIG_PATH.resolve(),
        log_path.resolve(),
        (BASE_DIR / "README.md").resolve(),
    }

    # All recognized categories + 'Others' and 'Duplicates'
    category_names: Set[str] = set(config.keys()) | {"Others", "Duplicates"}

    log_data: List[Dict[str, Any]] = []
    stats: Dict[str, int] = {
        "moved": 0,
        "duplicates_moved": 0,
        "duplicates_deleted": 0,
        "skipped": 0,
        "errors": 0,
    }
    category_counts: Dict[str, int] = {cat: 0 for cat in category_names}
    doc_subcounts: Dict[str, int] = {subcat: 0 for subcat in list(DOC_TAXONOMY.keys()) + ["General"]}

    # Hash cache for duplicate detection: hash -> original_path
    seen_hashes: Dict[str, Path] = {}

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

        # Extract modification year
        try:
            mtime = item.stat().st_mtime
            year = datetime.fromtimestamp(mtime).strftime("%Y")
        except OSError:
            year = "Unknown"

        # Check for true byte duplicate if deduplication is enabled
        duplicate_ref: Optional[Path] = None
        item_hash: Optional[str] = None

        if dedup:
            item_hash = compute_file_hash(item)
            if item_hash:
                # 1. Check if identical file was encountered in this batch
                if item_hash in seen_hashes:
                    duplicate_ref = seen_hashes[item_hash]
                else:
                    # 2. Check if identical file already exists in expected destination
                    item_ext = item.suffix.lower()
                    target_category = "Others"
                    for cat, extensions in config.items():
                        if item_ext in extensions:
                            target_category = cat
                            break
                    potential_dest = target_root / target_category / year / item.name
                    if potential_dest.exists() and compute_file_hash(potential_dest) == item_hash:
                        duplicate_ref = potential_dest

        # Handle Duplicate
        if duplicate_ref is not None:
            if dedup_action == "delete":
                if dry_run:
                    print(f"  [DUP-DEL]  {item.name} (identical to {duplicate_ref.name})")
                    stats["duplicates_deleted"] += 1
                else:
                    try:
                        item.unlink()
                        print(f"  [DUP-DEL]  {item.name} (deleted - identical to {duplicate_ref.name})")
                        stats["duplicates_deleted"] += 1
                        log_data.append({
                            "action": "delete",
                            "timestamp": datetime.now().isoformat(),
                            "source": str(item.resolve()),
                            "destination": None,
                            "original_parent": str(target_root),
                            "is_duplicate": True,
                            "duplicate_of": str(duplicate_ref.resolve()),
                        })
                    except (PermissionError, OSError) as e:
                        print(f"  [ERROR]   Could not delete {item.name}: {e}")
                        stats["errors"] += 1
                continue
            else:
                # Default dedup action: move to Duplicates/<Year>/
                dup_folder = target_root / "Duplicates" / year
                unique_dest_path = get_unique_path(dup_folder, item.name)

                if dry_run:
                    print(f"  [DUP-MOVE] {item.name} -> Duplicates/{year}/{unique_dest_path.name} (identical to {duplicate_ref.name})")
                    stats["duplicates_moved"] += 1
                    category_counts["Duplicates"] += 1
                else:
                    try:
                        dup_folder.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(item), str(unique_dest_path))
                        print(f"  [DUP-MOVE] {item.name} -> Duplicates/{year}/{unique_dest_path.name}")
                        stats["duplicates_moved"] += 1
                        category_counts["Duplicates"] += 1
                        log_data.append({
                            "action": "move",
                            "timestamp": datetime.now().isoformat(),
                            "source": str(item.resolve()),
                            "destination": str(unique_dest_path.resolve()),
                            "original_parent": str(target_root),
                            "is_duplicate": True,
                            "duplicate_of": str(duplicate_ref.resolve()),
                        })
                    except (PermissionError, OSError) as e:
                        print(f"  [ERROR]   Could not move duplicate {item.name}: {e}")
                        stats["errors"] += 1
                continue

        # Standard Category Resolution
        item_ext = item.suffix.lower()
        matched_category = "Others"

        for category, extensions in config.items():
            if item_ext in extensions:
                matched_category = category
                break

        # Check for smart document classification
        subcat: Optional[str] = None
        conf: float = 0.0

        if matched_category == "Documents" and smart_docs:
            subcat, conf = classify_document(item)
            doc_subcounts[subcat] += 1
            dest_folder = target_root / "Documents" / subcat / year
        else:
            dest_folder = target_root / matched_category / year

        unique_dest_path = get_unique_path(dest_folder, item.name)
        display_rel = dest_folder.relative_to(target_root) / unique_dest_path.name

        if dry_run:
            if subcat:
                print(f"  [SMART-DOC] {item.name} -> {display_rel} ({conf}% conf)")
            else:
                print(f"  [DRY RUN]   {item.name} -> {display_rel}")
            stats["moved"] += 1
            category_counts[matched_category] += 1
            if dedup and item_hash:
                seen_hashes[item_hash] = unique_dest_path
        else:
            try:
                dest_folder.mkdir(parents=True, exist_ok=True)
                shutil.move(str(item), str(unique_dest_path))
                if subcat:
                    print(f"  [SMART-DOC] {item.name} -> {display_rel} ({conf}% conf)")
                else:
                    print(f"  [MOVED]     {item.name} -> {display_rel}")

                stats["moved"] += 1
                category_counts[matched_category] += 1
                if dedup and item_hash:
                    seen_hashes[item_hash] = unique_dest_path
                log_data.append({
                    "action": "move",
                    "timestamp": datetime.now().isoformat(),
                    "source": str(item.resolve()),
                    "destination": str(unique_dest_path.resolve()),
                    "original_parent": str(target_root),
                    "is_duplicate": False,
                    "doc_subcategory": subcat,
                })
            except (PermissionError, OSError) as e:
                print(f"  [ERROR]     Could not move {item.name}: {e}")
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

    if smart_docs and any(cnt > 0 for cnt in doc_subcounts.values()):
        print("\nDocument Subcategories:")
        for sc, cnt in doc_subcounts.items():
            if cnt > 0:
                print(f"    * {sc:18}: {cnt}")

    if dedup:
        total_dups = stats["duplicates_moved"] + stats["duplicates_deleted"]
        action_note = "deleted" if dedup_action == "delete" else "moved to Duplicates/"
        print(f"\nDuplicates Detected:   {total_dups} ({action_note})")

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
    roots: Set[Path] = set()

    for entry in reversed(log_data):
        action = entry.get("action", "move")
        src_str = entry.get("destination")
        dest_str = entry.get("source")
        parent_root_str = entry.get("original_parent")

        if parent_root_str:
            roots.add(Path(parent_root_str))

        if action == "delete":
            print(f"  [NOTICE]   Permanently deleted duplicate cannot be restored: {dest_str}")
            continue

        if not src_str or not dest_str:
            continue

        src_path = Path(src_str)
        dest_path = Path(dest_str)

        if src_path.exists():
            try:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
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

    # Prune now-empty category, subcategory, and year folders all the way up to target root
    pruned_count = 0
    for folder in affected_dirs:
        # Match target root if recorded
        matching_root = next((r for r in roots if folder.is_relative_to(r)), folder.parent.parent)
        pruned_count += prune_empty_dir_chain(folder, matching_root)

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
        description="Smart File Organizer: Categorize & sort files safely by type, year, and content."
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
        "--dedup",
        action="store_true",
        help="Enable SHA-256 byte-level duplicate detection",
    )
    parser.add_argument(
        "--dedup-action",
        choices=["move", "delete"],
        default="move",
        help="Action for detected duplicates: 'move' (default, moves to Duplicates/) or 'delete'",
    )
    parser.add_argument(
        "--smart-docs",
        "-s",
        action="store_true",
        help="Enable AI/NLP semantic document classification (Invoices, Resumes, Academic, Legal, Technical, General)",
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
        dedup=args.dedup,
        dedup_action=args.dedup_action,
        smart_docs=args.smart_docs,
        log_path=log_file,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
