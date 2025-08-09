import os
import time
import uuid
import json
from pathlib import Path

from utils import (
    ensure_runtime_dirs,
    summarize_meeting,
    log_metrics,
    list_queue_depth,
)

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
LOG_FILE = "logs/metrics.csv"
POLL_INTERVAL = 2.0  # seconds


def claim_next_file() -> Path | None:
    # List .txt files and claim one by renaming to .processing to avoid double-processing
    files = sorted([p for p in INPUT_DIR.glob("*.txt") if p.is_file()])
    for p in files:
        processing = p.with_suffix(".processing")
        try:
            p.rename(processing)
            return processing
        except FileNotFoundError:
            continue
        except PermissionError:
            continue
    return None


def process_file(path: Path):
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    start = time.time()
    status = "completed"
    error = None

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        result = summarize_meeting(text)
        out = {
            "job_id": job_id,
            "summary": result.summary,
            "attendees": result.attendees,
            "action_items": result.action_items,
        }
        out_path = OUTPUT_DIR / (path.stem + ".json")
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ Processed: {path.stem}".encode("utf-8"))
        print(f"   Summary: {result.summary[:100]}...".encode("utf-8"))
        print(f"   Attendees: {', '.join(result.attendees)}".encode("utf-8"))
        print(f"   Action Items: {len(result.action_items)} items".encode("utf-8"))
    except Exception as e:
        status = "failed"
        error = str(e)
        err_path = OUTPUT_DIR / (path.stem + ".error.json")
        err_payload = {
            "job_id": job_id,
            "error": error,
        }
        err_path.write_text(json.dumps(err_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"❌ Failed: {path.stem} - {error}".encode("utf-8"))
    finally:
        duration = time.time() - start
        log_metrics(LOG_FILE, job_id, status, duration, error)
        # Remove the processing file regardless
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


def main():
    ensure_runtime_dirs()
    print("📁 Meeting Transcript Analyzer started!")
    print("   Watching 'input/' for .txt files...")
    print("   Will extract: Summary + Attendees + Action Items")
    print("   Press Ctrl+C to stop.\n")
    
    while True:
        try:
            depth = list_queue_depth()
            if depth > 0:
                print(f"📊 Queue depth: {depth}")
            
            f = claim_next_file()
            if f is None:
                time.sleep(POLL_INTERVAL)
                continue
                
            print(f"🔄 Processing: {f.name}")
            process_file(f)
            print()  # Add blank line for readability
            
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
            break
        except Exception as e:
            print(f"⚠️  Worker error: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()