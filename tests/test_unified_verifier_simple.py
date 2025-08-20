#!/usr/bin/env python3
"""
Simple test for unified_verifier_agent
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Make sure we have the API key
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

async def test_unified_verifier_simple():
    """Test the unified verifier agent with simple data."""
    
    print("🧪 TESTING UNIFIED VERIFIER AGENT (SIMPLE)")
    print("="*60)
    
    try:
        from utils.a2a_client import A2AAgentClient
        
        test_message = """Verify this simple medical data:

Patient: Test Patient
Diagnosis: Common cold
Treatment: Rest and fluids
Date: 2024-01-15

Please verify this information for accuracy."""
        
        async with A2AAgentClient(timeout=30) as client:
            print("Sending simple test message...")
            response = await client.call_agent("http://localhost:8017", test_message)
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
    asyncio.run(test_unified_verifier_simple())