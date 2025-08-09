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
    from google import genai
    from google.genai import types
except Exception:
    genai = None
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


def _offline_summarizer(notes: str) -> SummaryResult:
    """Simple heuristic fallback when LLM fails."""
    lines = [line.strip() for line in notes.split('\n') if line.strip()]
    
    # Extract attendees from speaker patterns
    attendees = set()
    speaker_patterns = [
        r'^\[[0-9:]+\]\s*([A-Za-z\u00C0-\u017F]+)\s*:',  # "[10:30] John:"
        r'^([A-Za-z\u00C0-\u017F]+)\s*:',  # "John:"
        r'([A-Za-z\u00C0-\u017F]+):\s*',  # "Alice: "
        r'([A-Za-z\u00C0-\u017F]+)\s+said',  # "Alice said"
        r'([A-Za-z\u00C0-\u017F]+)\s+mentioned',  # "Bob mentioned"
        r'([A-Za-z\u00C0-\u017F]+)\s+asked',  # "Carol asked"
        r'([A-Za-z\u00C0-\u017F]+)\s+explaining',  # "Alice explaining"
        r'([A-Za-z\u00C0-\u017F]+)\s+agreed',  # "Everyone agreed"
    ]
    
    for line in lines:
        for pattern in speaker_patterns:
            matches = re.findall(pattern, line)
            for match in matches:
                if len(match) > 1 and match.isalpha():
                    attendees.add(match.title())
    
    # Take first 2-3 sentences as summary
    sentences = re.split(r'[.!?]', notes)
    summary = ". ".join(sentences[:2]) if sentences else "Meeting discussion completed"
    
    # Extract action items heuristically
    action_words = ['will', 'should', 'need to', 'plan to', 'going to', 'must', 'have to']
    action_items = []
    
    for line in lines:
        line_lower = line.lower()
        if any(word in line_lower for word in action_words):
            # Clean up and make it actionable
            clean_line = line.strip('- •').strip()
            # Remove speaker prefix if present
            if ':' in clean_line[:30]:
                clean_line = clean_line.split(':', 1)[1].strip()
            
            if len(clean_line) > 10:
                # Make it start with a verb if it doesn't
                if not any(clean_line.lower().startswith(verb) for verb in ['review', 'prepare', 'send', 'call', 'meet', 'create', 'draft', 'schedule']):
                    clean_line = f"Follow up on {clean_line.lower()}"
                action_items.append(clean_line)
    
    # Ensure exactly 3 items
    while len(action_items) < 3:
        action_items.append(f"Review meeting notes and follow up on item {len(action_items) + 1}")
    
    return SummaryResult(
        summary=summary,
        attendees=list(attendees)[:5] if attendees else ["Meeting participants"],
        action_items=action_items[:3]
    )


def _extract_json_with_regex(text: str) -> Optional[dict]:
    """Try to extract JSON using regex patterns."""
    # Look for JSON-like patterns with all three fields
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
    
    # Try to build JSON from parts
    summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', text)
    attendees_match = re.search(r'"attendees"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    items_match = re.search(r'"action_items"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    
    if summary_match and attendees_match and items_match:
        try:
            summary = summary_match.group(1)
            attendees_text = attendees_match.group(1)
            items_text = items_match.group(1)
            
            # Extract quoted strings from the arrays
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



def call_llm(notes: str, model: str = "gemini-2.0-flash") -> SummaryResult:
    """Calls Gemini to analyze transcript and return structured result."""
    if genai is None or types is None:
        _debug_log("google-genai not available, using offline fallback")
        return _offline_summarizer(notes)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        _debug_log("GEMINI_API_KEY not set, using offline fallback")
        return _offline_summarizer(notes)

    try:
        genai.configure(api_key=api_key)
        prompt = TRANSCRIPT_PROMPT.format(notes=notes)

        # Try non-streaming first
        config = genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1,
        )

        _debug_log(f"Analyzing transcript with LLM ('{model}')...")
        
        try:
            # Non-streaming call
            llm = genai.GenerativeModel(model_name=model)
            response = llm.generate_content(
                contents=[genai.types.Content(role="user", parts=[genai.types.Part.from_text(text=prompt)])],
                generation_config=config,
            )
            
            raw = response.text if hasattr(response, 'text') else str(response)
            _debug_log(f"LLM response: {repr(raw[:200])}")
            
        except Exception as e:
            _debug_log(f"Non-streaming failed: {e}, trying streaming...")
            
            # Fall back to streaming
            chunks = []
            llm = genai.GenerativeModel(model_name=model)
            for chunk in llm.generate_content(
                contents=[genai.types.Content(role="user", parts=[genai.types.Part.from_text(text=prompt)])],
                generation_config=config,
                stream=True,
            ):
                text = getattr(chunk, "text", "") or ""
                if text:
                    chunks.append(text)
            raw = "".join(chunks)
            _debug_log(f"Streaming response: {repr(raw[:200])}")

        if not raw or len(raw.strip()) < 10:
            _debug_log("Empty response, using offline fallback")
            return _offline_summarizer(notes)

        # Try direct JSON parsing
        try:
            raw_clean = raw.strip()
            if raw_clean.startswith('```json'):
                raw_clean = raw_clean.replace('```json', '').replace('```', '').strip()
            
            obj = json.loads(raw_clean)
            _debug_log("Direct JSON parsing succeeded!")
            return parse_transcript_json_obj(obj)
            
        except Exception as e:
            _debug_log(f"Direct JSON parsing failed: {e}")

        # Try regex extraction
        _debug_log("Trying regex extraction...")
        regex_result = _extract_json_with_regex(raw)
        if regex_result:
            _debug_log("Regex extraction succeeded!")
            return parse_transcript_json_obj(regex_result)

        # Final fallback
        _debug_log("All parsing methods failed, using offline fallback")
        return _offline_summarizer(notes)

    except Exception as e:
        _debug_log(f"LLM call completely failed: {e}, using offline fallback")
        return _offline_summarizer(notes)


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