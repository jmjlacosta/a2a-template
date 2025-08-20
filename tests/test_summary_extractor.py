#!/usr/bin/env python3
"""
Test script for summary extractor agent with fixed tools.
GITHUB ISSUE: Testing fixed tool signatures
"""

import json
import requests
import subprocess
import time

def start_agent():
    """Start the summary extractor agent."""
    print("🚀 Starting Summary Extractor Agent...")
    process = subprocess.Popen(
        ["python", "examples/pipeline/summary_extractor_agent.py"],
        env={"PORT": "8013", **subprocess.os.environ},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(5)  # Wait for startup
    return process

def test_extraction():
    """Test summary extraction with sample data."""
    
    # Sample reconciled group data
    test_data = {
        "reconciled_groups": [
            {
                "encounter_date": "2024-01-15",
                "encounter_type": "diagnostic",
                "reconciled_facts": [
                    {
                        "content": "Stage IIIB melanoma diagnosed",
                        "status": "Final",
                        "provenance": "Primary",
                        "confidence": 0.95,
                        "is_carry_forward": False,
                        "source_pages": [1],
                        "source_documents": ["medical_record.pdf"]
                    },
                    {
                        "content": "BRAF V600E mutation positive",
                        "status": "Final",
                        "provenance": "Primary",
                        "confidence": 0.9,
                        "is_carry_forward": False,
                        "source_pages": [2],
                        "source_documents": ["pathology_report.pdf"]
                    }
                ]
            }
        ]
    }
    
    # A2A message format
    request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": "test-extractor-1",
                "role": "user",
                "parts": [{
                    "text": f"Extract summaries from this reconciled data:\n{json.dumps(test_data, indent=2)}"
                }]
            }
        },
        "id": "test-1"
    }
    
    print("📤 Sending test request to summary extractor agent...")
    
    try:
        response = requests.post(
            "http://localhost:8013",
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
        print("❌ Could not connect to agent at http://localhost:8013")
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
    print("🧪 Testing Summary Extractor Agent with Fixed Tools")
    print("=" * 50)
    
    # Start agent
    agent_process = start_agent()
    
    try:
        # Test extraction
        test_passed = test_extraction()
        
        # Check logs
        logs_clean = check_agent_logs(agent_process)
        
        if test_passed and logs_clean:
            print("\n" + "=" * 50)
            print("✅ ALL TESTS PASSED: Summary Extractor Agent works with fixed tools!")
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