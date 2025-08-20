#!/usr/bin/env python3
"""
Test script for unified_verifier_agent
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Make sure we have the API key
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

async def test_unified_verifier():
    """Test the unified verifier agent."""
    
    print("🧪 TESTING UNIFIED VERIFIER AGENT")
    print("="*60)
    
    try:
        from utils.a2a_client import A2AAgentClient
        
        # Sample processed medical data for verification
        test_data = {
            "patient_id": "P99999",
            "processed_data": {
                "temporal_extractions": [
                    {"date": "2024-01-15", "content": "Initial diagnosis of diabetes", "type": "diagnosis"},
                    {"date": "2024-01-20", "content": "Started metformin 500mg", "type": "medication"}
                ],
                "reconciled_facts": [
                    {"content": "Diabetes diagnosis", "status": "Final", "confidence": 0.95},
                    {"content": "Metformin treatment", "status": "Final", "confidence": 0.90}
                ],
                "timeline": [
                    {"date": "2024-01-15", "event": "Diabetes diagnosis"},
                    {"date": "2024-01-20", "event": "Medication started"}
                ],
                "summaries": {
                    "conditions": ["Type 2 Diabetes"],
                    "medications": ["Metformin 500mg"],
                    "outcomes": ["Treatment initiated"]
                }
            }
        }
        
        test_message = f"""Verify this processed medical data for accuracy and completeness:

{json.dumps(test_data, indent=2)}

Please perform comprehensive verification including:
1. Cross-check all extracted data
2. Validate medical logic
3. Ensure completeness
4. Check for contradictions
5. Generate confidence scores

Provide a verification report with any issues found."""
        
        async with A2AAgentClient(timeout=45) as client:
            print("Sending test message with processed medical data...")
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
    print("\n" + "="*60)
    print("UNIFIED VERIFIER AGENT TEST")
    print("="*60)
    print(f"OpenAI API Key present: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
    print("="*60 + "\n")
    
    asyncio.run(test_unified_verifier())