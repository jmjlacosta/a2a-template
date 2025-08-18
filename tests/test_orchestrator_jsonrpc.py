#!/usr/bin/env python3
"""
Test script for the orchestrator agent using JSON-RPC format.
"""

import asyncio
import json
import httpx
import uuid

async def test_orchestrator():
    """Test the orchestrator with medical text using JSON-RPC."""
    
    # Read the test medical text
    with open('test.txt', 'r') as f:
        medical_text = f.read()
    
    # Create JSON-RPC request following A2A spec
    request_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    jsonrpc_request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": message_id,
                "role": "user",
                "parts": [
                    {
                        "text": f"Analyze this medical record and provide information about the patient's cardiac condition and medications:\n\n{medical_text}"
                    }
                ]
            }
        },
        "id": request_id
    }
    
    orchestrator_url = "http://localhost:8006/"
    
    print("🚀 Sending JSON-RPC request to orchestrator...")
    print(f"📋 Request: Analyze cardiac condition and medications")
    print(f"📄 Document length: {len(medical_text)} characters")
    print("-" * 60)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                orchestrator_url, 
                json=jsonrpc_request,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Response received from orchestrator:")
                if "result" in result:
                    print(f"Result: {result['result'][:500]}..." if len(str(result['result'])) > 500 else f"Result: {result['result']}")
                elif "error" in result:
                    print(f"❌ Error: {result['error']}")
                else:
                    print(json.dumps(result, indent=2))
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ Error calling orchestrator: {e}")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())