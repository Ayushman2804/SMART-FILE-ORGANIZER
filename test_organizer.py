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
            "Documents": [".pdf", ".txt", ".docx", ".md"],
            "Videos": [".mp4"],
            "Music": [".mp3"],
            "Code": [".py", ".ts"],
            "Archives": [".zip", ".tar"],
            "Data": [".csv", ".json"],
            "Executables": [".exe"],
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

    def test_expanded_categories(self):
        code_file = self.test_dir / "script.py"
        zip_file = self.test_dir / "backup.zip"
        csv_file = self.test_dir / "data.csv"
        exe_file = self.test_dir / "setup.exe"

        code_file.write_text("print('hello')")
        zip_file.write_text("fake zip")
        csv_file.write_text("id,name")
        exe_file.write_text("fake exe")

        current_year = datetime.now().strftime("%Y")

        sfo.organize(
            target_dir=self.test_dir,
            config=self.config,
            dry_run=False,
            log_path=self.log_file,
        )

        self.assertTrue((self.test_dir / "Code" / current_year / "script.py").exists())
        self.assertTrue((self.test_dir / "Archives" / current_year / "backup.zip").exists())
        self.assertTrue((self.test_dir / "Data" / current_year / "data.csv").exists())
        self.assertTrue((self.test_dir / "Executables" / current_year / "setup.exe").exists())

    def test_collision_handling(self):
        dest_folder = self.test_dir / "Images" / "2024"
        dest_folder.mkdir(parents=True)
        (dest_folder / "pic.png").write_text("original")

        unique_path = sfo.get_unique_path(dest_folder, "pic.png")
        self.assertEqual(unique_path.name, "pic_1.png")

        (dest_folder / "pic_1.png").write_text("first collision")
        unique_path_2 = sfo.get_unique_path(dest_folder, "pic.png")
        self.assertEqual(unique_path_2.name, "pic_2.png")

    def test_file_hashing_sha256(self):
        f1 = self.test_dir / "file1.txt"
        f2 = self.test_dir / "file2.txt"
        f3 = self.test_dir / "file3.txt"

        f1.write_text("identical bytes")
        f2.write_text("identical bytes")
        f3.write_text("different bytes")

        h1 = sfo.compute_file_hash(f1)
        h2 = sfo.compute_file_hash(f2)
        h3 = sfo.compute_file_hash(f3)

        self.assertIsNotNone(h1)
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)

    def test_deduplication_move_action(self):
        f_orig = self.test_dir / "contract.pdf"
        f_dup = self.test_dir / "contract_copy.pdf"
        f_orig.write_text("exact contract agreement")
        f_dup.write_text("exact contract agreement")

        current_year = datetime.now().strftime("%Y")

        sfo.organize(
            target_dir=self.test_dir,
            config=self.config,
            dry_run=False,
            dedup=True,
            dedup_action="move",
            log_path=self.log_file,
        )

        orig_dest = self.test_dir / "Documents" / current_year / "contract.pdf"
        dup_dest = self.test_dir / "Duplicates" / current_year / "contract_copy.pdf"

        self.assertTrue(orig_dest.exists())
        self.assertTrue(dup_dest.exists())

        # Test Undo restores both
        sfo.undo(log_path=self.log_file)
        self.assertTrue((self.test_dir / "contract.pdf").exists())
        self.assertTrue((self.test_dir / "contract_copy.pdf").exists())
        self.assertFalse((self.test_dir / "Duplicates").exists())

    def test_deduplication_delete_action(self):
        f_orig = self.test_dir / "notes.txt"
        f_dup = self.test_dir / "notes_backup.txt"
        f_orig.write_text("my notes")
        f_dup.write_text("my notes")

        current_year = datetime.now().strftime("%Y")

        sfo.organize(
            target_dir=self.test_dir,
            config=self.config,
            dry_run=False,
            dedup=True,
            dedup_action="delete",
            log_path=self.log_file,
        )

        orig_dest = self.test_dir / "Documents" / current_year / "notes.txt"
        self.assertTrue(orig_dest.exists())
        self.assertFalse((self.test_dir / "notes_backup.txt").exists())
        self.assertFalse((self.test_dir / "Duplicates").exists())

    def test_smart_document_classification_logic(self):
        inv_file = self.test_dir / "bill.txt"
        inv_file.write_text("Tax Invoice #8234 Billed To Acme Corp Total Amount Due: $1500 GSTIN: 29A")

        res_file = self.test_dir / "profile.txt"
        res_file.write_text("Curriculum Vitae Education B.Tech Work Experience Technical Skills Projects")

        paper_file = self.test_dir / "deep_learning.txt"
        paper_file.write_text("Abstract: We propose a new transformer model. Introduction Methodology Literature Review References")

        legal_file = self.test_dir / "nda.txt"
        legal_file.write_text("Non-Disclosure Agreement Confidentiality Terms of Service Governing Law Indemnification")

        general_file = self.test_dir / "grocery_list.txt"
        general_file.write_text("Milk, eggs, apples, bread")

        cat_inv, conf_inv = sfo.classify_document(inv_file)
        cat_res, conf_res = sfo.classify_document(res_file)
        cat_paper, conf_paper = sfo.classify_document(paper_file)
        cat_legal, conf_legal = sfo.classify_document(legal_file)
        cat_gen, conf_gen = sfo.classify_document(general_file)

        self.assertEqual(cat_inv, "Invoices_Receipts")
        self.assertEqual(cat_res, "Resumes_Career")
        self.assertEqual(cat_paper, "Research_Academic")
        self.assertEqual(cat_legal, "Legal_Contracts")
        self.assertEqual(cat_gen, "General")

    def test_smart_docs_organization_and_undo(self):
        inv = self.test_dir / "aws_invoice.pdf"
        inv.write_text("Tax Invoice Receipt Total Amount Due $50")

        resume = self.test_dir / "ayushman_resume.pdf"
        resume.write_text("Curriculum Vitae Work Experience Technical Skills")

        current_year = datetime.now().strftime("%Y")

        sfo.organize(
            target_dir=self.test_dir,
            config=self.config,
            dry_run=False,
            smart_docs=True,
            log_path=self.log_file,
        )

        expected_inv = self.test_dir / "Documents" / "Invoices_Receipts" / current_year / "aws_invoice.pdf"
        expected_res = self.test_dir / "Documents" / "Resumes_Career" / current_year / "ayushman_resume.pdf"

        self.assertTrue(expected_inv.exists())
        self.assertTrue(expected_res.exists())

        # Test Undo restores files and prunes all nested subdirectories
        sfo.undo(log_path=self.log_file)

        self.assertTrue(inv.exists())
        self.assertTrue(resume.exists())
        self.assertFalse((self.test_dir / "Documents").exists())

    def test_protected_and_ignored_files(self):
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

        self.assertTrue(hidden.exists())
        self.assertTrue(sys_file.exists())
        self.assertTrue(crdownload.exists())

    def test_undo_and_empty_folder_pruning(self):
        doc = self.test_dir / "contract.txt"
        doc.write_text("contract text")
        current_year = datetime.now().strftime("%Y")

        sfo.organize(
            target_dir=self.test_dir,
            config=self.config,
            dry_run=False,
            log_path=self.log_file,
        )

        organized_path = self.test_dir / "Documents" / current_year / "contract.txt"
        self.assertTrue(organized_path.exists())

        sfo.undo(log_path=self.log_file)
        self.assertTrue(doc.exists())
        self.assertFalse((self.test_dir / "Documents").exists())

    def test_re_nesting_prevention(self):
        pic = self.test_dir / "vacation.jpg"
        pic.write_text("photo")
        current_year = datetime.now().strftime("%Y")

        sfo.organize(
            target_dir=self.test_dir,
            config=self.config,
            dry_run=False,
            log_path=self.log_file,
        )

        organized_path = self.test_dir / "Images" / current_year / "vacation.jpg"
        self.assertTrue(organized_path.exists())

        sfo.organize(
            target_dir=self.test_dir,
            config=self.config,
            dry_run=False,
            log_path=self.log_file,
        )

        self.assertTrue(organized_path.exists())
        self.assertFalse((self.test_dir / "Images" / current_year / "Images").exists())

    def test_corrupted_log_graceful_handling(self):
        bad_log = self.test_dir / "bad_log.json"
        bad_log.write_text("2026-03-21 11:04:00 - Not valid JSON!")

        logs = sfo.load_log(bad_log)
        self.assertEqual(logs, [])

    def test_corrupted_config_fallback(self):
        bad_config = self.test_dir / "bad_config.json"
        bad_config.write_text("{broken json")

        cfg = sfo.load_config(bad_config)
        self.assertIn("Images", cfg)
        self.assertIn(".jpg", cfg["Images"])


if __name__ == "__main__":
    unittest.main()
