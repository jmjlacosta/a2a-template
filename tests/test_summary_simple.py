#!/usr/bin/env python3
"""
Simple test for summary_extractor_agent
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Make sure we have the API key
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

async def test_summary_simple():
    """Test the summary extractor agent with a simple message."""
    
    print("🧪 TESTING SUMMARY EXTRACTOR AGENT (SIMPLE)")
    print("="*60)
    
    try:
        from utils.a2a_client import A2AAgentClient
        
        test_message = """Extract a summary from this simple medical note:

Patient: John Doe
Age: 45
Chief complaint: Headache
Diagnosis: Tension headache
Treatment: Acetaminophen 500mg
Outcome: Pain resolved

Please extract the key findings."""
        
        async with A2AAgentClient(timeout=30) as client:
            print("Sending simple test message...")
            response = await client.call_agent("http://localhost:8013", test_message)
            print(f"✅ Response received: {len(response)} characters")
            print("\nResponse:")
            print("-"*40)
            print(response)
            print("-"*40)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_summary_simple())