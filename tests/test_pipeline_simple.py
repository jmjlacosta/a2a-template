#!/usr/bin/env python3
"""
Simple pipeline test - assumes agents are already running
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils.a2a_client import A2AAgentClient

TEST_DOC = """
PATIENT: Eleanor Richardson
DATE: March 15, 2024
DIAGNOSIS: Stage IIIB melanoma
TREATMENT: Pembrolizumab 200mg IV q3 weeks
"""

async def test():
    print("🔬 TESTING BASIC PIPELINE\n")
    
    # Step 1: Keyword
    print("1️⃣ Keyword Agent")
    async with A2AAgentClient(timeout=30) as client:
        keyword_resp = await client.call_agent(
            "http://localhost:8001",
            f"Generate patterns for: {TEST_DOC}"
        )
        print(f"   ✅ Got {len(keyword_resp)} chars\n")
    
    # Step 2: Grep
    print("2️⃣ Grep Agent")
    grep_msg = json.dumps({
        "patterns": ["melanoma", "Stage", "Pembrolizumab"],
        "document_content": TEST_DOC,
        "case_sensitive": False
    })
    async with A2AAgentClient(timeout=30) as client:
        grep_resp = await client.call_agent("http://localhost:8002", grep_msg)
        print(f"   ✅ Got {len(grep_resp)} chars\n")
    
    # Step 3: Chunk
    print("3️⃣ Chunk Agent")
    chunk_msg = json.dumps({
        "match_info": {"line_number": 4, "text": "DIAGNOSIS: Stage IIIB melanoma"},
        "lines_before": 1,
        "lines_after": 1,
        "document_content": TEST_DOC
    })
    async with A2AAgentClient(timeout=30) as client:
        chunk_resp = await client.call_agent("http://localhost:8003", chunk_msg)
        print(f"   ✅ Got {len(chunk_resp)} chars\n")
    
    # Step 4: Summarize
    print("4️⃣ Summarize Agent")
    summary_msg = json.dumps({
        "chunk_content": chunk_resp,
        "chunk_metadata": {"source": "test"},
        "summary_style": "clinical"
    })
    async with A2AAgentClient(timeout=30) as client:
        summary = await client.call_agent("http://localhost:8004", summary_msg)
        print(f"   ✅ Got {len(summary)} chars\n")
    
    print("="*50)
    print("📊 FINAL SUMMARY:")
    print(summary[:500])
    print("="*50)

if __name__ == "__main__":
    asyncio.run(test())