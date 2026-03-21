import os
import shutil
from datetime import datetime

# File categories
FILE_TYPES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif"],
    "Documents": [".pdf", ".docx", ".txt", ".pptx"],
    "Videos": [".mp4", ".mkv", ".avi"],
    "Music": [".mp3", ".wav"]
}

LOG_FILE = "organizer_log.txt"


def log_action(message):
    with open(LOG_FILE, "a") as log:
        log.write(f"{datetime.now()} - {message}\n")


def create_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)
        log_action(f"Created folder: {path}")


def get_unique_filename(folder, filename):
    base, ext = os.path.splitext(filename)
    counter = 1

    new_name = filename
    while os.path.exists(os.path.join(folder, new_name)):
        new_name = f"{base}_{counter}{ext}"
        counter += 1

    return new_name


def move_file(file_path, dest_folder):
    filename = os.path.basename(file_path)
    unique_name = get_unique_filename(dest_folder, filename)

    dest_path = os.path.join(dest_folder, unique_name)
    shutil.move(file_path, dest_path)

    print(f"Moved: {filename} → {dest_folder}")
    log_action(f"Moved {filename} to {dest_folder}")


def organize_files(source_folder):
    if not os.path.exists(source_folder):
        print("❌ Folder does not exist!")
        return

    print(f"\n📂 Organizing files in: {source_folder}\n")

    for file in os.listdir(source_folder):
        file_path = os.path.join(source_folder, file)

        if os.path.isfile(file_path):
            moved = False

            for folder, extensions in FILE_TYPES.items():
                if any(file.lower().endswith(ext) for ext in extensions):
                    dest_folder = os.path.join(source_folder, folder)
                    create_folder(dest_folder)
                    move_file(file_path, dest_folder)
                    moved = True
                    break

            if not moved:
                other_folder = os.path.join(source_folder, "Others")
                create_folder(other_folder)
                move_file(file_path, other_folder)

    print("\n✅ Organization Complete!")
    log_action("Completed organization process")


def main():
    print("===== Smart File Organizer =====")
    path = input("Enter folder path to organize: ").strip()

    organize_files(path)


if __name__ == "__main__":
    main()