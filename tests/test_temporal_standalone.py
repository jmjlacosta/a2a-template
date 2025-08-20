#!/usr/bin/env python3
"""
Test script for temporal tagging agent standalone operation.
GITHUB ISSUE: Testing fixed tool signatures
"""

import json
import requests
import time

def test_temporal_extraction():
    """Test temporal extraction with simple medical text."""
    
    # Test data with clear dates
    test_message = """
    Extract temporal information from this medical record:
    
    Patient was diagnosed with cancer on January 15, 2024.
    Initial treatment started February 1, 2024.
    Follow-up scan performed March 10, 2024 showed improvement.
    Next appointment scheduled for April 15, 2024.
    """
    
    # A2A message format
    request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": "test-temporal-1",
                "role": "user",
                "parts": [{
                    "text": test_message
                }]
            }
        },
        "id": "test-1"
    }
    
    print("📤 Sending test request to temporal tagging agent...")
    print(f"Test message: {test_message[:100]}...")
    
    try:
        response = requests.post(
            "http://localhost:8010",
            json=request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Response received!")
            
            if "result" in result:
                # Extract the message content
                if "message" in result["result"]:
                    message = result["result"]["message"]
                    if "parts" in message:
                        for part in message["parts"]:
                            if "text" in part:
                                print("\n📋 Extracted temporal information:")
                                print(part["text"][:500])  # Print first 500 chars
                                
                                # Try to parse as JSON if it looks like JSON
                                try:
                                    if part["text"].strip().startswith("{"):
                                        parsed = json.loads(part["text"])
                                        print("\n🔍 Parsed JSON structure:")
                                        print(f"  - Encounter dates found: {len(parsed.get('encounter_dates', []))}")
                                        print(f"  - Text segments: {len(parsed.get('text_segments', []))}")
                                        if parsed.get('encounter_dates'):
                                            print(f"  - First date: {parsed['encounter_dates'][0]}")
                                except:
                                    pass
                            elif "data" in part:
                                print("\n📊 Received data part:")
                                print(json.dumps(part["data"], indent=2)[:500])
            elif "error" in result:
                print(f"\n❌ Error: {result['error']}")
        else:
            print(f"\n❌ HTTP Error {response.status_code}")
            print(response.text[:500])
            
    except requests.exceptions.Timeout:
        print("\n⏱️ Request timed out after 30 seconds")
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to agent at http://localhost:8010")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Temporal Tagging Agent with Fixed Tools")
    print("=" * 50)
    test_temporal_extraction()
    print("\n" + "=" * 50)
    print("✅ Test complete")