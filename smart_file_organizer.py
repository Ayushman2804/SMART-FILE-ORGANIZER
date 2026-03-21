import os
import shutil
import argparse
import json
from datetime import datetime

LOG_FILE = "organizer_log.json"


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)


def save_log(data):
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=4)


def load_log():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        return json.load(f)


def get_unique_filename(folder, filename):
    base, ext = os.path.splitext(filename)
    counter = 1
    new_name = filename

    while os.path.exists(os.path.join(folder, new_name)):
        new_name = f"{base}_{counter}{ext}"
        counter += 1

    return new_name


def move_file(src, dest, dry_run, log_data):
    filename = os.path.basename(src)
    unique_name = get_unique_filename(dest, filename)
    dest_path = os.path.join(dest, unique_name)

    if dry_run:
        print(f"[DRY RUN] {filename} → {dest}")
    else:
        shutil.move(src, dest_path)
        print(f"Moved: {filename} → {dest}")

    log_data.append({
        "source": src,
        "destination": dest_path
    })


def organize(path, config, dry_run):
    log_data = []

    for file in os.listdir(path):
        file_path = os.path.join(path, file)

        if os.path.isfile(file_path):
            moved = False

            for category, extensions in config.items():
                if any(file.lower().endswith(ext) for ext in extensions):
                    year = datetime.fromtimestamp(
                        os.path.getmtime(file_path)
                    ).strftime("%Y")

                    dest_folder = os.path.join(path, category, year)
                    os.makedirs(dest_folder, exist_ok=True)

                    move_file(file_path, dest_folder, dry_run, log_data)
                    moved = True
                    break

            if not moved:
                other = os.path.join(path, "Others")
                os.makedirs(other, exist_ok=True)
                move_file(file_path, other, dry_run, log_data)

    if not dry_run:
        save_log(log_data)

    print("\n✅ Done!")


def undo():
    log_data = load_log()

    if not log_data:
        print("Nothing to undo!")
        return

    for entry in reversed(log_data):
        src = entry["destination"]
        dest = os.path.dirname(entry["source"])

        if os.path.exists(src):
            shutil.move(src, dest)
            print(f"Restored: {os.path.basename(src)}")

    print("\n↩ Undo completed!")


def main():
    parser = argparse.ArgumentParser(description="Smart File Organizer")
    parser.add_argument("--path", help="Folder path to organize")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--undo", action="store_true", help="Undo last operation")

    args = parser.parse_args()

    if args.undo:
        undo()
        return

    if not args.path:
        print("Please provide --path")
        return

    config = load_config()
    organize(args.path, config, args.dry_run)


if __name__ == "__main__":
    main()
