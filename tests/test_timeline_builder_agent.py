#!/usr/bin/env python3
"""
Test script for timeline_builder_agent
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

async def test_timeline_builder():
    """Test the timeline builder agent."""
    
    print("🧪 TESTING TIMELINE BUILDER AGENT")
    print("="*60)
    
    try:
        from utils.a2a_client import A2AAgentClient
        
        # Sample medical events for timeline building
        test_data = {
            "patient_id": "P67890",
            "events": [
                {
                    "date": "2023-06-15",
                    "type": "diagnosis",
                    "content": "Initial diagnosis of Type 2 diabetes",
                    "severity": "moderate"
                },
                {
                    "date": "2023-06-20",
                    "type": "medication",
                    "content": "Started on metformin 500mg twice daily",
                    "related_to": "diabetes_management"
                },
                {
                    "date": "2023-09-15",
                    "type": "lab_result",
                    "content": "HbA1c 8.2% (elevated)",
                    "related_to": "diabetes_monitoring"
                },
                {
                    "date": "2023-09-20",
                    "type": "medication_change",
                    "content": "Increased metformin to 1000mg twice daily",
                    "related_to": "diabetes_management"
                },
                {
                    "date": "2023-12-15",
                    "type": "lab_result",
                    "content": "HbA1c 7.1% (improved)",
                    "related_to": "diabetes_monitoring"
                },
                {
                    "date": "2024-03-15",
                    "type": "follow_up",
                    "content": "Routine diabetes follow-up, good control",
                    "related_to": "diabetes_management"
                }
            ]
        }
        
        test_message = f"""Build a chronological timeline for this patient's medical events:

{json.dumps(test_data, indent=2)}

Please create a comprehensive timeline that:
1. Orders events chronologically
2. Links related events
3. Identifies patterns and trends
4. Highlights critical events
5. Shows progression of treatment"""
        
        async with A2AAgentClient(timeout=60) as client:
            print("Sending test message with medical events...")
            response = await client.call_agent("http://localhost:8014", test_message)
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
    print("TIMELINE BUILDER AGENT TEST")
    print("="*60)
    print(f"OpenAI API Key present: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
    print("="*60 + "\n")
    
    asyncio.run(test_timeline_builder())