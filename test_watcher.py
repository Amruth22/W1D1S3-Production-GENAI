# tests/test_worker.py
import unittest
import tempfile
import os
import json
from pathlib import Path

import utils
import worker
from utils import SummaryResult


class TestWorkerFunctions(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.orig_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)
        # create runtime dirs
        utils.ensure_runtime_dirs()

    def tearDown(self):
        os.chdir(self.orig_cwd)
        self.tmpdir.cleanup()

    def test_list_queue_depth_and_claim(self):
        # create two .txt files
        inp = Path("input")
        (inp / "a.txt").write_text("a")
        (inp / "b.txt").write_text("b")
        depth = utils.list_queue_depth()
        self.assertEqual(depth, 2)

        claimed = worker.claim_next_file()
        self.assertIsNotNone(claimed)
        # should have been renamed to .processing
        self.assertTrue(str(claimed).endswith(".processing"))
        # cleanup
        claimed.unlink(missing_ok=True)

    def test_process_file_creates_output_and_logs(self):
        inp = Path("input")
        file_path = inp / "meeting.txt"
        sample = "John: Hi\nAlice: Hello\nJohn: I'll follow up tomorrow."
        file_path.write_text(sample, encoding="utf-8")

        # claim (rename)
        proc = worker.claim_next_file()
        self.assertIsNotNone(proc)

        # monkeypatch worker.summarize_meeting to be deterministic
        def fake_summarize(text):
            return SummaryResult(
                summary="Fake summary",
                attendees=["John", "Alice"],
                action_items=["Task A", "Task B", "Task C"]
            )

        worker.summarize_meeting = fake_summarize

        # process file
        worker.process_file(proc)

        # check output json written
        out_path = Path("output") / (proc.stem + ".json")
        self.assertTrue(out_path.exists())
        data = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(data["summary"], "Fake summary")

        # check metrics log
        log_path = Path("logs") / "metrics.csv"
        self.assertTrue(log_path.exists())
        content = log_path.read_text(encoding="utf-8")
        self.assertIn("job_id,status,duration_sec,error", content)

        # ensure the processing file was removed
        self.assertFalse(proc.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
