#!/usr/bin/env python3
"""
Simple test to verify a single agent works correctly.
"""

import asyncio
import sys
import subprocess
import time
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Make sure we have the API key
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

async def test_keyword_agent():
    """Test the keyword agent directly."""
    
    print("🧪 TESTING KEYWORD AGENT")
    print("="*60)
    
    # Start the keyword agent
    print("Starting keyword agent on port 8001...")
    process = subprocess.Popen(
        "PORT=8001 python examples/pipeline/keyword_agent.py",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print(f"Agent started with PID: {process.pid}")
    print("Waiting 15 seconds for initialization...")
    time.sleep(15)
    
    # Test with curl first
    print("\n📍 Testing agent card endpoint...")
    result = subprocess.run(
        "curl -s http://localhost:8001/.well-known/agent-card.json",
        shell=True,
        capture_output=True,
        text=True,
        timeout=5
    )
    
    if result.returncode == 0 and result.stdout:
        print("✅ Agent card retrieved successfully")
        print(f"Response length: {len(result.stdout)} characters")
    else:
        print("❌ Failed to retrieve agent card")
        print(f"Error: {result.stderr}")
    
    # Now test with A2A client
    print("\n📍 Testing with A2A client...")
    
    try:
        from utils.a2a_client import A2AAgentClient
        
        test_message = """Generate regex patterns for finding medical information in this document:

PATIENT: Eleanor Richardson
DATE: March 15, 2024

CHIEF COMPLAINT: Follow-up for melanoma treatment

Generate comprehensive patterns for diagnosis, medications, and dates."""
        
        async with A2AAgentClient(timeout=60) as client:
            print("Sending test message...")
            response = await client.call_agent("http://localhost:8001", test_message)
            print(f"✅ Response received: {len(response)} characters")
            print("\nResponse preview:")
            print("-"*40)
            print(response[:500] + "..." if len(response) > 500 else response)
            print("-"*40)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Stop the agent
        print("\n🛑 Stopping agent...")
        process.terminate()
        process.wait(timeout=5)
        print("Agent stopped")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("SINGLE AGENT TEST")
    print("="*60)
    print(f"OpenAI API Key present: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
    print("="*60 + "\n")
    
    asyncio.run(test_keyword_agent())