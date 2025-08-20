#!/usr/bin/env python3
"""
Test a single fixed agent to verify it works with proper A2A protocol.
"""

import asyncio
import json
import sys
import subprocess
import time
from pathlib import Path
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.a2a_client import A2AAgentClient

# Test document
TEST_DOCUMENT = """
PATIENT: John Doe
DATE: March 15, 2024

DIAGNOSIS: Stage IIIB melanoma
- Confirmed by biopsy on January 15, 2024
- BRAF V600E mutation positive

TREATMENT: 
- Pembrolizumab 200mg IV every 3 weeks
- Started February 1, 2024
"""

async def test_keyword_agent():
    """Test the keyword agent with proper A2A protocol."""
    
    print("🚀 Starting keyword agent...")
    
    # Start the agent
    process = subprocess.Popen(
        "PORT=8007 python examples/pipeline/keyword_agent.py",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for startup
    print("⏳ Waiting for agent to start...")
    time.sleep(5)
    
    try:
        # Test with A2A client
        async with A2AAgentClient(timeout=60) as client:
            print("📤 Sending test message...")
            
            message = f"""Generate comprehensive regex patterns for finding medical information in this document:

{TEST_DOCUMENT}

Focus on:
- Diagnosis and staging
- Treatment medications
- Dates and timelines
- Medical terms

Generate patterns that will help identify these elements."""
            
            response = await client.call_agent("http://localhost:8007", message)
            
            print("✅ Response received!")
            print("-" * 50)
            print(response[:1000] if len(response) > 1000 else response)
            print("-" * 50)
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Kill the agent
        process.terminate()
        process.wait(timeout=5)
        print("🛑 Agent stopped")


async def main():
    """Run the test."""
    print("=" * 60)
    print("TESTING FIXED KEYWORD AGENT")
    print("=" * 60)
    
    success = await test_keyword_agent()
    
    if success:
        print("\n✅ TEST PASSED - Agent is working correctly!")
    else:
        print("\n❌ TEST FAILED - Check the errors above")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)