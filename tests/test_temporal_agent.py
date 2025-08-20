#!/usr/bin/env python3
"""
Test script for temporal_tagging_agent
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Make sure we have the API key
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

async def test_temporal_agent():
    """Test the temporal tagging agent."""
    
    print("🧪 TESTING TEMPORAL TAGGING AGENT")
    print("="*60)
    
    try:
        from utils.a2a_client import A2AAgentClient
        
        test_message = """Extract temporal information from this medical document:

PATIENT: John Smith
DATE OF SERVICE: March 15, 2024
REPORT DATE: March 16, 2024

CHIEF COMPLAINT: Follow-up for hypertension diagnosed 6 months ago

HISTORY: Patient was first seen on September 10, 2023 for elevated blood pressure. 
Laboratory work was done on September 12, 2023 showing normal kidney function.
Previous visit on February 1, 2024 showed improved BP control.
Patient reports taking medications consistently since last visit.

CURRENT VISIT: Blood pressure today 135/85. Will recheck in 3 months.
Next appointment scheduled for June 20, 2024.

Please extract and classify all temporal information including dates, temporal relationships, and event sequences."""
        
        async with A2AAgentClient(timeout=60) as client:
            print("Sending test message...")
            response = await client.call_agent("http://localhost:8010", test_message)
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
    print("\n" + "="*60)
    print("TEMPORAL AGENT TEST")
    print("="*60)
    print(f"OpenAI API Key present: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
    print("="*60 + "\n")
    
    asyncio.run(test_temporal_agent())