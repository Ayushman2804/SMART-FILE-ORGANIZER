# Smart File Organizer (Python)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black.svg)](https://github.com/psf/black)

A reliable, cross-platform Python CLI automation utility that systematically categorizes and declutters messy directories (such as `Downloads` or `Desktop`) into organized folders based on file category, year of last modification, SHA-256 duplicate detection, content-aware AI/NLP document classification, and real-time background folder monitoring.

Built on the **Python Standard Library** (`pathlib`, `shutil`, `hashlib`, `argparse`, `json`, `datetime`) with zero mandatory external dependencies, and enhanced with optional integrations for `watchdog`, `pypdf`, and `rich`.

---

## Key Features

- **Category & Temporal Sorting**: Automatically matches file extensions against configurable rules and sorts them into `<Category>/<Year>/` structures. Unmatched files are safely routed to `Others/<Year>/`.
- **Real-Time Folder Watcher (`--watch`)**:
  - Monitors directories continuously in the background using `watchdog`.
  - Automatically organizes new files (e.g., fresh downloads or saved exports) the moment they land on disk.
- **Smart AI/NLP Document Classification (`--smart-docs`)**:
  - Parses and analyzes the text content of documents (`.pdf`, `.docx`, `.txt`, `.md`, `.rtf`).
  - Semantically classifies documents into designated subcategories:
    - `Invoices_Receipts/` (bills, tax invoices, receipts, payment proofs)
    - `Resumes_Career/` (CVs, resumes, job descriptions, portfolios)
    - `Research_Academic/` (papers, theses, lecture notes, syllabus)
    - `Legal_Contracts/` (NDAs, agreements, terms of service, policies)
    - `Technical_Guides/` (API docs, architecture guides, cheatsheets)
    - `General/` (miscellaneous text documents)
  - Resulting structure: `Documents/<Subcategory>/<Year>/<filename>`.
- **SHA-256 Byte-Level Deduplication (`--dedup`)**:
  - Computes cryptographic SHA-256 checksums to detect exact duplicate files, even if filenames differ (e.g., `report.pdf` vs `report_copy (1).pdf`).
  - Safely isolates duplicates into a separate `Duplicates/<Year>/` folder (default) or permanently cleans them up with `--dedup-action delete`.
- **Collision-Safe Renaming**: Never overwrites existing files. Automatically resolves naming conflicts for distinct files using incremental suffixes (e.g., `invoice_1.pdf`).
- **Safe Dry-Run Mode (`--dry-run`)**: Preview all planned file movements, duplicate detections, and document classifications in the terminal before touching a single file.
- **Instant Rollback / Undo (`--undo`)**: Logs all transfer operations to `organizer_log.json`. Run with `--undo` to cleanly restore all files to their original locations and automatically prune empty generated folders (including nested subcategories).
- **Self-Protection & Re-nesting Prevention**:
  - Automatically skips system files (`desktop.ini`, `thumbs.db`, `.DS_Store`).
  - Ignores hidden files and in-progress downloads (`.crdownload`, `.part`, `.tmp`).
  - Prevents recursive re-nesting of already organized category, subcategory, and duplicate folders.
  - Protects the organizer script, configs, and repository root files from being moved.
- **Rich Terminal UI**: Automatically renders beautiful tables and status badges when `rich` is installed, falling back cleanly to universal ASCII in minimal terminal environments.
- **Packaged CLI**: Can be installed globally via pip to use anywhere as the `smart-organizer` terminal command.

---

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Ayushman2804/SMART-FILE-ORGANIZER.git
cd SMART-FILE-ORGANIZER
```

### 2. Install as a CLI Tool (Optional)
Install in editable mode to unlock the global `smart-organizer` command:
```bash
pip install -e .

# Or install with all optional visual & watcher packages:
pip install -e .[all]
```

Once installed, you can use `smart-organizer` directly from anywhere in your terminal!

---

## Quick Start & Usage Examples

### 1. Preview Organization (Dry Run)
Test how your directory will be organized without moving any files:
```bash
smart-organizer --path "C:/Users/YourName/Downloads" --dry-run
# or: python smart_file_organizer.py --path "C:/Users/YourName/Downloads" --dry-run
```

### 2. Organize with Smart Document Categorization
Organize files and automatically sort PDFs/documents into intelligent subcategories:
```bash
smart-organizer --path "C:/Users/YourName/Downloads" --smart-docs
```

### 3. Full Power: Smart Docs + Duplicate Isolation
Organize, classify documents, and segregate duplicate files in a single pass:
```bash
smart-organizer --path "C:/Users/YourName/Downloads" --smart-docs --dedup
```

### 4. Real-Time Background Folder Watcher
Keep your Downloads folder permanently organized in real-time as new files arrive:
```bash
smart-organizer --path "C:/Users/YourName/Downloads" --watch --smart-docs --dedup
```

### 5. Delete Exact Duplicates
Preview or delete byte-identical duplicate files:
```bash
# Preview duplicate deletions safely first:
smart-organizer --path "C:/Users/YourName/Downloads" --dedup --dedup-action delete --dry-run

# Execute:
smart-organizer --path "C:/Users/YourName/Downloads" --dedup --dedup-action delete
```

### 6. Roll Back (Undo)
Accidentally organized the wrong folder or want to revert? Restore everything with a single command:
```bash
smart-organizer --undo
```

---

## CLI Options Reference

| Flag | Short | Description |
| :--- | :---: | :--- |
| `--path <dir>` | `-p` | Path to the directory you want to organize (**required** for organize mode) |
| `--dry-run` | `-d` | Preview prospective file moves without applying changes |
| `--watch` | `-w` | Run as a real-time background watcher to auto-organize incoming files |
| `--smart-docs` | `-s` | Enable semantic document classification (Invoices, Resumes, Academic, Legal, Technical) |
| `--dedup` | | Enable SHA-256 byte-level duplicate detection |
| `--dedup-action` | | Action for duplicates: `move` (default, into `Duplicates/`) or `delete` |
| `--undo` | `-u` | Revert the last organization session and restore files |
| `--config <file>` | `-c` | Path to a custom category JSON configuration file |
| `--verbose` | `-v` | Display detailed logs including reasons for skipped files |
| `--help` | `-h` | Show CLI help message and flag references |

---

## Default File Categories (`config.json`)

| Category | Supported Extensions |
| :--- | :--- |
| **Images** | `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`, `.bmp`, `.tiff`, `.ico` |
| **Documents** | `.pdf`, `.docx`, `.doc`, `.txt`, `.pptx`, `.ppt`, `.odt`, `.rtf`, `.md` *(with `--smart-docs` subcategories)* |
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

A comprehensive unit test suite (14 tests) is included to verify collision handling, SHA-256 hashing, duplicate move/delete actions, smart document classification, dry-run simulation, re-nesting protection, undo rollbacks, and error fallbacks:

```bash
python test_organizer.py
```

---

## License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.
