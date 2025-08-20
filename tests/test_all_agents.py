#!/usr/bin/env python3
"""
Test script to confirm functionality of all fixed agents.
GITHUB ISSUE: Verifying all agents work with fixed tool signatures
"""

import json
import requests
import subprocess
import time
import sys

def start_agent(name, port, file_path):
    """Start an agent and return the process."""
    print(f"🚀 Starting {name} on port {port}...")
    process = subprocess.Popen(
        ["python", file_path],
        env={"PORT": str(port), **subprocess.os.environ},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(8)  # Wait for startup
    return process

def test_agent(name, port, test_message):
    """Test an agent with a message and check response."""
    request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": f"test-{name}-1",
                "role": "user",
                "parts": [{
                    "text": test_message
                }]
            }
        },
        "id": "test-1"
    }
    
    try:
        response = requests.post(
            f"http://localhost:{port}",
            json=request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                return True, "Success - Agent responded"
            elif "error" in result:
                error_msg = str(result.get('error', ''))
                if "validation error" in error_msg.lower():
                    return False, "TOOL SIGNATURE ERROR"
                elif "default value" in error_msg.lower():
                    return False, "DEFAULT VALUE ERROR"
                else:
                    return False, f"Error: {error_msg[:100]}"
        else:
            return False, f"HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return False, "Timeout (30s)"
    except requests.exceptions.ConnectionError:
        return False, "Connection failed"
    except Exception as e:
        return False, f"Exception: {str(e)[:50]}"

def check_agent_logs(process, name):
    """Check for errors in agent logs."""
    import select
    errors = []
    warnings = []
    
    # Check stderr for errors/warnings
    if select.select([process.stderr], [], [], 0)[0]:
        stderr_output = process.stderr.read(2000).decode('utf-8', errors='ignore')
        
        if "Default value is not supported" in stderr_output:
            warnings.append("Default value warning")
        if "validation error" in stderr_output.lower():
            errors.append("Validation error")
        if "error" in stderr_output.lower() and "INFO" not in stderr_output:
            # Extract actual error messages
            for line in stderr_output.split('\n'):
                if 'error' in line.lower() and 'INFO' not in line:
                    errors.append(line.strip()[:100])
    
    return errors, warnings

def main():
    print("=" * 80)
    print("🧪 TESTING ALL FIXED AGENTS")
    print("=" * 80)
    
    # Define all agents to test with their fixed versions
    agents = [
        {
            "name": "temporal_tagging",
            "port": 8010,
            "file": "examples/pipeline/temporal_tagging_agent.py",
            "test_message": "Extract temporal information from: Patient diagnosed January 2024, treated March 2024."
        },
        {
            "name": "reconciliation",
            "port": 8012,
            "file": "examples/pipeline/reconciliation_agent_hybrid.py",
            "test_message": "Reconcile this clinical data: Patient has Stage IIIB melanoma diagnosed January 2024."
        },
        {
            "name": "timeline_builder",
            "port": 8014,
            "file": "examples/pipeline/timeline_builder_agent.py",
            "test_message": json.dumps({
                "action": "build_timeline",
                "facts": ["Diagnosed January 2024", "Treatment started March 2024"],
                "instructions": "Build a timeline"
            })
        },
        {
            "name": "summary_extractor",
            "port": 8013,
            "file": "examples/pipeline/summary_extractor_agent.py",
            "test_message": json.dumps({
                "reconciled_groups": [{"date": "2024-01", "facts": ["Stage IIIB melanoma"]}],
                "extract": "summary"
            })
        },
        {
            "name": "unified_verifier",
            "port": 8017,
            "file": "examples/pipeline/unified_verifier_agent.py",
            "test_message": json.dumps({
                "data_to_verify": {"diagnosis": "melanoma", "stage": "IIIB"},
                "verify": "accuracy"
            })
        },
        {
            "name": "checker",
            "port": 8015,
            "file": "examples/pipeline/checker_agent.py",
            "test_message": "Verify summary: Patient has melanoma. Source: Stage IIIB melanoma diagnosed."
        }
    ]
    
    results = []
    
    for agent in agents:
        print(f"\n{'='*60}")
        print(f"📍 Testing: {agent['name'].upper()}")
        print(f"{'='*60}")
        
        # Start agent
        process = start_agent(agent['name'], agent['port'], agent['file'])
        
        try:
            # Test agent
            print(f"📤 Sending test message...")
            success, message = test_agent(agent['name'], agent['port'], agent['test_message'])
            
            # Check logs
            errors, warnings = check_agent_logs(process, agent['name'])
            
            # Determine status
            if success and not errors:
                status = "✅ WORKING"
                details = "No errors, tools executing correctly"
            elif errors:
                status = "❌ ERRORS"
                details = f"Errors: {', '.join(errors[:2])}"
            elif warnings:
                status = "⚠️ WARNINGS"
                details = f"Warnings: {', '.join(warnings[:2])}"
            else:
                status = "❌ FAILED"
                details = message
            
            results.append({
                "agent": agent['name'],
                "status": status,
                "details": details,
                "response": message,
                "errors": errors,
                "warnings": warnings
            })
            
            print(f"Status: {status}")
            print(f"Details: {details}")
            
        finally:
            # Stop agent
            print(f"🛑 Stopping {agent['name']}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except:
                process.kill()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY REPORT")
    print("=" * 80)
    
    working = sum(1 for r in results if "✅" in r['status'])
    total = len(results)
    
    print(f"\n✅ Working: {working}/{total}")
    print(f"❌ Failed: {total - working}/{total}")
    
    print("\nDETAILED RESULTS:")
    print("-" * 60)
    for r in results:
        print(f"{r['status']} {r['agent']:20} - {r['details']}")
    
    if working == total:
        print("\n" + "🎉" * 20)
        print("ALL AGENTS ARE WORKING CORRECTLY!")
        print("🎉" * 20)
    else:
        print("\n⚠️ Some agents have issues. Check details above.")
    
    return working == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)