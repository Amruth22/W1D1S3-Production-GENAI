import unittest
import tempfile
import os
import json
from pathlib import Path

import utils
import worker
from utils import SummaryResult


class TestCorePipeline(unittest.TestCase):
    def setUp(self):
        # Run in an isolated temp directory
        self.tmpdir = tempfile.TemporaryDirectory()
        self.orig_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)
        utils.ensure_runtime_dirs()

    def tearDown(self):
        os.chdir(self.orig_cwd)
        self.tmpdir.cleanup()

    def test_01_worker_pipeline_can_start(self):
        # Worker "startup" essentials without running the infinite loop
        self.assertTrue(Path("input").exists())
        self.assertTrue(Path("output").exists())
        self.assertTrue(Path("logs").exists())
        # No files yet, claiming should return None (no crash)
        self.assertEqual(utils.list_queue_depth(), 0)
        self.assertIsNone(worker.claim_next_file())

    def test_02_llm_is_working_or_skip(self):
        # Real LLM test runs only if GEMINI_API_KEY is set; otherwise skip
        if not os.environ.get("GEMINI_API_KEY"):
            self.skipTest("GEMINI_API_KEY not set - skipping real LLM test")
        transcript = "John: Project update. Alice: Frontend ready."
        result = utils.summarize_meeting(transcript)
        self.assertIsInstance(result, SummaryResult)
        self.assertTrue(result.summary)
        self.assertEqual(len(result.action_items), 3)

    def test_03_upload_file_and_processing_starts(self):
        # Upload a .txt and verify it's claimed (renamed to .processing)
        inp = Path("input")
        (inp / "meeting.txt").write_text("John: Hi\nAlice: Hello\n", encoding="utf-8")
        claimed = worker.claim_next_file()
        self.assertIsNotNone(claimed)
        self.assertTrue(claimed.suffix == ".processing")

    def test_04_output_json_is_created(self):
        # Process a file and verify output JSON exists with required fields
        inp = Path("input")
        (inp / "meeting.txt").write_text(
            "John: Hi\nAlice: Hello\nI will send the report tomorrow.",
            encoding="utf-8",
        )
        proc = worker.claim_next_file()
        self.assertIsNotNone(proc)

        # Make deterministic by monkeypatching summarize_meeting
        def fake_summarize(_text):
            return SummaryResult(
                summary="Fake summary",
                attendees=["John", "Alice"],
                action_items=["Task A", "Task B", "Task C"],
            )

        original = worker.summarize_meeting
        worker.summarize_meeting = fake_summarize
        try:
            worker.process_file(proc)
        finally:
            worker.summarize_meeting = original

        out_path = Path("output") / (proc.stem + ".json")
        self.assertTrue(out_path.exists())
        data = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertIn("job_id", data)
        self.assertIn("summary", data)
        self.assertIn("attendees", data)
        self.assertIn("action_items", data)
        self.assertEqual(len(data["action_items"]), 3)

    def test_05_logs_csv_is_present(self):
        # Process another file and verify logs/metrics.csv exists and contains a header
        inp = Path("input")
        (inp / "meeting2.txt").write_text(
            "John: Update\nAlice: OK\nWe need to schedule a meeting.",
            encoding="utf-8",
        )
        proc = worker.claim_next_file()
        self.assertIsNotNone(proc)

        # Deterministic result again
        def fake_summarize(_text):
            return SummaryResult(
                summary="Another fake",
                attendees=["John", "Alice"],
                action_items=["Task 1", "Task 2", "Task 3"],
            )

        original = worker.summarize_meeting
        worker.summarize_meeting = fake_summarize
        try:
            worker.process_file(proc)
        finally:
            worker.summarize_meeting = original

        log_path = Path("logs") / "metrics.csv"
        self.assertTrue(log_path.exists())
        content = log_path.read_text(encoding="utf-8")
        self.assertIn("job_id,status,duration_sec,error", content)
