#!/usr/bin/env python3
"""
Test script for reconciliation_agent_hybrid
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

async def test_reconciliation_agent():
    """Test the reconciliation agent."""
    
    print("🧪 TESTING RECONCILIATION AGENT")
    print("="*60)
    
    try:
        from utils.a2a_client import A2AAgentClient
        
        # Sample clinical data with duplicates and conflicts
        test_data = {
            "patient_id": "P12345",
            "encounters": [
                {
                    "date": "2024-01-15",
                    "facts": [
                        {"content": "Blood pressure 140/90", "source": "Vital Signs"},
                        {"content": "Patient has hypertension", "source": "Assessment"},
                        {"content": "Started on lisinopril 10mg", "source": "Treatment"},
                        {"content": "Blood pressure elevated at 140/90", "source": "Notes"}
                    ]
                },
                {
                    "date": "2024-02-15", 
                    "facts": [
                        {"content": "Blood pressure 130/85", "source": "Vital Signs"},
                        {"content": "Hypertension improving", "source": "Assessment"},
                        {"content": "Continue lisinopril 10mg", "source": "Treatment"},
                        {"content": "Patient has hypertension", "source": "History"}
                    ]
                }
            ]
        }
        
        test_message = json.dumps(test_data, indent=2)
        
        async with A2AAgentClient(timeout=60) as client:
            print("Sending test message with clinical data containing duplicates...")
            response = await client.call_agent("http://localhost:8012", test_message)
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
    print("RECONCILIATION AGENT TEST")
    print("="*60)
    print(f"OpenAI API Key present: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
    print("="*60 + "\n")
    
    asyncio.run(test_reconciliation_agent())