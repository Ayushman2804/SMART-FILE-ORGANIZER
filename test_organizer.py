import unittest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime

import smart_file_organizer as sfo


class TestSmartFileOrganizer(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for tests
        self.test_dir = Path(tempfile.mkdtemp())
        self.log_file = self.test_dir / "test_log.json"
        self.config = {
            "Images": [".jpg", ".png"],
            "Documents": [".pdf", ".txt"],
            "Videos": [".mp4"],
            "Music": [".mp3"],
        }

    def tearDown(self):
        # Cleanup
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_dry_run_does_not_move_files(self):
        sample = self.test_dir / "photo.jpg"
        sample.write_text("dummy")

        sfo.organize(
            target_dir=self.test_dir,
            config=self.config,
            dry_run=True,
            log_path=self.log_file,
        )

        self.assertTrue(sample.exists())
        self.assertFalse((self.test_dir / "Images").exists())
        self.assertFalse(self.log_file.exists())

    def test_normal_categorization_and_year(self):
        img = self.test_dir / "photo.jpg"
        doc = self.test_dir / "report.pdf"
        other = self.test_dir / "archive.iso"
        img.write_text("image content")
        doc.write_text("doc content")
        other.write_text("other content")

        current_year = datetime.now().strftime("%Y")

        sfo.organize(
            target_dir=self.test_dir,
            config=self.config,
            dry_run=False,
            log_path=self.log_file,
        )

        expected_img = self.test_dir / "Images" / current_year / "photo.jpg"
        expected_doc = self.test_dir / "Documents" / current_year / "report.pdf"
        expected_other = self.test_dir / "Others" / current_year / "archive.iso"

        self.assertTrue(expected_img.exists())
        self.assertTrue(expected_doc.exists())
        self.assertTrue(expected_other.exists())
        self.assertTrue(self.log_file.exists())

    def test_collision_handling(self):
        dest_folder = self.test_dir / "Images" / "2024"
        dest_folder.mkdir(parents=True)
        (dest_folder / "pic.png").write_text("original")

        unique_path = sfo.get_unique_path(dest_folder, "pic.png")
        self.assertEqual(unique_path.name, "pic_1.png")

        (dest_folder / "pic_1.png").write_text("first collision")
        unique_path_2 = sfo.get_unique_path(dest_folder, "pic.png")
        self.assertEqual(unique_path_2.name, "pic_2.png")

    def test_protected_and_ignored_files(self):
        # Create ignored items
        hidden = self.test_dir / ".hidden_file.txt"
        hidden.write_text("hidden")
        sys_file = self.test_dir / "desktop.ini"
        sys_file.write_text("system")
        crdownload = self.test_dir / "large_file.crdownload"
        crdownload.write_text("downloading")

        sfo.organize(
            target_dir=self.test_dir,
            config=self.config,
            dry_run=False,
            log_path=self.log_file,
        )

        # None of the protected/ignored files should have moved
        self.assertTrue(hidden.exists())
        self.assertTrue(sys_file.exists())
        self.assertTrue(crdownload.exists())

    def test_undo_and_empty_folder_pruning(self):
        doc = self.test_dir / "contract.txt"
        doc.write_text("contract text")
        current_year = datetime.now().strftime("%Y")

        # Organize
        sfo.organize(
            target_dir=self.test_dir,
            config=self.config,
            dry_run=False,
            log_path=self.log_file,
        )

        organized_path = self.test_dir / "Documents" / current_year / "contract.txt"
        self.assertTrue(organized_path.exists())

        # Undo
        sfo.undo(log_path=self.log_file)

        # File should be restored to test_dir
        self.assertTrue(doc.exists())
        # Organized folder should be pruned
        self.assertFalse((self.test_dir / "Documents").exists())

    def test_re_nesting_prevention(self):
        # Test that running twice does not re-nest already organized subfolders
        pic = self.test_dir / "vacation.jpg"
        pic.write_text("photo")
        current_year = datetime.now().strftime("%Y")

        # 1st run
        sfo.organize(
            target_dir=self.test_dir,
            config=self.config,
            dry_run=False,
            log_path=self.log_file,
        )

        organized_path = self.test_dir / "Images" / current_year / "vacation.jpg"
        self.assertTrue(organized_path.exists())

        # 2nd run on same directory
        sfo.organize(
            target_dir=self.test_dir,
            config=self.config,
            dry_run=False,
            log_path=self.log_file,
        )

        # File should remain at Images/2026/vacation.jpg and NOT Images/2026/Images/2026/vacation.jpg
        self.assertTrue(organized_path.exists())
        self.assertFalse((self.test_dir / "Images" / current_year / "Images").exists())

    def test_corrupted_log_graceful_handling(self):
        # Write corrupted non-json string to log
        bad_log = self.test_dir / "bad_log.json"
        bad_log.write_text("2026-03-21 11:04:00 - Not valid JSON!")

        # Should return empty list and not crash
        logs = sfo.load_log(bad_log)
        self.assertEqual(logs, [])

    def test_corrupted_config_fallback(self):
        bad_config = self.test_dir / "bad_config.json"
        bad_config.write_text("{broken json")

        # Should fallback to default config and not crash
        cfg = sfo.load_config(bad_config)
        self.assertIn("Images", cfg)
        self.assertIn(".jpg", cfg["Images"])


if __name__ == "__main__":
    unittest.main()
