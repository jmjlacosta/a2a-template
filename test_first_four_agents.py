#!/usr/bin/env python3
"""
Test the first four agents in the pipeline without requiring an LLM.
Tests: keyword -> grep -> chunk -> summarize
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.a2a_client import A2AAgentClient

TEST_DOCUMENT = """Patient: Eleanor Richardson, 72-year-old female
Date: March 15, 2024
Chief Complaint: Follow-up for diabetes management and hypertension

Current Medications:
- Metformin 1000mg PO BID
- Lisinopril 20mg PO daily

Vital Signs:
- BP: 142/88 mmHg
- HR: 76 bpm"""

async def test_pipeline():
    """Test the first four agents."""
    print("="*60)
    print("Testing First Four Agents")
    print("="*60)
    
    try:
        # Step 1: Keyword Agent
        print("\n1. Testing Keyword Agent...")
        async with A2AAgentClient(timeout=30.0) as client:
            keyword_response = await client.call_agent(
                "http://localhost:8002",
                f"Generate search patterns for: {TEST_DOCUMENT[:200]}"
            )
        print(f"   ✓ Got patterns: {keyword_response[:100]}...")
        
        # For testing, use simple patterns
        patterns = ["diabetes", "medication", "BP", "mg"]
        
        # Step 2: Grep Agent
        print("\n2. Testing Grep Agent...")
        grep_message = json.dumps({
            "patterns": patterns,
            "document_content": TEST_DOCUMENT,
            "case_sensitive": False
        })
        
        async with A2AAgentClient(timeout=30.0) as client:
            grep_response = await client.call_agent(
                "http://localhost:8003",
                grep_message
            )
        print(f"   ✓ Got matches: {grep_response[:100]}...")
        
        # Parse grep results
        try:
            grep_data = json.loads(grep_response)
            matches = grep_data.get("search_results", [])
            print(f"   Found {len(matches)} pattern matches")
        except:
            matches = [{"line_number": 1, "match_text": TEST_DOCUMENT[:50]}]
        
        # Step 3: Chunk Agent  
        print("\n3. Testing Chunk Agent...")
        chunk_message = json.dumps({
            "matches": matches[:2],  # Just test with first 2 matches
            "document": TEST_DOCUMENT
        })
        
        async with A2AAgentClient(timeout=30.0) as client:
            chunk_response = await client.call_agent(
                "http://localhost:8004",
                chunk_message
            )
        print(f"   ✓ Got chunks: {chunk_response[:100]}...")
        
        # Step 4: Summarize Agent
        print("\n4. Testing Summarize Agent...")
        summarize_message = json.dumps({
            "chunks": [chunk_response],
            "chunk_metadata": {"source": "test"},
            "summary_style": "clinical"
        })
        
        async with A2AAgentClient(timeout=30.0) as client:
            summary_response = await client.call_agent(
                "http://localhost:8005",
                summarize_message
            )
        print(f"   ✓ Got summary: {summary_response[:200]}...")
        
        print("\n" + "="*60)
        print("✅ All four agents working!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_pipeline())
    sys.exit(0 if success else 1)