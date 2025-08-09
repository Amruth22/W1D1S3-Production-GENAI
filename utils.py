import os
import json
import time
import re
from dataclasses import dataclass
from typing import List, Optional

# LLM client (Gemini) with optional .env support
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from google.genai import Client, types
except Exception:
    Client = None
    types = None


@dataclass
class SummaryResult:
    summary: str
    attendees: List[str]
    action_items: List[str]


# Updated prompt for transcript analysis
TRANSCRIPT_PROMPT = """Analyze this meeting transcript and extract the following information:

1. Summary: Brief overview of what was discussed
2. Attendees: Names of people who spoke in the meeting
3. Action Items: Specific tasks or follow-ups mentioned (exactly 3 items)

Meeting Transcript:
{notes}

Return only this JSON format:
{{"summary": "brief summary of the meeting", "attendees": ["Name1", "Name2", "Name3"], "action_items": ["Action 1", "Action 2", "Action 3"]}}

Rules:
- Extract attendee names from speaker labels (e.g., "John:", "Alice said", etc.)
- Action items should start with verbs and be specific
- If fewer than 3 action items exist, create reasonable follow-up tasks
- Use only information present in the transcript"""


def _debug_log(message: str):
    """Simple debug logging to help diagnose issues."""
    print(f"[DEBUG] {message}")




def _extract_json_with_regex(text: str) -> Optional[dict]:
    """Try to extract JSON using regex patterns."""
    patterns = [
        r'\{[^{}]*"summary"[^{}]*"attendees"[^{}]*"action_items"[^{}]*\}',
        r'\{.*?"summary".*?"attendees".*?"action_items".*?\}',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except:
                continue
    
    summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', text)
    attendees_match = re.search(r'"attendees"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    items_match = re.search(r'"action_items"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    
    if summary_match and attendees_match and items_match:
        try:
            summary = summary_match.group(1)
            attendees_text = attendees_match.group(1)
            items_text = items_match.group(1)
            
            attendees = re.findall(r'"([^"]*)"', attendees_text)
            items = re.findall(r'"([^"]*)"', items_text)
            
            if attendees and items:
                return {
                    "summary": summary,
                    "attendees": attendees,
                    "action_items": items[:3]
                }
        except:
            pass
    
    return None



def call_llm(notes: str, model: str = "gemini-2.0-flash-exp") -> SummaryResult:
    """Calls Gemini to analyze transcript and return structured result."""
    if Client is None or types is None:
        raise RuntimeError("google-genai not available. Please install: pip install google-genai")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    client = Client(api_key=api_key)
    prompt = TRANSCRIPT_PROMPT.format(notes=notes)

    _debug_log(f"Analyzing transcript with LLM ('{model}')...")
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            )
        )
        
        raw = response.text
        _debug_log(f"LLM response: {repr(raw[:200])}")
        
    except Exception as e:
        _debug_log(f"LLM call failed: {e}")
        raise RuntimeError(f"LLM API call failed: {e}")

    if not raw or len(raw.strip()) < 10:
        raise RuntimeError("LLM returned empty response")

    try:
        raw_clean = raw.strip()
        if raw_clean.startswith('```json'):
            raw_clean = raw_clean.replace('```json', '').replace('```', '').strip()
        
        obj = json.loads(raw_clean)
        _debug_log("Direct JSON parsing succeeded!")
        return parse_transcript_json_obj(obj)
        
    except Exception as e:
        _debug_log(f"Direct JSON parsing failed: {e}")

    _debug_log("Trying regex extraction...")
    regex_result = _extract_json_with_regex(raw)
    if regex_result:
        _debug_log("Regex extraction succeeded!")
        return parse_transcript_json_obj(regex_result)

    raise RuntimeError("Failed to parse LLM response into valid JSON")


def parse_transcript_json_obj(obj: dict) -> SummaryResult:
    """Parse a JSON object into SummaryResult with attendees."""
    summary = (obj.get("summary") or "").strip()
    attendees = obj.get("attendees") or []
    action_items = obj.get("action_items") or []
    
    # Validate and clean attendees
    if not isinstance(attendees, list):
        attendees = []
    attendees = [str(x).strip().title() for x in attendees if str(x).strip()]
    if not attendees:
        attendees = ["Meeting participants"]
    
    # Validate and clean action items
    if not isinstance(action_items, list):
        action_items = []
    action_items = [str(x).strip() for x in action_items if str(x).strip()]
    
    # Ensure exactly 3 action items
    if len(action_items) < 3:
        action_items += ["Follow up on meeting outcomes"] * (3 - len(action_items))
    if len(action_items) > 3:
        action_items = action_items[:3]
    
    return SummaryResult(
        summary=summary or "Meeting discussion completed",
        attendees=attendees[:5],  # Limit to 5 attendees max
        action_items=action_items
    )


def summarize_meeting(notes: str) -> SummaryResult:
    if not notes or not notes.strip():
        raise ValueError("Notes are empty")
    return call_llm(notes)


def log_metrics(path: str, job_id: str, status: str, duration_sec: float, error: Optional[str] = None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    header_needed = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if header_needed:
            f.write("job_id,status,duration_sec,error\n")
        safe_error = (error or "").replace("\n", " ").replace(",", ";")
        f.write(f"{job_id},{status},{duration_sec:.3f},{safe_error}\n")


def ensure_runtime_dirs():
    for d in ("input", "output", "logs"):
        os.makedirs(d, exist_ok=True)


def list_queue_depth() -> int:
    try:
        return len([n for n in os.listdir("input") if n.lower().endswith(".txt")])
    except FileNotFoundError:
        return 0