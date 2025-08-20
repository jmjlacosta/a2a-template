#!/usr/bin/env python3
"""
Test the grep agent directly to see what error occurs.
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

async def test_grep():
    """Test grep agent directly."""
    print("="*60)
    print("Testing Grep Agent Directly")
    print("="*60)
    
    patterns = ["diabetes", "medication", "BP", "mg"]
    
    # Test with JSON message (as orchestrator sends)
    grep_message = json.dumps({
        "patterns": patterns,
        "document_content": TEST_DOCUMENT,
        "case_sensitive": False
    })
    
    print(f"\nSending JSON message to grep agent:")
    print(f"Message: {grep_message[:200]}...")
    
    try:
        async with A2AAgentClient(timeout=30.0) as client:
            response = await client.call_agent(
                "http://localhost:8003",
                grep_message
            )
        
        print(f"\n✓ Success! Response:")
        print(response[:500])
        
        # Try to parse response
        try:
            data = json.loads(response)
            print(f"\nParsed response:")
            print(f"- Total patterns: {data.get('summary', {}).get('total_patterns', 0)}")
            print(f"- Successful searches: {data.get('summary', {}).get('successful_searches', 0)}")
            print(f"- Total matches: {data.get('summary', {}).get('total_matches', 0)}")
        except:
            print("\nCouldn't parse as JSON")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_grep())