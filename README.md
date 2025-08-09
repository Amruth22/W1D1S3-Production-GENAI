# Folder Watcher - Meeting Transcript Analyzer

Beginner-friendly project: drop meeting transcript `.txt` files into `input/`, a worker picks them up, analyzes the transcript to extract **summary**, **attendees**, and **action items**, then writes results to `output/` plus simple metrics to `logs/metrics.csv`.

No web APIs required. You can run 1 or more workers to simulate scaling.

## What it extracts
- **Summary**: Brief overview of what was discussed
- **Attendees**: Names of people who spoke (extracted from speaker labels like "John:", "Alice said", etc.)
- **Action Items**: Exactly 3 specific tasks or follow-ups mentioned

## How it works
- Put meeting transcript files as `.txt` files into `input/`
- Run `python worker.py`
- The worker will:
  - Read a transcript from `input/`
  - Ask the LLM to analyze and extract summary, attendees, and action items
  - Write a JSON result into `output/<filename>.json`
  - Append a row to `logs/metrics.csv` with job duration and status
- Start multiple workers (in separate terminals) to process files in parallel

## Setup

1) Clone and install:
```bash
git clone https://github.com/Amruth22/folder-watcher.git
cd folder-watcher
pip install -r requirements.txt
```

2) Configure API key (or use heuristic fallback):
- Create `.env` file:
```
GEMINI_API_KEY=your_key_here
```

3) Create runtime folders:
```bash
# Windows PowerShell
New-Item -ItemType Directory -Force -Path @('input','output','logs')

# macOS/Linux/Git Bash
mkdir -p input output logs
```

## Run a worker
```bash
python worker.py
```
Drop transcript files into `input/` while the worker is running.

## Example Input
Create a file `input/team-meeting.txt`:
```
John: Good morning everyone, let's start with the project update.
Alice: The frontend is 80% complete. I need to finish the login page by Friday.
Bob: Backend API is ready. I'll deploy to staging tomorrow.
Carol: QA testing will begin next week. I'll prepare the test cases.
John: Great! Alice, can you also review the design docs? Bob, please send the API documentation to Carol.
Alice: Sure, I'll review them by Thursday.
Bob: Will do, I'll send everything today.
```

## Example Output
`output/team-meeting.json`:
```json
{
  "job_id": "job-abc123",
  "summary": "Team discussed project progress with frontend 80% complete and backend API ready for staging deployment",
  "attendees": ["John", "Alice", "Bob", "Carol"],
  "action_items": [
    "Finish the login page by Friday",
    "Deploy backend API to staging tomorrow", 
    "Review design docs by Thursday"
  ]
}
```

## Supported Transcript Formats

The analyzer handles various meeting transcript formats:

### Speaker Labels
```
John: Let's start the meeting.
Alice: I have the updates ready.
```

### Narrative Style
```
Alice mentioned the project is on track.
Bob said he'll handle the deployment.
Carol asked about the timeline.
```

### With Timestamps
```
[10:30] John: Good morning everyone
[10:31] Alice: Hello, let's begin
```

### Mixed Formats
```
John: We should start. Alice said she's ready.
[10:32] Bob: I agree with Alice.
```

## Testing

### Run Unit Tests
```bash
# Run all tests
python -m unittest discover
```

### Test Categories
- **Core Function Tests**: JSON parsing, data structure validation
- **Attendee Extraction**: Speaker labels, narrative mentions, unicode names, and timestamps
- **Action Items**: Extraction, padding to 3 items, verb formatting
- **JSON Parsing**: Regex extraction, malformed JSON handling
- **Edge Cases**: Timestamps, empty input, single speaker
- **Integration**: Real LLM calls vs offline fallback

### Sample Test Data
Create test files in `input/` to verify functionality:

**Simple Meeting** (`input/simple.txt`):
```
John: Project status update.
Alice: Frontend complete.
Bob: Backend ready for testing.
```

**Complex Meeting** (`input/complex.txt`):
```
[09:00] Sarah: Good morning team, let's review our sprint.
Mike mentioned he finished the API integration yesterday.
[09:05] Lisa: I'll start QA testing today and finish by Wednesday.
Sarah: Great! Mike, can you help Lisa with the test data?
Mike: Absolutely, I'll prepare it this morning.
```

## Scaling
- Start more workers:
```bash
python worker.py  # Terminal 1
python worker.py  # Terminal 2
```
Each worker will pick different files automatically.

## Monitoring (basic)
- **Queue depth**: number of files currently in `input/`
- **Job duration**: captured per file in `logs/metrics.csv`
- **Failures**: rows with status=failed in `logs/metrics.csv`
- **Success rate**: completed vs failed jobs

### Sample Metrics Output
`logs/metrics.csv`:
```csv
job_id,status,duration_sec,error
job-abc123,completed,2.456,
job-def456,completed,1.823,
job-ghi789,failed,0.234,Empty input file
```

## Features
- **Smart extraction**: Finds speaker names from various patterns, including timestamps and unicode characters
- **Offline fallback**: If LLM fails, uses heuristic analysis to still produce results
- **Multiple parsing methods**: Direct JSON, regex extraction, and fallback ensure reliability
- **Beginner-friendly**: No web APIs, just file processing
- **Robust error handling**: Jobs never fail completely, always produce output
- **Unicode support**: Handles international names and characters
- **Flexible input**: Supports various transcript formats

## Architecture

```
input/           # Drop .txt transcript files here
├── meeting1.txt
├── standup.txt
└── review.txt

worker.py        # Watches input/, processes files
├── Claims files (renames to .processing)
├── Calls utils.summarize_meeting()
├── Writes JSON to output/
└── Logs metrics to logs/

utils.py         # Core analysis logic
├── LLM integration (Gemini)
├── JSON parsing & cleaning
├── Offline fallback analysis
└── Attendee/action extraction

output/          # Results written here
├── meeting1.json
├── standup.json
└── review.json

logs/            # Metrics and debugging
└── metrics.csv
```

## Project structure
- `worker.py` - Folder watcher worker with transcript analysis
- `utils.py` - LLM integration and offline fallback for transcript processing
- `test_transcript_analyzer.py` - Comprehensive unit tests
- `requirements.txt` - Dependencies (google-genai, python-dotenv)
- `README.md` - This guide

## Troubleshooting

### Common Issues

**No output files generated:**
- Check that files are `.txt` format in `input/`
- Verify worker is running: `python worker.py`
- Check `logs/metrics.csv` for error details

**LLM parsing errors:**
- System automatically falls back to offline analysis
- Check debug output: `[DEBUG]` messages in console
- Verify API key in `.env` file

**Empty attendees list:**
- Ensure transcript has speaker labels like "Name:" or "Name said"
- System will use "Meeting participants" as fallback

**Incorrect action items:**
- System always generates exactly 3 items
- Uses fallback items if insufficient actions found
- Check transcript has action-oriented language ("will", "should", "need to")

### Debug Mode
The system provides detailed debug logging:
```
[DEBUG] Analyzing transcript with LLM...
[DEBUG] LLM response: {"summary": "..."}
[DEBUG] Direct JSON parsing succeeded!
```

## Notes
- If the API key is missing, the system automatically uses offline heuristic analysis
- Supports various transcript formats (speaker labels, timestamps, etc.)
- Keep `input/` small. This is for learning, not production
- Files are processed in alphabetical order
- Multiple workers prevent processing the same file twice
- All jobs complete successfully (offline fallback ensures no failures)

## Learning Objectives
This project teaches:
- **File processing**: Watching folders, claiming files, atomic operations
- **LLM integration**: API calls, JSON parsing, error handling
- **Fallback strategies**: Offline processing when APIs fail
- **Data extraction**: Regex patterns, text analysis, structured output
- **Monitoring**: Metrics collection, job tracking, performance measurement
- **Scaling**: Multiple workers, queue management, parallel processing
- **Testing**: Unit tests, integration tests, edge case handling
