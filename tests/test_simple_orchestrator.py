#!/usr/bin/env python3
"""
Simple test for orchestrator with a basic message.
"""

import asyncio
import json
import httpx
import uuid

async def test_orchestrator():
    """Test the orchestrator with a simple message."""
    
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
                        "kind": "text",
                        "text": "Test the pipeline by finding the word 'diabetes' in this text: The patient has type 2 diabetes mellitus."
                    }
                ]
            }
        },
        "id": request_id
    }
    
    orchestrator_url = "http://localhost:8006/"
    
    print("🚀 Sending simple test to orchestrator...")
    print("-" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                orchestrator_url, 
                json=jsonrpc_request,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Response received:")
                print(json.dumps(result, indent=2)[:1000])
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())