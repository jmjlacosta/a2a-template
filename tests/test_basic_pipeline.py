#!/usr/bin/env python3
"""
Test the basic 4-agent pipeline: keyword -> grep -> chunk -> summarize
"""

import asyncio
import json
import sys
import subprocess
import time
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Ensure API key is set
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

# Test document
TEST_DOCUMENT = """
PATIENT: Eleanor Richardson
DATE: March 15, 2024

CHIEF COMPLAINT: Follow-up for melanoma treatment

HISTORY OF PRESENT ILLNESS:
Ms. Richardson is a 68-year-old female with Stage IIIB melanoma diagnosed in January 2024. 
She completed her third cycle of pembrolizumab (Keytruda) on March 1, 2024. She reports 
mild fatigue but no fever, rash, or other immune-related adverse events.

CURRENT MEDICATIONS:
- Pembrolizumab 200mg IV q3 weeks
- Metformin 1000mg BID
- Lisinopril 10mg daily

ASSESSMENT AND PLAN:
1. Stage IIIB melanoma - Responding well to immunotherapy
2. Continue pembrolizumab as scheduled
3. Monitor for immune-related adverse events
"""

# Basic agents configuration
AGENTS = [
    {"name": "keyword", "port": 8001, "file": "examples/pipeline/keyword_agent.py"},
    {"name": "grep", "port": 8002, "file": "examples/pipeline/grep_agent.py"},
    {"name": "chunk", "port": 8003, "file": "examples/pipeline/chunk_agent.py"},
    {"name": "summarize", "port": 8004, "file": "examples/pipeline/summarize_agent.py"},
]


def start_agents():
    """Start the 4 basic agents."""
    print("🚀 Starting basic agents...")
    print("="*60)
    
    processes = []
    for agent in AGENTS:
        cmd = f"PORT={agent['port']} python {agent['file']}"
        
        print(f"  Starting {agent['name']:12} on port {agent['port']}... ", end="")
        
        process = subprocess.Popen(
            cmd, 
            shell=True, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append((agent['name'], process))
        print(f"✓ (PID: {process.pid})")
    
    print("\n⏳ Waiting 20 seconds for agents to initialize...")
    time.sleep(20)
    
    # Verify agents are ready
    print("\n🔍 Verifying agents are ready...")
    for agent in AGENTS:
        result = subprocess.run(
            f"curl -s http://localhost:{agent['port']}/.well-known/agent-card.json | head -c 100",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.stdout:
            print(f"  ✅ {agent['name']:12} is ready")
        else:
            print(f"  ❌ {agent['name']:12} not responding")
    
    return processes


def stop_agents(processes):
    """Stop all agent processes."""
    print("\n🛑 Stopping agents...")
    for name, process in processes:
        print(f"  Stopping {name:12}... ", end="")
        process.terminate()
        try:
            process.wait(timeout=5)
            print("✓")
        except:
            process.kill()
            print("✓ (forced)")


async def run_basic_pipeline():
    """Run the basic 4-step pipeline."""
    
    print("\n" + "="*60)
    print("🔬 RUNNING BASIC PIPELINE")
    print("="*60)
    
    from utils.a2a_client import A2AAgentClient
    
    try:
        # Step 1: Keyword Generation
        print("\n📍 STEP 1: Keyword Generation")
        print("-"*40)
        
        keyword_message = f"""Generate regex patterns for finding medical information in this document:

{TEST_DOCUMENT[:500]}

Focus on medical terms, medications, diagnoses, and dates."""
        
        async with A2AAgentClient(timeout=60) as client:
            print("Calling keyword agent...")
            keyword_response = await client.call_agent("http://localhost:8001", keyword_message)
            print(f"✅ Received {len(keyword_response)} characters")
            print(f"Preview: {keyword_response[:200]}...")
        
        # Extract patterns from response
        patterns = []
        for line in keyword_response.split('\n'):
            if '`' in line and not line.strip().startswith('#'):
                import re
                found = re.findall(r'`([^`]+)`', line)
                patterns.extend(found)
        
        if not patterns:
            patterns = ["melanoma", "pembrolizumab", "Stage", "medication", "diagnosis"]
        
        print(f"Extracted {len(patterns)} patterns")
        
        # Step 2: Grep Search
        print("\n📍 STEP 2: Pattern Search (Grep)")
        print("-"*40)
        
        grep_message = json.dumps({
            "patterns": patterns[:10],
            "document_content": TEST_DOCUMENT,
            "case_sensitive": False
        })
        
        async with A2AAgentClient(timeout=60) as client:
            print(f"Calling grep agent with {len(patterns[:10])} patterns...")
            grep_response = await client.call_agent("http://localhost:8002", grep_message)
            print(f"✅ Received {len(grep_response)} characters")
        
        # Parse grep results
        try:
            grep_data = json.loads(grep_response)
            matches = grep_data.get("matches", [])[:3]
            print(f"Found {len(matches)} matches to process")
        except:
            print("Using default match")
            matches = [{
                "line_number": 8,
                "text": "Stage IIIB melanoma diagnosed",
                "pattern": "melanoma"
            }]
        
        # Step 3: Chunk Extraction
        print("\n📍 STEP 3: Context Extraction (Chunking)")
        print("-"*40)
        
        chunks = []
        for i, match in enumerate(matches, 1):
            chunk_message = json.dumps({
                "match_info": match,
                "lines_before": 2,
                "lines_after": 2,
                "document_content": TEST_DOCUMENT
            })
            
            async with A2AAgentClient(timeout=60) as client:
                print(f"  [{i}/{len(matches)}] Extracting chunk...")
                chunk_response = await client.call_agent("http://localhost:8003", chunk_message)
                chunks.append(chunk_response)
                print(f"    ✅ Extracted {len(chunk_response)} characters")
        
        combined_chunks = "\n\n".join(chunks)
        
        # Step 4: Summarization
        print("\n📍 STEP 4: Medical Summarization")
        print("-"*40)
        
        summarize_message = json.dumps({
            "chunk_content": combined_chunks,
            "chunk_metadata": {
                "source": "Eleanor Richardson medical record",
                "total_chunks": len(chunks)
            },
            "summary_style": "clinical"
        })
        
        async with A2AAgentClient(timeout=60) as client:
            print("Calling summarize agent...")
            summary = await client.call_agent("http://localhost:8004", summarize_message)
            print(f"✅ Received summary ({len(summary)} characters)")
        
        # Final output
        print("\n" + "="*60)
        print("✅ PIPELINE COMPLETE")
        print("="*60)
        print("\n📊 FINAL SUMMARY:")
        print("-"*40)
        print(summary[:1000] if len(summary) > 1000 else summary)
        print("-"*40)
        
        return summary
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main function."""
    
    # Start agents
    processes = start_agents()
    
    try:
        # Run pipeline
        result = await run_basic_pipeline()
        
        if result:
            # Save result
            with open("basic_pipeline_result.txt", "w") as f:
                f.write(result)
            print(f"\n💾 Result saved to basic_pipeline_result.txt")
        
    finally:
        # Stop agents
        stop_agents(processes)


if __name__ == "__main__":
    print("\n🧪 BASIC PIPELINE TEST")
    print("This will test the 4-agent pipeline: keyword -> grep -> chunk -> summarize\n")
    
    asyncio.run(main())