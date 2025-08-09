# tests/test_utils.py
import unittest
import tempfile
import os
import json
from pathlib import Path

import utils
from utils import SummaryResult


class TestUtilsFunctions(unittest.TestCase):
    def setUp(self):
        # run tests in a temp dir to avoid touching real input/output/logs
        self.tmpdir = tempfile.TemporaryDirectory()
        self.orig_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        self.tmpdir.cleanup()

    def test_parse_transcript_json_obj_valid(self):
        obj = {
            "summary": "Team meeting about project status",
            "attendees": ["John", "Alice", "Bob"],
            "action_items": ["Finish frontend", "Deploy backend", "Prepare tests"]
        }
        result = utils.parse_transcript_json_obj(obj)
        self.assertEqual(result.summary, "Team meeting about project status")
        self.assertEqual(result.attendees, ["John", "Alice", "Bob"])
        self.assertEqual(len(result.action_items), 3)
        self.assertEqual(result.action_items[0], "Finish frontend")

    def test_parse_transcript_json_obj_missing_fields(self):
        obj = {"summary": "Brief meeting"}
        result = utils.parse_transcript_json_obj(obj)
        self.assertEqual(result.summary, "Brief meeting")
        self.assertEqual(result.attendees, ["Meeting participants"])
        self.assertEqual(len(result.action_items), 3)  # padded

    def test_parse_transcript_json_obj_too_many_items(self):
        obj = {
            "summary": "Long meeting",
            "attendees": ["John", "Alice"],
            "action_items": ["Task 1", "Task 2", "Task 3", "Task 4"]
        }
        result = utils.parse_transcript_json_obj(obj)
        self.assertEqual(len(result.action_items), 3)
        self.assertEqual(result.action_items, ["Task 1", "Task 2", "Task 3"])

    def test_offline_summarizer_with_speakers(self):
        transcript = """John: Good morning everyone, let's start the meeting.
Alice: I've completed the frontend work and will deploy tomorrow.
Bob: The backend API is ready for testing.
John: Great! Alice, please send the deployment notes to Bob."""
        result = utils._offline_summarizer(transcript)
        # attendees are collected into a set and returned as a list (order not guaranteed)
        self.assertIn("John", result.attendees)
        self.assertIn("Alice", result.attendees)
        self.assertIn("Bob", result.attendees)
        self.assertEqual(len(result.action_items), 3)
        self.assertTrue(len(result.summary) > 0)

    def test_offline_summarizer_narrative_style(self):
        transcript = """The meeting started with Alice explaining the project status.
Bob mentioned that the database migration is complete.
Carol asked about the testing timeline.
Everyone agreed to meet again next week."""
        result = utils._offline_summarizer(transcript)
        self.assertIn("Alice", result.attendees)
        self.assertIn("Bob", result.attendees)
        self.assertIn("Carol", result.attendees)

    def test_offline_summarizer_no_speakers(self):
        transcript = """Meeting notes about project progress.
The team discussed various implementation options.
Several decisions were made regarding the timeline."""
        result = utils._offline_summarizer(transcript)
        self.assertEqual(result.attendees, ["Meeting participants"])
        self.assertEqual(len(result.action_items), 3)

    def test_extract_json_with_regex_complete(self):
        text = '''Here's the analysis:
{"summary": "Project meeting", "attendees": ["John", "Alice"], "action_items": ["Task 1", "Task 2", "Task 3"]}
That's the result.'''
        result = utils._extract_json_with_regex(text)
        self.assertIsNotNone(result)
        self.assertEqual(result["summary"], "Project meeting")
        self.assertEqual(len(result["attendees"]), 2)
        self.assertEqual(len(result["action_items"]), 3)

    def test_extract_json_with_regex_partial(self):
        text = '''Here is a partial JSON: {"summary": "Team standup meeting", "attendees": ["John", "Alice", "Bob"], "action_items": ["Review code", "Update docs", "Test features"]}'''
        result = utils._extract_json_with_regex(text)
        self.assertIsNotNone(result)
        self.assertEqual(result["summary"], "Team standup meeting")
        self.assertEqual(len(result["attendees"]), 3)

    def test_extract_json_with_regex_no_match(self):
        text = "This is just plain text with no JSON structure."
        result = utils._extract_json_with_regex(text)
        self.assertIsNone(result)

    def test_summarize_meeting_empty_input(self):
        with self.assertRaises(ValueError):
            utils.summarize_meeting("")
        with self.assertRaises(ValueError):
            utils.summarize_meeting("   \n\t   ")

    def test_transcript_with_timestamps_behaviour(self):
        # NOTE: current offline summarizer expects the name at the start of the line.
        # If a timestamp precedes the speaker (e.g., "[10:30] John: ...") the current
        # implementation will not extract the attendee and will fall back.
        transcript = """[10:30] John: Good morning everyone
[10:31] Alice: Hello, let's start with updates
[10:32] Bob: I'll go first with the backend status"""
        result = utils._offline_summarizer(transcript)
        self.assertIn("John", result.attendees)
        self.assertIn("Alice", result.attendees)
        self.assertIn("Bob", result.attendees)

    def test_transcript_with_unicode_names(self):
        # current regex uses ASCII ranges; accented or non-latin names may not be captured
        transcript = """José: Hola everyone, let's begin.
François: Bonjour! I have the updates ready.
李明: 我们开始吧 (Let's start)."""
        result = utils._offline_summarizer(transcript)
        # ensure function does not crash and returns 3 action items padded if needed
        self.assertEqual(len(result.action_items), 3)
        self.assertIsInstance(result.summary, str)

    def test_action_items_extraction(self):
        transcript = """John: I will prepare the presentation by Friday.
Alice: We need to schedule a client meeting next week.
Bob: I should review the code before deployment.
Carol: The team must complete testing by Thursday."""
        result = utils._offline_summarizer(transcript)
        action_text = " ".join(result.action_items).lower()
        self.assertTrue(any(word in action_text for word in ["prepare", "schedule", "review", "complete"]))

    def test_single_speaker_transcript(self):
        transcript = """John: I'll start by reviewing the project status.
John: The frontend is 90% complete and ready for testing.
John: Next week I'll focus on the backend integration.
John: That concludes my update for today."""
        result = utils._offline_summarizer(transcript)
        self.assertEqual(result.attendees, ["John"])
        self.assertEqual(len(result.action_items), 3)

    def test_llm_unavailable_fallback(self):
        # Simulate LLM not available by forcing genai/types to None
        orig_genai = getattr(utils, "genai", None)
        orig_types = getattr(utils, "types", None)
        utils.genai = None
        utils.types = None
        try:
            transcript = "John: Let's discuss the project. Alice: I agree."
            result = utils.summarize_meeting(transcript)
            self.assertIsInstance(result, SummaryResult)
            # can be real attendees or the fallback "Meeting participants"
            self.assertTrue(len(result.action_items) == 3)
        finally:
            utils.genai = orig_genai
            utils.types = orig_types

    def test_action_items_padding(self):
        transcript = "John: I will do one task."
        result = utils._offline_summarizer(transcript)
        self.assertEqual(len(result.action_items), 3)
        # ensure fallback items are produced
        self.assertTrue(any("follow up" in item.lower() or "review meeting notes" in item.lower()
                            for item in result.action_items))

    def test_attendees_deduplication(self):
        transcript = """John: First comment.
John: Second comment.
Alice: My comment.
John: Third comment."""
        result = utils._offline_summarizer(transcript)
        self.assertEqual(result.attendees.count("John"), 1)
        self.assertIn("Alice", result.attendees)

    def test_summary_generation_quality(self):
        # put narrative lines first so offline summarizer will pick them up as summary
        transcript = """We are here to discuss the Q4 project timeline.
The development phase is on track for completion by December.
Testing will begin in November and run for three weeks.
John: some speaker line that will be ignored."""
        result = utils._offline_summarizer(transcript)
        summary_lower = result.summary.lower()
        self.assertTrue(any(word in summary_lower for word in ["project", "timeline", "development", "testing"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
