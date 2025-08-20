#!/usr/bin/env python3
"""
Test script for checker agent with fixed tools.
GITHUB ISSUE: Testing fixed tool signatures
"""

import json
import requests
import subprocess
import time

def start_agent():
    """Start the checker agent."""
    print("🚀 Starting Checker Agent...")
    process = subprocess.Popen(
        ["python", "examples/pipeline/checker_agent.py"],
        env={"PORT": "8015", **subprocess.os.environ},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(5)  # Wait for startup
    return process

def test_verification():
    """Test verification with sample data."""
    
    # Sample data for verification
    test_data = {
        "summary": "Patient diagnosed with Stage IIIB melanoma in January 2024. BRAF V600E mutation positive. Currently on pembrolizumab treatment.",
        "source_text": """PATIENT: Eleanor Richardson
DATE: March 15, 2024

HISTORY OF PRESENT ILLNESS:
Ms. Richardson is a 68-year-old female with Stage IIIB melanoma diagnosed in January 2024. 
She completed her third cycle of pembrolizumab (Keytruda) on March 1, 2024. She reports 
mild fatigue but no fever, rash, or other immune-related adverse events.

PAST MEDICAL HISTORY:
- Stage IIIB melanoma (BRAF V600E positive), diagnosed January 2024
- Hypertension, controlled
- Type 2 diabetes mellitus""",
        "verification_mode": "comprehensive"
    }
    
    # A2A message format
    request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": "test-checker-1",
                "role": "user",
                "parts": [{
                    "text": f"Verify this summary against the source text:\n\nSummary: {test_data['summary']}\n\nSource: {test_data['source_text']}"
                }]
            }
        },
        "id": "test-1"
    }
    
    print("📤 Sending test request to checker agent...")
    
    try:
        response = requests.post(
            "http://localhost:8015",
            json=request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Response received!")
            
            if "result" in result:
                print("✅ SUCCESS: Agent responded without errors")
                
                # Check for any error indicators
                if "error" in result:
                    print(f"⚠️ Warning: {result['error']}")
                    return False
                
                return True
            elif "error" in result:
                print(f"❌ Error: {result['error']}")
                
                # Check if it's a tool signature error
                if "validation error" in str(result['error']).lower():
                    print("❌ TOOL SIGNATURE ERROR: Google ADK validation failed")
                elif "default value" in str(result['error']).lower():
                    print("❌ DEFAULT VALUE ERROR: Default parameters not supported")
                
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}")
            print(response.text[:500])
            return False
            
    except requests.exceptions.Timeout:
        print("⏱️ Request timed out after 30 seconds")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to agent at http://localhost:8015")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_agent_logs(process):
    """Check agent stderr for warnings."""
    print("\n📋 Checking agent logs for warnings...")
    
    # Give agent time to process
    time.sleep(2)
    
    # Read stderr (non-blocking)
    import select
    if select.select([process.stderr], [], [], 0)[0]:
        stderr_output = process.stderr.read(1000).decode('utf-8')
        
        if "Default value is not supported" in stderr_output:
            print("⚠️ Found 'Default value not supported' warnings")
            return False
        elif "error" in stderr_output.lower():
            print(f"⚠️ Found errors in logs: {stderr_output[:200]}")
            return False
        else:
            print("✅ No warnings or errors in agent logs")
            return True
    else:
        print("✅ No stderr output (good sign)")
        return True

def main():
    print("🧪 Testing Checker Agent with Fixed Tools")
    print("=" * 50)
    
    # Start agent
    agent_process = start_agent()
    
    try:
        # Test verification
        test_passed = test_verification()
        
        # Check logs
        logs_clean = check_agent_logs(agent_process)
        
        if test_passed and logs_clean:
            print("\n" + "=" * 50)
            print("✅ ALL TESTS PASSED: Checker Agent works with fixed tools!")
            print("- No validation errors")
            print("- No default value warnings")
            print("- Tools execute successfully")
        else:
            print("\n" + "=" * 50)
            print("❌ TESTS FAILED: Check the errors above")
            
    finally:
        # Clean up
        print("\n🛑 Stopping agent...")
        agent_process.terminate()
        agent_process.wait(timeout=5)
        print("✅ Agent stopped")

if __name__ == "__main__":
    main()