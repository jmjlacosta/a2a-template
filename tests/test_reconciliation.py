#!/usr/bin/env python3
"""Test reconciliation agent with proper format."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils.a2a_client import A2AAgentClient


async def test_reconciliation():
    """Test the reconciliation agent."""
    
    # Simple plain text message
    simple_message = """Please reconcile the following clinical information:
    
Encounter Date: January 2024 - March 2024
Clinical Content: Ms. Richardson is a 68-year-old female with Stage IIIB melanoma diagnosed in January 2024. 
She completed her third cycle of pembrolizumab (Keytruda) on March 1, 2024.

Temporal Information: 
- Diagnosis Date: January 2024 (Stage IIIB melanoma)
- Treatment Date: March 1, 2024 (third cycle of pembrolizumab)

Encounter Information:
- March 1, 2024: Treatment visit for pembrolizumab administration
- January 2024: Initial diagnosis visit

Please identify any conflicting information, duplicates, or carry-forward notes and reconcile them."""

    print("Testing reconciliation agent at http://localhost:8012")
    print("="*60)
    print("Message being sent:")
    print(simple_message)
    print("="*60)
    
    try:
        async with A2AAgentClient(timeout=60) as client:
            print("Calling reconciliation agent...")
            response = await client.call_agent("http://localhost:8012", simple_message)
            print("\nResponse received:")
            print("-"*40)
            print(response[:1000] if len(response) > 1000 else response)
            print("-"*40)
            return response
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    # Test the reconciliation agent
    print("Testing reconciliation agent...")
    print()
    
    result = asyncio.run(test_reconciliation())
    if result:
        print("\n✅ Test successful!")
    else:
        print("\n❌ Test failed!")