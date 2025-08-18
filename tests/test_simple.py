#!/usr/bin/env python3
"""
Simple test with shorter text for faster orchestrator response.
"""

import asyncio
import json
import logging
import uuid
import httpx

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set specific loggers
logging.getLogger("OrchestratorAgent").setLevel(logging.INFO)
logging.getLogger("utils.a2a_client").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.WARNING)

async def test_orchestrator_simple():
    """Test with simple, short message."""
    
    # Create JSON-RPC request with SHORT message
    request_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    
    # Much shorter test message
    test_message = """The patient has type 2 diabetes managed with metformin 1000mg twice daily. 
    Blood sugar levels are 140 mg/dL. HbA1c is 8.5%."""
    
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
                        "text": test_message
                    }
                ]
            }
        },
        "id": request_id
    }
    
    orchestrator_url = "http://localhost:8006/"
    
    print("="*80)
    print("🚀 SIMPLE ORCHESTRATOR TEST")
    print("="*80)
    print(f"\n📝 Short Test Message:")
    print(f"   {test_message}")
    print("\n" + "="*80)
    print("📡 WATCHING FOR INTER-AGENT COMMUNICATION...")
    print("="*80 + "\n")
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(
                orchestrator_url, 
                json=jsonrpc_request,
                headers={"Content-Type": "application/json"}
            )
            
            print("\n" + "="*80)
            print("✅ ORCHESTRATOR RESPONSE:")
            print("="*80)
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract text from response
                if "result" in result and "artifacts" in result["result"]:
                    artifacts = result["result"]["artifacts"]
                    if artifacts and len(artifacts) > 0:
                        artifact = artifacts[0]
                        if "parts" in artifact and len(artifact["parts"]) > 0:
                            text = artifact["parts"][0].get("text", "No text")
                            print(f"\n{text[:1000]}..." if len(text) > 1000 else f"\n{text}")
                else:
                    print(json.dumps(result, indent=2)[:500])
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                
        except asyncio.TimeoutError:
            print("❌ Request timed out after 180 seconds")
            print("The orchestrator is taking too long to process.")
            print("\nPossible reasons:")
            print("- LLM API is slow")
            print("- Text is too complex")
            print("- Network issues")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("\n⚠️  Using SHORT text for faster response")
    print("   This should complete in 30-60 seconds\n")
    
    asyncio.run(test_orchestrator_simple())