# 🎯 Coding Challenge: Meeting Transcript Analyzer

## 📋 Challenge Overview

**Difficulty Level**: Intermediate to Advanced  
**Estimated Time**: 4-6 hours  
**Technologies**: Python 3.8+, Google Gemini API, File I/O, JSON Processing

Build a production-ready **Meeting Transcript Analysis Pipeline** that automatically processes meeting transcripts and extracts structured insights using AI.

---

## 🎪 Problem Statement

You are tasked with creating an intelligent system that can:

1. **Monitor** a directory for new meeting transcript files
2. **Process** files automatically using AI (Google Gemini LLM)
3. **Extract** structured data: summary, attendees, and action items
4. **Output** results in JSON format
5. **Log** performance metrics and handle errors gracefully
6. **Scale** horizontally with multiple workers

Your solution should be **production-ready** with proper error handling, atomic operations, comprehensive testing, and clear documentation.

---

## 📝 Technical Requirements

### 🏗️ Architecture Requirements

**Core Components to Implement:**

1. **`worker.py`** - Main processing engine
   - File monitoring and claiming system
   - Atomic file operations (prevent race conditions)
   - Main processing loop with graceful shutdown
   
2. **`utils.py`** - AI integration and utilities
   - Google Gemini API integration
   - JSON parsing with fallback mechanisms
   - Metrics logging functionality
   - Directory management utilities

3. **`test_core_pipeline.py`** - Comprehensive test suite
   - Unit and integration tests
   - Mock testing for consistent results
   - Real API testing (conditional on API key)

### 🔧 Functional Requirements

#### **File Processing Pipeline**
```
input/*.txt → [Claim File] → [AI Analysis] → [JSON Output] → [Metrics Logging] → [Cleanup]
```

#### **Data Extraction Requirements**
- **Summary**: Intelligent overview of meeting content
- **Attendees**: Extract speaker names from various formats:
  - `"John: Hello everyone"`
  - `"Alice mentioned that..."`
  - `"[10:30] Bob: Let's start"`
- **Action Items**: Exactly 3 action items (pad if needed)

#### **Output Format**
```json
{
  "job_id": "job-abc12345",
  "summary": "Brief meeting overview",
  "attendees": ["Name1", "Name2", "Name3"],
  "action_items": [
    "Action item 1",
    "Action item 2", 
    "Action item 3"
  ]
}
```

#### **Metrics Logging**
CSV format: `job_id,status,duration_sec,error`

---

## 🎯 Detailed Implementation Specifications

### 📁 **Directory Structure**
```
production-genai/
├── worker.py              # Main processing engine
├── utils.py               # AI integration & utilities  
├── test_core_pipeline.py  # Test suite
├── requirements.txt       # Dependencies
├── README.md              # Documentation
├── description.md         # This specification
├── input/                 # Input directory (auto-created)
├── output/                # Output directory (auto-created)
├── logs/                  # Logs directory (auto-created)
└── Test_Files/            # Sample test data
    └── Meeting Transcript.txt
```

### 🔍 **worker.py Specifications**

**Required Functions:**

```python
def claim_next_file() -> Path | None:
    """
    Atomically claim the next available .txt file in input/
    - Find .txt files in input/ directory
    - Rename first available file to .processing extension
    - Return Path object or None if no files
    - Handle race conditions between multiple workers
    """

def process_file(path: Path) -> None:
    """
    Process a single transcript file
    - Read file content with UTF-8 encoding
    - Call AI analysis via utils.summarize_meeting()
    - Generate unique job_id (format: job-<8 hex chars>)
    - Save results to output/<filename>.json
    - Log metrics to logs/metrics.csv
    - Handle errors gracefully (save .error.json on failure)
    - Always cleanup processing file
    """

def main() -> None:
    """
    Main worker loop
    - Create runtime directories
    - Poll input/ directory every 2 seconds
    - Display queue depth when > 0
    - Process files until KeyboardInterrupt
    - Graceful shutdown handling
    """
```

**Constants:**
- `INPUT_DIR = Path("input")`
- `OUTPUT_DIR = Path("output")`
- `LOG_FILE = "logs/metrics.csv"`
- `POLL_INTERVAL = 2.0`

### 🤖 **utils.py Specifications**

**Required Functions:**

```python
@dataclass
class SummaryResult:
    summary: str
    attendees: List[str]  # Max 5 attendees
    action_items: List[str]  # Exactly 3 items

def summarize_meeting(notes: str) -> SummaryResult:
    """
    AI-powered transcript analysis
    - Validate input (raise ValueError if empty)
    - Call Google Gemini API with structured prompt
    - Parse JSON response with multiple fallback methods
    - Return SummaryResult with validated data
    """

def log_metrics(path: str, job_id: str, status: str, duration_sec: float, error: Optional[str] = None) -> None:
    """
    Log job metrics to CSV file
    - Create directory if doesn't exist
    - Add header if file doesn't exist
    - Append metrics row with proper CSV escaping
    """

def ensure_runtime_dirs() -> None:
    """Create input/, output/, logs/ directories if they don't exist"""

def list_queue_depth() -> int:
    """Count .txt files in input/ directory"""
```

**AI Integration Requirements:**
- Use Google Gemini API (`gemini-2.0-flash-exp` model)
- Structured JSON output with `response_mime_type="application/json"`
- Temperature: 0.1 for consistency
- Multiple JSON parsing strategies:
  1. Direct JSON parsing
  2. Regex extraction
  3. Field-by-field extraction
- Robust error handling with detailed debug logging

### 📊 **Prompt Engineering Specification**

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

---

## 🧪 Test Cases Specification

### **Test Suite Requirements** (`test_core_pipeline.py`)

Your implementation must pass **ALL** of these test cases:

#### **Test 01: Worker Pipeline Startup**
```python
def test_01_worker_pipeline_startup(self):
    """Test that worker pipeline can start properly with all required directories."""
    # MUST PASS:
    - input/, output/, logs/ directories exist
    - All directories initially empty
    - list_queue_depth() returns 0
    - claim_next_file() returns None when no files
```

#### **Test 02: LLM Integration with API Key**
```python
def test_02_llm_integration_with_api_key(self):
    """Test LLM integration with actual API key if available."""
    # MUST PASS (if GEMINI_API_KEY is set):
    - Real API call succeeds
    - Returns SummaryResult object
    - Summary is non-empty string (>10 chars)
    - Attendees is non-empty list
    - Action items list has exactly 3 items
    - All data types are correct
```

#### **Test 03: Real File Processing**
```python
def test_03_real_file_processing_meeting_transcript(self):
    """Test processing actual Meeting Transcript.txt from Test_Files folder."""
    # MUST PASS:
    - Successfully claims Meeting Transcript.txt
    - File has .processing extension when claimed
    - Processing completes without errors
    - Processing file is cleaned up after completion
    - Works with both real API and mock
```

#### **Test 04: Input Folder & File Detection**
```python
def test_04_input_folder_creation_and_file_detection(self):
    """Test input folder is created and can detect input files."""
    # MUST PASS:
    - Input directory exists and is writable
    - Queue depth starts at 0
    - Can create multiple .txt files
    - list_queue_depth() accurately counts files
    - claim_next_file() works for multiple files
    - Files claimed in correct order (alphabetical)
    - No more files to claim when all processed
```

#### **Test 05: Output Folder with Summary JSON**
```python
def test_05_output_folder_with_summary_json(self):
    """Test output folder creation and JSON summary generation."""
    # MUST PASS:
    - Output directory exists and is writable
    - JSON file created with correct filename
    - JSON contains all required fields: job_id, summary, attendees, action_items
    - job_id follows format: "job-<8 hex chars>"
    - summary is non-empty string
    - attendees is list (can be empty)
    - action_items is list with exactly 3 items
    - JSON is properly formatted and parseable
```

#### **Test 06: CSV Log Presence & Structure**
```python
def test_06_csv_log_presence_and_structure(self):
    """Test CSV log file creation and proper structure."""
    # MUST PASS:
    - logs/ directory exists
    - CSV file created after processing
    - Correct header: "job_id,status,duration_sec,error"
    - Data row has 4 columns
    - job_id starts with "job-"
    - status is "completed" or "failed"
    - duration_sec is valid float >= 0
    - Multiple entries work correctly
    - CSV properly formatted (no newlines in fields)
```

---

## 🎪 Edge Cases & Error Handling

Your implementation must handle these scenarios:

### **File System Edge Cases**
- ✅ Empty input files
- ✅ Permission denied errors
- ✅ Disk full scenarios
- ✅ Concurrent file access (multiple workers)
- ✅ File renamed/deleted during processing
- ✅ Non-UTF8 encoded files

### **API Edge Cases**
- ✅ Network timeouts
- ✅ API rate limiting
- ✅ Invalid API key
- ✅ Malformed API responses
- ✅ Empty/null responses
- ✅ JSON parsing failures

### **Data Edge Cases**
- ✅ Transcripts with no speakers
- ✅ Transcripts with only timestamps
- ✅ Unicode characters in names
- ✅ Very long transcripts (>10,000 chars)
- ✅ Transcripts with no action items
- ✅ Mixed transcript formats

---

## 🔒 Production Requirements

### **Security & Reliability**
- ✅ **No hardcoded secrets** - API keys via environment variables
- ✅ **Input validation** - Sanitize all file inputs
- ✅ **Error boundaries** - No uncaught exceptions crash the worker
- ✅ **Atomic operations** - Race condition prevention
- ✅ **Resource cleanup** - Proper file handle management

### **Performance & Scalability**
- ✅ **Memory efficient** - Don't load entire files into memory unnecessarily
- ✅ **Concurrent workers** - Multiple instances can run safely
- ✅ **Graceful shutdown** - SIGINT/SIGTERM handling
- ✅ **Monitoring ready** - Comprehensive metrics logging

### **Code Quality**
- ✅ **Type hints** - All functions properly typed
- ✅ **Docstrings** - Clear documentation for all functions
- ✅ **Error messages** - Helpful, actionable error messages
- ✅ **Consistent style** - Follow Python conventions

---

## 🎯 Success Criteria

Your implementation is considered complete when:

### **✅ Functional Requirements**
- [ ] All 6 test cases pass with verbose output
- [ ] Can process the provided `Meeting Transcript.txt` successfully
- [ ] Multiple workers can run concurrently without conflicts
- [ ] Graceful shutdown with Ctrl+C
- [ ] Proper JSON output format maintained

### **✅ Technical Requirements**
- [ ] Code follows Python best practices
- [ ] Proper error handling throughout
- [ ] No memory leaks or resource issues
- [ ] Clean separation of concerns
- [ ] Comprehensive logging and debugging

### **✅ Integration Requirements**
- [ ] Google Gemini API integration works
- [ ] Environment variable configuration
- [ ] File system operations are atomic
- [ ] CSV metrics logging is accurate
- [ ] All dependencies in requirements.txt

---

## 📦 Dependencies

Your `requirements.txt` should contain:

```
google-genai
python-dotenv
```

---

## 🏃‍♂️ Getting Started

1. **Set up environment**:
   ```bash
   pip install -r requirements.txt
   echo "GEMINI_API_KEY=your_key_here" > .env
   ```

2. **Run tests** to verify your implementation:
   ```bash
   python -m unittest test_core_pipeline.py -v
   ```

3. **Test with real data**:
   ```bash
   # Copy test file
   cp Test_Files/Meeting\ Transcript.txt input/
   
   # Run worker
   python worker.py
   ```

4. **Verify outputs**:
   - Check `output/` for JSON files
   - Check `logs/metrics.csv` for performance data

---

## 🎖️ Bonus Challenges (Optional)

If you complete the core requirements, consider these enhancements:

- **🚀 Performance**: Implement async file processing
- **🔧 Configuration**: Add configurable polling intervals and timeouts  
- **📊 Monitoring**: Add more detailed metrics and health checks
- **🎨 UI**: Create a simple web interface to view processed files
- **🔄 Resilience**: Implement retry logic with exponential backoff
- **📝 Logging**: Add structured logging with different log levels

---

## ❓ Evaluation Rubric

| Category | Weight | Criteria |
|----------|--------|----------|
| **Functionality** | 40% | All test cases pass, handles edge cases |
| **Code Quality** | 25% | Clean, readable, well-structured code |
| **Error Handling** | 20% | Robust error handling and recovery |
| **Testing** | 10% | Comprehensive test coverage |
| **Documentation** | 5% | Clear comments and docstrings |

**Minimum passing score**: 80%

---

## 📞 Support

- Check existing tests for expected behavior patterns
- Review the provided `Meeting Transcript.txt` for input format examples
- Use debug logging extensively during development
- Test with both real API and mock scenarios

**Good luck!** 🚀 Build something amazing!