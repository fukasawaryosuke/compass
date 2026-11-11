from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from compass.runtime import Run, VaultLockedError


class RunTests(unittest.TestCase):
    def test_writes_minimal_record_and_releases_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with Run("ingest", runtime_root=root) as run:
                run.add_summary(created=2, skipped=1)
                run.add_details(targets=["https://example.com"], validation="passed")

            record_path = next((root / "runs").glob("*.json"))
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(record["operation"], "ingest")
            self.assertEqual(record["status"], "succeeded")
            self.assertEqual(record["summary"], {"created": 2, "skipped": 1})
            self.assertEqual(record["targets"], ["https://example.com"])
            self.assertEqual(record["validation"], "passed")
            self.assertFalse((root / "locks" / "vault.lock").exists())

    def test_refuses_a_second_writer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with Run("ingest", runtime_root=root):
                with self.assertRaises(VaultLockedError):
                    with Run("init", runtime_root=root):
                        pass
