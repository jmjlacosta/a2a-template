#!/usr/bin/env python3
"""
Test direct agent-to-agent communication.
"""

import asyncio
from utils.a2a_client import A2AAgentClient

async def test_direct_call():
    """Test calling keyword agent directly."""
    
    print("🚀 Testing direct agent call...")
    print("📍 Calling keyword agent at http://localhost:8002")
    print("-" * 60)
    
    async with A2AAgentClient() as client:
        try:
            # Call keyword agent with a simple request
            response = await client.call_agent(
                "http://localhost:8002",
                "Generate search patterns for finding diabetes information in medical records"
            )
            
            print("✅ Response from keyword agent:")
            print(response[:500] if len(response) > 500 else response)
            
        except Exception as e:
            print(f"❌ Error calling agent: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct_call())