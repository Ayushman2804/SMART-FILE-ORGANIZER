# Smart File Organizer (Python)

A reliable, cross-platform Python CLI automation utility that systematically categorizes and declutters messy directories (such as `Downloads` or `Desktop`) into organized folders based on file category, year of last modification, and SHA-256 duplicate detection.

Built purely using the **Python Standard Library** (`pathlib`, `shutil`, `hashlib`, `argparse`, `json`, `datetime`) — zero external dependencies required.

---

## Key Features

- **Category & Temporal Sorting**: Automatically matches file extensions against configurable rules and sorts them into `<Category>/<Year>/` structures. Unmatched files are safely routed to `Others/<Year>/`.
- **SHA-256 Byte-Level Deduplication (`--dedup`)**:
  - Computes cryptographic SHA-256 checksums to detect exact duplicate files, even if filenames differ (e.g., `report.pdf` vs `report_copy (1).pdf`).
  - Safely isolates duplicates into a separate `Duplicates/<Year>/` folder (default) or permanently cleans them up with `--dedup-action delete`.
- **Collision-Safe Renaming**: Never overwrites existing files. Automatically resolves naming conflicts for distinct files using incremental suffixes (e.g., `invoice_1.pdf`).
- **Safe Dry-Run Mode (`--dry-run`)**: Preview all planned file movements and duplicate detections in the terminal before touching a single file.
- **Instant Rollback / Undo (`--undo`)**: Logs all transfer operations to `organizer_log.json`. Run with `--undo` to cleanly restore all files to their original locations and automatically prune empty generated folders.
- **Self-Protection & Re-nesting Prevention**:
  - Automatically skips system files (`desktop.ini`, `thumbs.db`, `.DS_Store`).
  - Ignores hidden files and in-progress downloads (`.crdownload`, `.part`, `.tmp`).
  - Prevents recursive re-nesting of already organized category and duplicate folders.
  - Protects the organizer script, configs, and repository root files from being moved.
- **Cross-Platform & Path-Independent**: Uses `pathlib.Path` with automatic path resolution, allowing you to run the script from any working directory.
- **Configurable Categories**: Easily extend or customize category mappings via `config.json` or pass a custom config with `--config`.

---

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/Ayushman2804/SMART-FILE-ORGANIZER.git
cd SMART-FILE-ORGANIZER
```

### 2. Preview Organization (Dry Run)
Test how your directory will be organized without moving any files:
```bash
python smart_file_organizer.py --path "C:/Users/YourName/Downloads" --dry-run
```

### 3. Organize with Duplicate Detection
Organize files and automatically isolate true byte duplicates:
```bash
python smart_file_organizer.py --path "C:/Users/YourName/Downloads" --dedup
```

### 4. Delete Exact Duplicates
Preview or delete byte-identical duplicate files:
```bash
# Preview duplicate deletions safely first:
python smart_file_organizer.py --path "C:/Users/YourName/Downloads" --dedup --dedup-action delete --dry-run

# Execute:
python smart_file_organizer.py --path "C:/Users/YourName/Downloads" --dedup --dedup-action delete
```

### 5. Roll Back (Undo)
Accidentally organized the wrong folder or want to revert? Restore everything with a single command:
```bash
python smart_file_organizer.py --undo
```

---

## CLI Options

| Flag | Short | Description |
| :--- | :---: | :--- |
| `--path <dir>` | `-p` | Path to the directory you want to organize (**required** for organize mode) |
| `--dry-run` | `-d` | Preview prospective file moves without applying changes |
| `--dedup` | | Enable SHA-256 byte-level duplicate detection |
| `--dedup-action` | | Action for duplicates: `move` (default, into `Duplicates/`) or `delete` |
| `--undo` | `-u` | Revert the last organization session and restore files |
| `--config <file>` | `-c` | Path to a custom category JSON configuration file |
| `--verbose` | `-v` | Display detailed logs including reasons for skipped files |
| `--help` | `-h` | Show CLI help message and flag references |

---

## Default File Categories (`config.json`)

The default configuration includes 8 modern categories:

| Category | File Extensions |
| :--- | :--- |
| **Images** | `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`, `.bmp`, `.tiff`, `.ico` |
| **Documents** | `.pdf`, `.docx`, `.doc`, `.txt`, `.pptx`, `.ppt`, `.odt`, `.rtf`, `.md` |
| **Music** | `.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`, `.m4a` |
| **Videos** | `.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm` |
| **Archives** | `.zip`, `.tar`, `.gz`, `.rar`, `.7z`, `.bz2`, `.xz`, `.iso` |
| **Data** | `.csv`, `.xlsx`, `.xls`, `.json`, `.parquet`, `.sql`, `.tsv`, `.xml` |
| **Code** | `.py`, `.js`, `.ts`, `.html`, `.css`, `.cpp`, `.c`, `.java`, `.sh`, `.bat`, `.ipynb`, `.rs`, `.go` |
| **Executables** | `.exe`, `.msi`, `.dmg`, `.pkg`, `.deb`, `.rpm`, `.apk` |
| *Duplicates* | Isolated duplicate copies (when `--dedup` is enabled) |
| *Others* | All unrecognized file extensions |

---

## Running Automated Tests

A comprehensive unit test suite (12 tests) is included to verify collision handling, SHA-256 hashing, duplicate move/delete actions, dry-run simulation, re-nesting protection, undo rollbacks, and error fallbacks:

```bash
python test_organizer.py
```

---

## Technologies Used

- **Language**: Python 3.8+
- **Modules**: `pathlib`, `shutil`, `hashlib`, `argparse`, `json`, `datetime`, `unittest`
