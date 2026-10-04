# Smart File Organizer (Python)

A reliable, cross-platform Python CLI automation utility that systematically categorizes and declutters messy directories (such as `Downloads` or `Desktop`) into organized folders based on file category and year of last modification.

Built purely using the **Python Standard Library** (`pathlib`, `shutil`, `argparse`, `json`, `datetime`) — zero external dependencies required.

---

## Key Features

- **Category & Temporal Sorting**: Automatically matches file extensions against configurable rules and sorts them into `<Category>/<Year>/` structures. Unmatched files are safely routed to `Others/<Year>/`.
- **Collision-Safe Renaming**: Never overwrites existing files. Automatically resolves naming conflicts with incremental suffixes (e.g., `invoice_1.pdf`).
- **Safe Dry-Run Mode (`--dry-run`)**: Preview all planned file movements in the terminal before touching a single file.
- **Instant Rollback / Undo (`--undo`)**: Logs all transfer operations to `organizer_log.json`. Run with `--undo` to cleanly restore all files to their original locations and automatically prune empty generated folders.
- **Self-Protection & Re-nesting Prevention**:
  - Automatically skips system files (`desktop.ini`, `thumbs.db`, `.DS_Store`).
  - Ignores hidden files and in-progress downloads (`.crdownload`, `.part`, `.tmp`).
  - Prevents recursive re-nesting of already organized category folders.
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

### 3. Execute Organization
Organize the target folder:
```bash
python smart_file_organizer.py --path "C:/Users/YourName/Downloads"
```

### 4. Roll Back (Undo)
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
| `--undo` | `-u` | Revert the last organization session and restore files |
| `--config <file>` | `-c` | Path to a custom category JSON configuration file |
| `--verbose` | `-v` | Display detailed logs including reasons for skipped files |
| `--help` | `-h` | Show CLI help message and flag references |

---

## Configuration (`config.json`)

You can customize file categories and mapped extensions in `config.json`:

```json
{
  "Images": [".jpg", ".jpeg", ".png", ".gif"],
  "Documents": [".pdf", ".docx", ".txt", ".pptx"],
  "Videos": [".mp4", ".mkv", ".avi"],
  "Music": [".mp3", ".wav"]
}
```

Any file whose extension is not in `config.json` is safely placed into the `Others/<Year>/` directory.

---

## Running Automated Tests

A comprehensive unit test suite is included to verify collision handling, dry-run simulation, re-nesting protection, undo rollbacks, and error fallbacks:

```bash
python test_organizer.py
```

---

## Technologies Used

- **Language**: Python 3.8+
- **Modules**: `pathlib`, `shutil`, `argparse`, `json`, `datetime`, `unittest`
