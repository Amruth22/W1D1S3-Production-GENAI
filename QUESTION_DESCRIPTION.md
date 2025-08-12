# Production GenAI Pipeline - Advanced Coding Challenge

## 🎯 Problem Statement

Build a **Production-Ready AI Processing Pipeline** that automatically monitors, processes, and analyzes meeting transcripts using Google's Gemini AI. Your task is to create a scalable, fault-tolerant system that can handle concurrent file processing, extract structured insights from unstructured text, and provide comprehensive monitoring and error handling.

## 📋 Requirements Overview

### Core System Components
You need to implement a complete production pipeline with:

1. **File Processing Worker** with atomic operations and concurrent safety
2. **AI Integration Service** with Google Gemini API and robust parsing
3. **Metrics and Logging System** with CSV-based performance tracking
4. **Comprehensive Testing Suite** with real API integration and mocking
5. **Error Handling and Recovery** with graceful failure management
6. **Horizontal Scalability** supporting multiple concurrent workers

## 🏗️ System Architecture

```
input/*.txt → [File Claiming] → [AI Analysis] → [JSON Output] → [Metrics Logging]
                    ↓                ↓              ↓              ↓
            [Atomic Operations] → [Gemini API] → [Structured Data] → [CSV Logs]
                    ↓
            [Multi-Worker Safe] → [Error Recovery] → [Cleanup]
```

## 📚 Detailed Implementation Requirements

### 1. Worker Engine (`worker.py`)

**Core Processing Loop:**

```python
def main():
    """
    Main worker loop with monitoring and graceful shutdown
    - Create runtime directories (input/, output/, logs/)
    - Poll input/ directory every 2 seconds
    - Display queue depth when files are waiting
    - Process files until KeyboardInterrupt
    - Handle graceful shutdown
    """

def claim_next_file() -> Optional[Path]:
    """
    Atomically claim next available .txt file
    - Find .txt files in input/ directory (sorted order)
    - Rename first available to .processing extension
    - Return Path object or None if no files available
    - Prevent race conditions between multiple workers
    """

def process_file(path: Path):
    """
    Process single transcript file with full error handling
    - Generate unique job_id (format: job-<8 hex chars>)
    - Read file content with UTF-8 encoding
    - Call AI analysis via utils.summarize_meeting()
    - Save results to output/<filename>.json
    - Log metrics to logs/metrics.csv
    - Handle errors gracefully (save .error.json on failure)
    - Always cleanup processing file
    """
```

**Technical Specifications:**
- **Polling Interval**: 2.0 seconds
- **File Extensions**: Process `.txt` files, rename to `.processing`
- **Atomic Operations**: Prevent concurrent access conflicts
- **Error Recovery**: Always cleanup, never leave orphaned files
- **Monitoring**: Display queue depth and processing status

### 2. AI Integration Service (`utils.py`)

**Data Structures:**

```python
@dataclass
class SummaryResult:
    summary: str              # Meeting overview
    attendees: List[str]      # Speaker names (max 5)
    action_items: List[str]   # Exactly 3 action items
```

**Core Functions:**

```python
def summarize_meeting(notes: str) -> SummaryResult:
    """
    AI-powered transcript analysis with robust parsing
    - Validate input (raise ValueError if empty)
    - Call Google Gemini API with structured prompt
    - Parse JSON response with multiple fallback methods
    - Return SummaryResult with validated, cleaned data
    """

def call_llm(notes: str, model: str = "gemini-2.0-flash-exp") -> SummaryResult:
    """
    Direct LLM API integration
    - Use Google Gemini client with API key from environment
    - Configure for JSON output with low temperature (0.1)
    - Handle API errors and timeouts gracefully
    - Implement multiple JSON parsing strategies
    """

def parse_transcript_json_obj(obj: dict) -> SummaryResult:
    """
    Parse and validate JSON response
    - Extract summary, attendees, action_items
    - Clean and validate attendee names
    - Ensure exactly 3 action items (pad if needed)
    - Apply business rules and constraints
    """
```

**AI Integration Requirements:**
- **Model**: `gemini-2.0-flash-exp`
- **Output Format**: `application/json` MIME type
- **Temperature**: 0.1 for consistency
- **Parsing Strategy**: Multiple fallback methods (direct JSON, regex, field extraction)
- **Error Handling**: Comprehensive exception management with debug logging

### 3. Utility Functions

```python
def log_metrics(path: str, job_id: str, status: str, duration_sec: float, error: Optional[str] = None):
    """
    Log job performance metrics to CSV
    - Create directory if doesn't exist
    - Add header if file doesn't exist
    - Append metrics row with proper CSV escaping
    - Handle concurrent writes safely
    """

def ensure_runtime_dirs():
    """Create required directories: input/, output/, logs/"""

def list_queue_depth() -> int:
    """Count .txt files waiting in input/ directory"""
```

### 4. Prompt Engineering Specification

```python
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
```

## 🧪 Test Cases & Validation

Your implementation will be tested against these comprehensive scenarios:

### Test Case 1: Worker Pipeline Startup
```python
def test_01_worker_pipeline_startup(self):
    """Test that worker pipeline can start properly with all required directories."""
    # MUST PASS:
    assert Path("input").exists() and Path("input").is_dir()
    assert Path("output").exists() and Path("output").is_dir()
    assert Path("logs").exists() and Path("logs").is_dir()
    assert utils.list_queue_depth() == 0
    assert worker.claim_next_file() is None
```

### Test Case 2: LLM Integration with Real API
```python
def test_02_llm_integration_with_api_key(self):
    """Test LLM integration with actual API key if available."""
    # Skip if no API key available
    if not os.environ.get("GEMINI_API_KEY"):
        self.skipTest("GEMINI_API_KEY not set")
    
    test_transcript = """
    John: Good morning everyone, let's start our daily standup.
    Alice: I completed the frontend dashboard yesterday.
    Bob: Backend API is 90% complete.
    """
    
    result = utils.summarize_meeting(test_transcript)
    assert isinstance(result, utils.SummaryResult)
    assert len(result.summary) > 10
    assert len(result.attendees) > 0
    assert len(result.action_items) == 3
```

### Test Case 3: Real File Processing
```python
def test_03_real_file_processing_meeting_transcript(self):
    """Test processing actual Meeting Transcript.txt from Test_Files folder."""
    # Copy real meeting transcript to input
    test_files_dir = Path(self.orig_cwd) / "Test_Files"
    meeting_transcript = test_files_dir / "Meeting Transcript.txt"
    
    input_file = Path("input") / "meeting_transcript.txt"
    input_file.write_text(meeting_transcript.read_text(encoding="utf-8"))
    
    # Claim and process
    claimed_file = worker.claim_next_file()
    assert claimed_file is not None
    assert claimed_file.suffix == ".processing"
    
    # Process with real or mock LLM
    worker.process_file(claimed_file)
    
    # Verify cleanup
    assert not claimed_file.exists()
```

### Test Case 4: Input Folder & File Detection
```python
def test_04_input_folder_creation_and_file_detection(self):
    """Test input folder is created and can detect input files."""
    # Create multiple test files
    test_files = [
        ("meeting1.txt", "John: Project update.\nAlice: Frontend ready."),
        ("standup.txt", "Daily standup meeting.\nBob: Backend complete."),
        ("review.txt", "Code review session.\nCarol: Testing finished.")
    ]
    
    for filename, content in test_files:
        (Path("input") / filename).write_text(content)
    
    # Verify detection
    assert utils.list_queue_depth() == len(test_files)
    
    # Test claiming
    for i in range(len(test_files)):
        claimed = worker.claim_next_file()
        assert claimed is not None
    
    assert worker.claim_next_file() is None
```

### Test Case 5: Output JSON Generation
```python
def test_05_output_folder_with_summary_json(self):
    """Test output folder creation and JSON summary generation."""
    # Create test input
    input_file = Path("input") / "test_meeting.txt"
    input_file.write_text("Sarah: Welcome.\nMike: Database migration complete.")
    
    # Process with mock result
    claimed = worker.claim_next_file()
    mock_result = utils.SummaryResult(
        summary="Team meeting discussing database migration",
        attendees=["Sarah", "Mike"],
        action_items=["Document migration", "Review changes", "Schedule follow-up"]
    )
    
    # Process and verify output
    worker.process_file(claimed)  # Using mock
    
    output_file = Path("output") / "test_meeting.json"
    assert output_file.exists()
    
    with open(output_file) as f:
        data = json.load(f)
    
    assert "job_id" in data and data["job_id"].startswith("job-")
    assert "summary" in data and len(data["summary"]) > 0
    assert "attendees" in data and isinstance(data["attendees"], list)
    assert "action_items" in data and len(data["action_items"]) == 3
```

### Test Case 6: CSV Metrics Logging
```python
def test_06_csv_log_presence_and_structure(self):
    """Test CSV log file creation and proper structure."""
    # Process a file to generate metrics
    input_file = Path("input") / "metrics_test.txt"
    input_file.write_text("Alex: Quarterly results.\nJordan: Revenue up 15%.")
    
    claimed = worker.claim_next_file()
    worker.process_file(claimed)
    
    # Verify CSV structure
    metrics_file = Path("logs") / "metrics.csv"
    assert metrics_file.exists()
    
    csv_content = metrics_file.read_text()
    lines = csv_content.strip().split('\n')
    
    # Verify header
    assert lines[0] == "job_id,status,duration_sec,error"
    
    # Verify data row
    data_row = lines[1].split(',')
    assert len(data_row) == 4
    assert data_row[0].startswith("job-")
    assert data_row[1] in ["completed", "failed"]
    assert float(data_row[2]) >= 0  # Valid duration
```

## 📊 Evaluation Criteria

Your solution will be evaluated on:

1. **Functionality** (35%): All test cases pass, handles real meeting transcripts
2. **Concurrency Safety** (25%): Multiple workers can run without conflicts
3. **Error Handling** (20%): Robust exception management and recovery
4. **Code Quality** (15%): Clean architecture, documentation, best practices
5. **Performance** (5%): Efficient processing and resource usage

## 🔧 Technical Requirements

### Dependencies
```txt
google-genai>=0.3.0
python-dotenv>=1.0.0
```

### Environment Configuration
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Directory Structure
```
production-genai/
├── worker.py                    # Main processing engine
├── utils.py                     # AI integration & utilities
├── test_core_pipeline.py        # Comprehensive test suite
├── requirements.txt             # Dependencies
├── .env                         # Environment variables
├── input/                       # Input directory (auto-created)
├── output/                      # Output directory (auto-created)
├── logs/                        # Logs directory (auto-created)
└── Test_Files/                  # Sample test data
    ├── Meeting Transcript.txt   # Real meeting transcript
    └── Meeting Transcripts.txt  # Additional test data
```

### Performance Requirements
- **Processing Speed**: < 5 seconds per transcript (with API calls)
- **Memory Usage**: < 100MB per worker process
- **Concurrent Workers**: Support 3+ workers simultaneously
- **Error Recovery**: 100% cleanup rate, no orphaned files
- **Uptime**: Handle 24/7 operation with graceful shutdown

## 🚀 Advanced Features (Bonus Points)

Implement these for extra credit:

1. **Advanced Parsing**: Support multiple transcript formats (timestamps, speaker variations)
2. **Retry Logic**: Exponential backoff for API failures
3. **Health Monitoring**: Worker health checks and status reporting
4. **Configuration Management**: YAML/JSON configuration files
5. **Batch Processing**: Process multiple files in single API call
6. **Web Interface**: Simple dashboard for monitoring and management
7. **Docker Support**: Containerization with Docker Compose
8. **Async Processing**: Asynchronous file processing with asyncio

## 📝 Implementation Guidelines

### Atomic File Operations
```python
def claim_next_file() -> Optional[Path]:
    files = sorted([p for p in INPUT_DIR.glob("*.txt") if p.is_file()])
    for p in files:
        processing = p.with_suffix(".processing")
        try:
            p.rename(processing)  # Atomic operation
            return processing
        except (FileNotFoundError, PermissionError):
            continue  # File claimed by another worker
    return None
```

### Error Handling Strategy
```python
def process_file(path: Path):
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    start = time.time()
    status = "completed"
    error = None
    
    try:
        # Main processing logic
        text = path.read_text(encoding="utf-8", errors="ignore")
        result = summarize_meeting(text)
        # Save successful result
    except Exception as e:
        status = "failed"
        error = str(e)
        # Save error result
    finally:
        duration = time.time() - start
        log_metrics(LOG_FILE, job_id, status, duration, error)
        path.unlink(missing_ok=True)  # Always cleanup
```

### JSON Parsing with Fallbacks
```python
def call_llm(notes: str) -> SummaryResult:
    # Get raw response from API
    raw = response.text
    
    # Strategy 1: Direct JSON parsing
    try:
        obj = json.loads(raw.strip())
        return parse_transcript_json_obj(obj)
    except:
        pass
    
    # Strategy 2: Regex extraction
    regex_result = _extract_json_with_regex(raw)
    if regex_result:
        return parse_transcript_json_obj(regex_result)
    
    # Strategy 3: Field-by-field extraction
    # ... additional fallback methods
    
    raise RuntimeError("Failed to parse LLM response")
```

## 🎯 Success Criteria

Your implementation is successful when:

- ✅ All 6 test cases pass with verbose output
- ✅ Can process the provided `Meeting Transcript.txt` successfully
- ✅ Multiple workers (3+) can run concurrently without conflicts
- ✅ Handles API failures gracefully with proper error logging
- ✅ Produces valid JSON output with required fields
- ✅ CSV metrics logging works correctly with proper formatting
- ✅ Graceful shutdown with Ctrl+C (KeyboardInterrupt)
- ✅ No memory leaks or resource issues during extended operation

## 📋 Submission Requirements

### Required Files
1. **`worker.py`**: Main processing engine with polling loop
2. **`utils.py`**: AI integration service with Gemini API
3. **`test_core_pipeline.py`**: Complete test suite with 6 test methods
4. **`requirements.txt`**: Minimal dependency list
5. **`.env`**: Environment template (without actual API key)

### Code Quality Standards
- **Type Hints**: Use type annotations for all functions
- **Docstrings**: Clear documentation for all public functions
- **Error Messages**: Helpful, actionable error messages
- **Logging**: Debug logging with `_debug_log()` function
- **Constants**: Use module-level constants for configuration

## 🔍 Sample Usage Examples

### Basic Operation
```bash
# Setup
pip install -r requirements.txt
echo "GEMINI_API_KEY=your_key_here" > .env

# Create test file
echo "John: Hello team.\nAlice: Project update ready." > input/test.txt

# Run worker
python worker.py
# Output: 
# 📁 Meeting Transcript Analyzer started!
# 🔄 Processing: test.processing
# ✅ Processed: test
```

### Multiple Workers
```bash
# Terminal 1
python worker.py

# Terminal 2  
python worker.py

# Terminal 3
python worker.py
# All workers process different files automatically
```

### Testing
```bash
# Run all tests
python -m unittest test_core_pipeline.py -v

# Expected output:
# test_01_worker_pipeline_startup ... ok
# test_02_llm_integration_with_api_key ... ok
# test_03_real_file_processing_meeting_transcript ... ok
# test_04_input_folder_creation_and_file_detection ... ok
# test_05_output_folder_with_summary_json ... ok
# test_06_csv_log_presence_and_structure ... ok
```

## ⚠️ Important Notes

- **API Key Security**: Never commit real API keys to version control
- **File Encoding**: Handle UTF-8 encoding with error tolerance
- **Concurrent Safety**: Test with multiple workers to ensure no race conditions
- **Error Recovery**: System should never crash, always log errors
- **Resource Cleanup**: Always cleanup processing files, even on errors
- **Testing**: Ensure tests work with both real API and mock scenarios

Build a production-ready AI processing pipeline that demonstrates enterprise-level software engineering skills! 🚀