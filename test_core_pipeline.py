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

    def _mock_process_with_result(self, claimed_file, mock_result):
        """Helper method to mock process_file with a specific result."""
        original = worker.summarize_meeting
        worker.summarize_meeting = lambda _: mock_result
        try:
            worker.process_file(claimed_file)
        finally:
            worker.summarize_meeting = original

    def test_01_worker_pipeline_startup(self):
        """Test that worker pipeline can start properly with all required directories."""
        print("\n=== TEST 01: Worker Pipeline Startup ===")
        
        # Verify all runtime directories are created
        self.assertTrue(Path("input").exists(), "Input directory should exist")
        self.assertTrue(Path("output").exists(), "Output directory should exist") 
        self.assertTrue(Path("logs").exists(), "Logs directory should exist")
        
        # Verify directories are empty initially
        self.assertEqual(len(list(Path("input").glob("*"))), 0, "Input directory should be empty")
        self.assertEqual(len(list(Path("output").glob("*"))), 0, "Output directory should be empty")
        self.assertEqual(len(list(Path("logs").glob("*"))), 0, "Logs directory should be empty")
        
        # Verify queue depth is 0 when no files present
        self.assertEqual(utils.list_queue_depth(), 0, "Queue depth should be 0 with no files")
        
        # Verify claiming returns None when no files available
        self.assertIsNone(worker.claim_next_file(), "Should return None when no files to claim")
        
        print("[PASS] All directories created successfully")
        print("[PASS] Queue depth calculation working")
        print("[PASS] File claiming mechanism ready")

    def test_02_llm_integration_with_api_key(self):
        """Test LLM integration with actual API key if available."""
        print("\n=== TEST 02: LLM Integration ===")
        
        # Check if API key is available
        if not os.environ.get("GEMINI_API_KEY"):
            print("⚠ GEMINI_API_KEY not set - skipping real LLM test")
            self.skipTest("GEMINI_API_KEY not set - skipping real LLM test")
        
        # Test with a simple meeting transcript
        test_transcript = """
        John: Good morning everyone, let's start our daily standup.
        Alice: I completed the frontend dashboard yesterday. Today I'll work on the user authentication.
        Bob: Backend API is 90% complete. I need to finish the error handling by end of day.
        John: Great progress team. Alice, can you review Bob's API docs when ready?
        Alice: Sure, I'll review them this afternoon.
        """
        
        print("[LLM] Testing LLM with real API call...")
        result = utils.summarize_meeting(test_transcript)
        
        # Verify result structure
        self.assertIsInstance(result, SummaryResult, "Should return SummaryResult object")
        self.assertTrue(result.summary, "Summary should not be empty")
        self.assertIsInstance(result.attendees, list, "Attendees should be a list")
        self.assertEqual(len(result.action_items), 3, "Should have exactly 3 action items")
        
        # Verify content quality
        self.assertGreater(len(result.summary), 10, "Summary should be meaningful")
        self.assertGreater(len(result.attendees), 0, "Should identify attendees")
        
        print(f"[PASS] LLM Response - Summary: {result.summary[:60]}...")
        print(f"[PASS] LLM Response - Attendees: {result.attendees}")
        print(f"[PASS] LLM Response - Action Items: {len(result.action_items)} items")

    def test_03_real_file_processing_meeting_transcript(self):
        """Test processing actual Meeting Transcript.txt from Test_Files folder."""
        print("\n=== TEST 03: Real File Processing ===")
        
        # Locate Test_Files directory
        test_files_dir = Path(self.orig_cwd) / "Test_Files"
        meeting_transcript = test_files_dir / "Meeting Transcript.txt"
        
        if not meeting_transcript.exists():
            print("⚠ Meeting Transcript.txt not found in Test_Files - skipping test")
            self.skipTest("Meeting Transcript.txt not found in Test_Files directory")
        
        # Copy the real meeting transcript to input
        input_file = Path("input") / "meeting_transcript.txt"
        input_file.write_text(meeting_transcript.read_text(encoding="utf-8"), encoding="utf-8")
        
        print(f"[FILE] Processing real file: {meeting_transcript.name}")
        print(f"[INFO] File size: {meeting_transcript.stat().st_size} bytes")
        
        # Claim and process the file
        claimed_file = worker.claim_next_file()
        self.assertIsNotNone(claimed_file, "Should successfully claim the file")
        self.assertTrue(claimed_file.suffix == ".processing", "File should have .processing extension")
        
        # Process with real LLM or mock depending on API key availability
        if os.environ.get("GEMINI_API_KEY"):
            print("[LLM] Using real LLM for processing...")
            worker.process_file(claimed_file)
        else:
            print("[MOCK] Using mock LLM for testing...")
            mock_result = SummaryResult(
                summary="Q3 strategic planning session covering performance review and future objectives",
                attendees=["Sarah Chen", "David Thompson", "Lisa Wang", "Michael Rodriguez", "Jennifer Park"],
                action_items=["Review Q3 budget allocation", "Finalize product roadmap", "Prepare board presentation"]
            )
            self._mock_process_with_result(claimed_file, mock_result)
        
        # Verify processing completed
        self.assertFalse(claimed_file.exists(), "Processing file should be removed after completion")
        
        print("[PASS] File successfully processed and cleaned up")

    def test_04_input_folder_creation_and_file_detection(self):
        """Test input folder is created and can detect input files."""
        print("\n=== TEST 04: Input Folder & File Detection ===")
        
        # Verify input folder exists
        input_dir = Path("input")
        self.assertTrue(input_dir.exists(), "Input directory should exist")
        self.assertTrue(input_dir.is_dir(), "Input should be a directory")
        
        # Test with no files initially
        initial_depth = utils.list_queue_depth()
        self.assertEqual(initial_depth, 0, "Queue depth should be 0 initially")
        print(f"[PASS] Initial queue depth: {initial_depth}")
        
        # Add multiple test files
        test_files = [
            ("meeting1.txt", "John: Project update.\nAlice: Frontend ready."),
            ("standup.txt", "Daily standup meeting.\nBob: Backend complete."),
            ("review.txt", "Code review session.\nCarol: Testing finished.")
        ]
        
        for filename, content in test_files:
            test_file = input_dir / filename
            test_file.write_text(content, encoding="utf-8")
            print(f"[CREATE] Created: {filename}")
        
        # Verify files are detected
        final_depth = utils.list_queue_depth()
        self.assertEqual(final_depth, len(test_files), f"Should detect {len(test_files)} files")
        print(f"[PASS] Final queue depth: {final_depth}")
        
        # Test file claiming
        claimed_files = []
        for i in range(len(test_files)):
            claimed = worker.claim_next_file()
            self.assertIsNotNone(claimed, f"Should claim file {i+1}")
            claimed_files.append(claimed)
            print(f"[CLAIM] Claimed: {claimed.name}")
        
        # Verify no more files to claim
        self.assertIsNone(worker.claim_next_file(), "Should be no more files to claim")
        
        # Cleanup claimed files
        for claimed in claimed_files:
            claimed.unlink(missing_ok=True)
        
        print("[PASS] File detection and claiming working correctly")

    def test_05_output_folder_with_summary_json(self):
        """Test output folder creation and JSON summary generation."""
        print("\n=== TEST 05: Output Folder & Summary JSON ===")
        
        # Verify output folder exists
        output_dir = Path("output")
        self.assertTrue(output_dir.exists(), "Output directory should exist")
        self.assertTrue(output_dir.is_dir(), "Output should be a directory")
        
        # Create test input file
        input_file = Path("input") / "test_meeting.txt"
        input_file.write_text(
            "Sarah: Welcome to our team meeting.\n"
            "Mike: I completed the database migration.\n"
            "Lisa: Frontend testing is done, found 2 minor issues.\n"
            "Sarah: Great work everyone. Mike, please document the migration steps.",
            encoding="utf-8"
        )
        
        # Claim and process file
        claimed = worker.claim_next_file()
        self.assertIsNotNone(claimed, "Should claim the test file")
        
        # Use deterministic mock for consistent testing
        mock_result = SummaryResult(
            summary="Team meeting discussing database migration and frontend testing completion",
            attendees=["Sarah", "Mike", "Lisa"],
            action_items=[
                "Document database migration steps",
                "Fix 2 minor frontend issues",
                "Schedule follow-up review"
            ]
        )
        self._mock_process_with_result(claimed, mock_result)
        
        # Verify JSON output exists
        expected_output = output_dir / "test_meeting.json"
        self.assertTrue(expected_output.exists(), "JSON output file should exist")
        
        # Verify JSON content
        with open(expected_output, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        required_fields = ["job_id", "summary", "attendees", "action_items"]
        for field in required_fields:
            self.assertIn(field, data, f"JSON should contain '{field}' field")
        
        # Verify data types and constraints
        self.assertIsInstance(data["job_id"], str, "job_id should be string")
        self.assertTrue(data["job_id"].startswith("job-"), "job_id should have 'job-' prefix")
        self.assertIsInstance(data["summary"], str, "summary should be string")
        self.assertIsInstance(data["attendees"], list, "attendees should be list")
        self.assertIsInstance(data["action_items"], list, "action_items should be list")
        self.assertEqual(len(data["action_items"]), 3, "Should have exactly 3 action items")
        
        print(f"[PASS] JSON created: {expected_output.name}")
        print(f"[PASS] Job ID: {data['job_id']}")
        print(f"[PASS] Summary: {data['summary'][:50]}...")
        print(f"[PASS] Attendees: {data['attendees']}")
        print(f"[PASS] Action Items: {len(data['action_items'])} items")
        
        # Verify JSON structure is valid
        json_str = json.dumps(data, indent=2)
        self.assertGreater(len(json_str), 100, "JSON should be substantial")

    def test_06_csv_log_presence_and_structure(self):
        """Test CSV log file creation and proper structure."""
        print("\n=== TEST 06: CSV Log Presence & Structure ===")
        
        # Verify logs folder exists
        logs_dir = Path("logs")
        self.assertTrue(logs_dir.exists(), "Logs directory should exist")
        
        # Initially no metrics file
        metrics_file = logs_dir / "metrics.csv"
        if metrics_file.exists():
            metrics_file.unlink()  # Clean slate for testing
        
        # Create and process a test file to generate metrics
        input_file = Path("input") / "metrics_test.txt"
        input_file.write_text(
            "Alex: Let's discuss the quarterly results.\n"
            "Jordan: Revenue is up 15% this quarter.\n"
            "Taylor: Customer satisfaction scores improved.",
            encoding="utf-8"
        )
        
        claimed = worker.claim_next_file()
        self.assertIsNotNone(claimed, "Should claim the metrics test file")
        
        # Mock processing to ensure consistent metrics
        mock_result = SummaryResult(
            summary="Quarterly results discussion with positive revenue and satisfaction trends",
            attendees=["Alex", "Jordan", "Taylor"], 
            action_items=[
                "Prepare detailed revenue report",
                "Analyze customer satisfaction data",
                "Plan next quarter strategy"
            ]
        )
        self._mock_process_with_result(claimed, mock_result)
        
        # Verify CSV file was created
        self.assertTrue(metrics_file.exists(), "Metrics CSV file should be created")
        
        # Read and verify CSV content
        csv_content = metrics_file.read_text(encoding="utf-8")
        lines = csv_content.strip().split('\n')
        
        # Verify header
        self.assertGreater(len(lines), 0, "CSV should have content")
        header = lines[0]
        expected_header = "job_id,status,duration_sec,error"
        self.assertEqual(header, expected_header, "CSV should have correct header")
        
        # Verify data row exists
        self.assertGreater(len(lines), 1, "CSV should have data rows")
        data_row = lines[1].split(',')
        self.assertEqual(len(data_row), 4, "Data row should have 4 columns")
        
        # Verify data row content
        job_id, status, duration, error = data_row
        self.assertTrue(job_id.startswith("job-"), "Job ID should start with 'job-'")
        self.assertIn(status, ["completed", "failed"], "Status should be completed or failed")
        
        # Duration should be a valid float
        try:
            duration_float = float(duration)
            self.assertGreaterEqual(duration_float, 0, "Duration should be non-negative")
        except ValueError:
            self.fail("Duration should be a valid number")
        
        print(f"[PASS] CSV file created: {metrics_file}")
        print(f"[PASS] Header: {header}")
        print(f"[PASS] Data row: job_id={job_id}, status={status}, duration={duration}s")
        print(f"[PASS] Total lines: {len(lines)} (1 header + {len(lines)-1} data)")
        
        # Test multiple entries by processing another file
        input_file2 = Path("input") / "second_test.txt"
        input_file2.write_text("Quick meeting.\nJohn: Status update.", encoding="utf-8")
        
        claimed2 = worker.claim_next_file()
        if claimed2:
            self._mock_process_with_result(claimed2, mock_result)
            
            # Verify multiple entries
            updated_content = metrics_file.read_text(encoding="utf-8")
            updated_lines = updated_content.strip().split('\n')
            self.assertGreater(len(updated_lines), 2, "Should have multiple data entries")
            print(f"[PASS] Multiple entries: {len(updated_lines)-1} data rows")


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)