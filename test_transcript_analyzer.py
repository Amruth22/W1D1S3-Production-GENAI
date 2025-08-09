import unittest
import json
import os
from unittest.mock import patch, MagicMock
from utils import (
    SummaryResult,
    parse_transcript_json_obj,
    summarize_meeting,
    _offline_summarizer,
    _extract_json_with_regex,
)


class TestTranscriptAnalyzer(unittest.TestCase):
    """Unit tests for Meeting Transcript Analyzer"""

    def test_parse_transcript_json_obj_valid(self):
        """Test parsing valid JSON object"""
        obj = {
            "summary": "Team meeting about project status",
            "attendees": ["John", "Alice", "Bob"],
            "action_items": ["Finish frontend", "Deploy backend", "Prepare tests"]
        }
        result = parse_transcript_json_obj(obj)
        
        self.assertEqual(result.summary, "Team meeting about project status")
        self.assertEqual(result.attendees, ["John", "Alice", "Bob"])
        self.assertEqual(len(result.action_items), 3)
        self.assertEqual(result.action_items[0], "Finish frontend")

    def test_parse_transcript_json_obj_missing_fields(self):
        """Test parsing JSON with missing fields"""
        obj = {"summary": "Brief meeting"}
        result = parse_transcript_json_obj(obj)
        
        self.assertEqual(result.summary, "Brief meeting")
        self.assertEqual(result.attendees, ["Meeting participants"])  # fallback
        self.assertEqual(len(result.action_items), 3)  # padded to 3

    def test_parse_transcript_json_obj_too_many_items(self):
        """Test parsing JSON with too many action items"""
        obj = {
            "summary": "Long meeting",
            "attendees": ["John", "Alice"],
            "action_items": ["Task 1", "Task 2", "Task 3", "Task 4", "Task 5"]
        }
        result = parse_transcript_json_obj(obj)
        
        self.assertEqual(len(result.action_items), 3)  # trimmed to 3
        self.assertEqual(result.action_items, ["Task 1", "Task 2", "Task 3"])

    def test_offline_summarizer_with_speakers(self):
        """Test offline summarizer with speaker labels"""
        transcript = """John: Good morning everyone, let's start the meeting.
Alice: I've completed the frontend work and will deploy tomorrow.
Bob: The backend API is ready for testing.
John: Great! Alice, please send the deployment notes to Bob."""
        
        result = _offline_summarizer(transcript)
        
        self.assertIn("John", result.attendees)
        self.assertIn("Alice", result.attendees)
        self.assertIn("Bob", result.attendees)
        self.assertEqual(len(result.action_items), 3)
        self.assertTrue(len(result.summary) > 0)

    def test_offline_summarizer_narrative_style(self):
        """Test offline summarizer with narrative mentions"""
        transcript = """The meeting started with Alice explaining the project status.
Bob mentioned that the database migration is complete.
Carol asked about the testing timeline.
Everyone agreed to meet again next week."""
        
        result = _offline_summarizer(transcript)
        
        self.assertIn("Alice", result.attendees)
        self.assertIn("Bob", result.attendees)
        self.assertIn("Carol", result.attendees)

    def test_offline_summarizer_no_speakers(self):
        """Test offline summarizer with no identifiable speakers"""
        transcript = """Meeting notes about project progress.
The team discussed various implementation options.
Several decisions were made regarding the timeline."""
        
        result = _offline_summarizer(transcript)
        
        self.assertEqual(result.attendees, ["Meeting participants"])
        self.assertEqual(len(result.action_items), 3)

    def test_extract_json_with_regex_complete(self):
        """Test regex JSON extraction with complete JSON"""
        text = '''Here's the analysis:
        {"summary": "Project meeting", "attendees": ["John", "Alice"], "action_items": ["Task 1", "Task 2", "Task 3"]}
        That's the result.'''
        
        result = _extract_json_with_regex(text)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["summary"], "Project meeting")
        self.assertEqual(len(result["attendees"]), 2)
        self.assertEqual(len(result["action_items"]), 3)

    def test_extract_json_with_regex_partial(self):
        """Test regex JSON extraction from partial matches"""
        text = '''Here is a partial JSON: {"summary": "Team standup meeting", "attendees": ["John", "Alice", "Bob"], "action_items": ["Review code", "Update docs", "Test features"]}'''
        
        result = _extract_json_with_regex(text)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["summary"], "Team standup meeting")
        self.assertEqual(len(result["attendees"]), 3)

    def test_extract_json_with_regex_no_match(self):
        """Test regex extraction when no JSON found"""
        text = "This is just plain text with no JSON structure."
        
        result = _extract_json_with_regex(text)
        
        self.assertIsNone(result)

    def test_summarize_meeting_empty_input(self):
        """Test error handling for empty input"""
        with self.assertRaises(ValueError):
            summarize_meeting("")
        
        with self.assertRaises(ValueError):
            summarize_meeting("   \n\t   ")

    def test_transcript_with_timestamps(self):
        """Test transcript with timestamps"""
        transcript = """[10:30] John: Good morning everyone
[10:31] Alice: Hello, let's start with updates
[10:32] Bob: I'll go first with the backend status"""
        
        result = _offline_summarizer(transcript)
        
        self.assertIn("John", result.attendees)
        self.assertIn("Alice", result.attendees)
        self.assertIn("Bob", result.attendees)

    def test_transcript_with_unicode_names(self):
        """Test transcript with unicode/international names"""
        transcript = """José: Hola everyone, let's begin.
François: Bonjour! I have the updates ready.
李明: 我们开始吧 (Let's start)."""
        
        result = _offline_summarizer(transcript)
        
        self.assertIn("José", result.attendees)
        self.assertIn("François", result.attendees)
        # Note: Chinese name might not be extracted by simple regex

    def test_action_items_extraction(self):
        """Test action item extraction from transcript"""
        transcript = """John: I will prepare the presentation by Friday.
Alice: We need to schedule a client meeting next week.
Bob: I should review the code before deployment.
Carol: The team must complete testing by Thursday."""
        
        result = _offline_summarizer(transcript)
        
        # Should find action-oriented phrases
        action_text = " ".join(result.action_items).lower()
        self.assertTrue(any(word in action_text for word in ["prepare", "schedule", "review", "complete"]))

    def test_single_speaker_transcript(self):
        """Test transcript with only one speaker"""
        transcript = """John: I'll start by reviewing the project status.
John: The frontend is 90% complete and ready for testing.
John: Next week I'll focus on the backend integration.
John: That concludes my update for today."""
        
        result = _offline_summarizer(transcript)
        
        self.assertEqual(result.attendees, ["John"])
        self.assertEqual(len(result.action_items), 3)

    @patch('utils.genai')
    def test_llm_unavailable_fallback(self, mock_genai):
        """Test fallback when LLM is unavailable"""
        mock_genai = None
        
        transcript = "John: Let's discuss the project. Alice: I agree."
        result = summarize_meeting(transcript)
        
        # Should use offline fallback
        self.assertIsInstance(result, SummaryResult)
        self.assertTrue(len(result.attendees) > 0)
        self.assertEqual(len(result.action_items), 3)

    def test_very_short_transcript(self):
        """Test very short transcript"""
        transcript = "John: Hi. Alice: Hello."
        
        result = _offline_summarizer(transcript)
        
        self.assertIn("John", result.attendees)
        self.assertIn("Alice", result.attendees)
        self.assertEqual(len(result.action_items), 3)

    def test_action_items_padding(self):
        """Test that action items are always padded to 3"""
        transcript = "John: I will do one task."
        
        result = _offline_summarizer(transcript)
        
        self.assertEqual(len(result.action_items), 3)
        # Should have fallback items
        self.assertTrue(any("follow up" in item.lower() for item in result.action_items))

    def test_attendees_deduplication(self):
        """Test that duplicate attendees are removed"""
        transcript = """John: First comment.
John: Second comment.
Alice: My comment.
John: Third comment."""
        
        result = _offline_summarizer(transcript)
        
        # Should only have John once
        self.assertEqual(result.attendees.count("John"), 1)
        self.assertIn("Alice", result.attendees)

    def test_summary_generation_quality(self):
        """Test that summary captures key information"""
        transcript = """John: We're here to discuss the Q4 project timeline.
Alice: The development phase is on track for completion by December.
Bob: Testing will begin in November and run for three weeks.
Carol: We need to coordinate with the marketing team for the launch."""
        
        result = _offline_summarizer(transcript)
        
        # Summary should contain key topics
        summary_lower = result.summary.lower()
        self.assertTrue(any(word in summary_lower for word in ["project", "timeline", "development", "testing"]))


class TestTranscriptAnalyzerIntegration(unittest.TestCase):
    """Integration tests that may use real LLM calls"""
    
    def setUp(self):
        self.sample_transcript = """John: Good morning team, let's review our sprint progress.
Alice: I've completed the user authentication module and it's ready for testing.
Bob: The database migration is finished. I'll deploy it to staging today.
Carol: I'll start the QA testing tomorrow and should have results by Friday.
John: Excellent! Alice, can you help Carol with the test cases?
Alice: Absolutely, I'll send her the documentation this afternoon."""

    @unittest.skipIf(not os.environ.get('GEMINI_API_KEY'), 
                     "GEMINI_API_KEY not set - skipping LLM integration test")
    def test_full_llm_integration(self):
        """Integration test with real LLM (only runs if API key available)"""
        result = summarize_meeting(self.sample_transcript)
        
        # Verify structure
        self.assertIsInstance(result, SummaryResult)
        self.assertTrue(len(result.summary) > 0)
        self.assertTrue(len(result.attendees) > 0)
        self.assertEqual(len(result.action_items), 3)
        
        # Verify content quality
        self.assertIn("John", result.attendees)
        self.assertIn("Alice", result.attendees)
        self.assertTrue(any("test" in item.lower() for item in result.action_items))

    def test_offline_only_integration(self):
        """Integration test using only offline processing"""
        with patch.dict('os.environ', {}, clear=True):  # Remove API key
            result = summarize_meeting(self.sample_transcript)
            
            # Should work with offline fallback
            self.assertIsInstance(result, SummaryResult)
            self.assertIn("John", result.attendees)
            self.assertIn("Alice", result.attendees)
            self.assertIn("Bob", result.attendees)
            self.assertIn("Carol", result.attendees)
            self.assertEqual(len(result.action_items), 3)


if __name__ == '__main__':
    # Add import for os in integration tests
    import os
    unittest.main(verbosity=2)