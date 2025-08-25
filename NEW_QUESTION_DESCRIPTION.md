# Production AI Meeting Transcript Processor - Question Description

## Overview

Build a production-ready AI processing pipeline that automatically monitors a directory for meeting transcript files, processes them using Google's Gemini AI to extract structured insights, and logs performance metrics. This project demonstrates how to create scalable, fault-tolerant systems that handle concurrent file processing with proper error handling and recovery mechanisms.

## Project Objectives

1. **File Processing Pipeline:** Create a worker system that continuously monitors an input directory, atomically claims files to prevent conflicts, and processes them through an AI analysis workflow.

2. **AI Integration and Parsing:** Integrate with Google's Gemini AI to analyze meeting transcripts and extract structured data including summaries, attendee lists, and action items with robust JSON parsing strategies.

3. **Concurrent Processing Safety:** Implement atomic file operations that allow multiple workers to run simultaneously without conflicts, using file renaming techniques for safe claiming mechanisms.

4. **Structured Data Extraction:** Design a system that consistently extracts meeting summaries, identifies attendees from speaker patterns, and generates exactly three actionable items from transcript content.

5. **Production Monitoring and Logging:** Build comprehensive logging systems that track job performance, success rates, and error conditions using CSV-based metrics storage.

6. **Error Handling and Recovery:** Implement robust error handling that ensures system reliability, proper cleanup of processing files, and graceful degradation when API calls fail.

## Key Features to Implement

- Continuous file monitoring worker that polls input directories and processes transcript files automatically
- Atomic file claiming system using file extensions to prevent race conditions between multiple workers
- AI-powered transcript analysis that extracts summaries, attendees, and action items using structured prompts
- Multiple JSON parsing strategies with fallback mechanisms for reliable data extraction
- Comprehensive metrics logging system tracking job performance and error rates
- Production-ready error handling with proper cleanup and recovery mechanisms
- Support for concurrent workers processing different files simultaneously

## Challenges and Learning Points

- **Atomic Operations:** Understanding file system operations that prevent race conditions in multi-worker environments
- **AI Response Parsing:** Handling unpredictable AI output formats with multiple parsing strategies and fallback mechanisms
- **Production Error Handling:** Building systems that gracefully handle failures without leaving corrupted state or orphaned files
- **Concurrent System Design:** Creating applications that can scale horizontally with multiple worker processes
- **Structured Data Extraction:** Using prompt engineering to consistently extract structured information from unstructured text
- **Performance Monitoring:** Implementing logging and metrics systems for production monitoring and debugging
- **API Integration Patterns:** Working with external AI services including authentication, error handling, and response processing

## Expected Outcome

You will create a production-ready AI processing pipeline that can handle real meeting transcripts, extract meaningful insights, and operate reliably in a multi-worker environment. The system will demonstrate enterprise-level practices including proper error handling, performance monitoring, and scalable architecture design.

## Additional Considerations

- Implement retry logic with exponential backoff for handling temporary API failures
- Add support for different transcript formats and speaker identification patterns
- Create health monitoring systems for tracking worker status and performance
- Extend the system to handle batch processing and priority queuing
- Add configuration management for different deployment environments
- Consider implementing async processing patterns for improved throughput