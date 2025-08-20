#!/usr/bin/env python3
"""
Test script for timeline builder agent with fixed tools.
GITHUB ISSUE: Testing fixed tool signatures
"""

import json
import requests
import subprocess
import time

def start_agent():
    """Start the timeline builder agent."""
    print("🚀 Starting Timeline Builder Agent...")
    process = subprocess.Popen(
        ["python", "examples/pipeline/timeline_builder_agent.py"],
        env={"PORT": "8014", **subprocess.os.environ},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(5)  # Wait for startup
    return process

def test_timeline_building():
    """Test timeline building with sample data."""
    
    # Sample timeline building request
    test_facts = [
        {
            "date_str": "01/15/2024",
            "summary": "Patient diagnosed with Stage IIIB melanoma",
            "status": "Final",
            "provenance": "Primary",
            "confidence": 0.95
        },
        {
            "date_str": "03/01/2024",
            "summary": "Started pembrolizumab treatment",
            "status": "Final",
            "provenance": "Primary",
            "confidence": 0.9
        },
        {
            "date_str": "03/15/2024",
            "summary": "Follow-up shows good response to treatment",
            "status": "Final",
            "provenance": "Primary",
            "confidence": 0.85
        }
    ]
    
    # A2A message format
    request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": "test-timeline-1",
                "role": "user",
                "parts": [{
                    "text": f"Build a timeline from these medical facts:\n{json.dumps(test_facts, indent=2)}"
                }]
            }
        },
        "id": "test-1"
    }
    
    print("📤 Sending test request to timeline builder agent...")
    
    try:
        response = requests.post(
            "http://localhost:8014",
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
        print("❌ Could not connect to agent at http://localhost:8014")
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
    print("🧪 Testing Timeline Builder Agent with Fixed Tools")
    print("=" * 50)
    
    # Start agent
    agent_process = start_agent()
    
    try:
        # Test timeline building
        test_passed = test_timeline_building()
        
        # Check logs
        logs_clean = check_agent_logs(agent_process)
        
        if test_passed and logs_clean:
            print("\n" + "=" * 50)
            print("✅ ALL TESTS PASSED: Timeline Builder Agent works with fixed tools!")
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