#!/usr/bin/env python3
"""
Test script for checker_agent
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Make sure we have the API key
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

async def test_checker_agent():
    """Test the checker agent."""
    
    print("🧪 TESTING CHECKER AGENT")
    print("="*60)
    
    try:
        from utils.a2a_client import A2AAgentClient
        
        test_message = """Check this medical information for accuracy and consistency:

PATIENT: Alice Brown
AGE: 55
DATE: 2024-01-15

TIMELINE:
1. 2024-01-10: Initial consultation for chest pain
2. 2024-01-12: EKG shows normal sinus rhythm
3. 2024-01-15: Stress test scheduled
4. 2024-01-08: Patient reports chest pain started 2 days ago

DIAGNOSES:
- Chest pain of unknown origin
- Rule out cardiac etiology

MEDICATIONS:
- Aspirin 81mg daily (started 2024-01-10)
- Metoprolol 25mg twice daily

NOTES:
- Patient has no cardiac history
- Family history of heart disease
- EKG normal but stress test pending

Please verify:
1. Factual accuracy
2. Logical consistency
3. Temporal sequence correctness
4. Identify any inconsistencies or errors"""
        
        async with A2AAgentClient(timeout=45) as client:
            print("Sending test message with medical data for checking...")
            response = await client.call_agent("http://localhost:8015", test_message)
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
    print("CHECKER AGENT TEST")
    print("="*60)
    print(f"OpenAI API Key present: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
    print("="*60 + "\n")
    
    asyncio.run(test_checker_agent())