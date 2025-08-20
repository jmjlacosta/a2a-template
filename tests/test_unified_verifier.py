#\!/usr/bin/env python3
"""
Test script for unified_verifier_agent with complex data.
GITHUB ISSUE: Testing fixed tool signatures with complex JSON
"""

import json
import requests
import time

def test_complex_verification():
    """Test verification with complex nested data."""
    
    # Complex test data that previously failed
    complex_data = {
        "diagnoses": [
            {
                "date": "01/15/2024",
                "summary": "Stage IIIB melanoma diagnosed",
                "status": "confirmed",
                "sources": ["pathology_report.pdf"]
            }
        ],
        "treatments": [
            {
                "date": "03/01/2024",
                "summary": "Pembrolizumab started",
                "type": "immunotherapy"
            }
        ],
        "timeline": [
            {
                "date": "01/15/2024",
                "summary": "Initial diagnosis of Stage IIIB melanoma",
                "event_type": "diagnosis"
            },
            {
                "date": "03/01/2024",
                "summary": "Started pembrolizumab treatment",
                "event_type": "treatment"
            }
        ]
    }
    
    # Create proper A2A message
    message = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": "test-complex-1",
                "role": "user",
                "parts": [{
                    "text": f"Please verify this medical data comprehensively:\n{json.dumps(complex_data, indent=2)}"
                }]
            }
        },
        "id": "test-1"
    }
    
    print("📤 Sending complex verification request...")
    print(f"Data structure: {len(complex_data)} top-level keys")
    
    try:
        response = requests.post(
            "http://localhost:8017",
            json=message,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if "result" in result:
                # Check if there's an actual response
                if "artifacts" in result["result"]:
                    text = result["result"]["artifacts"][0]["parts"][0]["text"]
                    print("\n✅ SUCCESS: Verification completed")
                    print(f"Response preview: {text[:200]}...")
                    return True
                    
            if "error" in result:
                error_msg = result.get("error", {})
                print(f"\n❌ Error in response: {error_msg}")
                
                # Check for specific error patterns
                if "NoneType" in str(error_msg):
                    print("❌ FOUND THE ISSUE: NoneType error when processing complex data")
                    return False
                    
        else:
            print(f"❌ HTTP Error {response.status_code}")
            print(response.text[:500])
            return False
            
    except requests.exceptions.Timeout:
        print("⏱️ Request timed out - agent may be stuck processing")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    print("🧪 Testing Unified Verifier Agent with Complex Data")
    print("=" * 60)
    
    # Test complex nested data
    test_passed = test_complex_verification()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULT:")
    if test_passed:
        print("✅ Verifier handles complex data correctly\!")
    else:
        print("❌ Verifier has issues with complex data")

if __name__ == "__main__":
    main()
