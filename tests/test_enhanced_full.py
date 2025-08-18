#!/usr/bin/env python3
"""
Test the enhanced orchestrator with full test.txt to see inter-agent communication.
"""

import asyncio
import json
import uuid
import httpx

async def test_enhanced_orchestrator():
    """Test with the full test.txt content."""
    
    # Read test.txt
    with open("test.txt", "r") as f:
        test_content = f.read()
    
    # Create JSON-RPC request
    request_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    
    test_message = f"Please analyze this medical text using the keyword agent first:\n\n{test_content}"
    
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
    
    orchestrator_url = "http://localhost:8007/"
    
    print("="*80)
    print("🚀 TESTING ENHANCED ORCHESTRATOR WITH FULL TEST.TXT")
    print("="*80)
    print(f"\n📝 Document length: {len(test_content)} characters")
    print("\n⏳ Sending to enhanced orchestrator on port 8007...")
    print("\n🔍 WATCH THE ORCHESTRATOR CONSOLE FOR:")
    print("   📤 ORCHESTRATOR → KEYWORD AGENT")
    print("   📝 Message being sent to keyword agent")
    print("   📥 Response from keyword agent")
    print("="*80 + "\n")
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(
                orchestrator_url, 
                json=jsonrpc_request,
                headers={"Content-Type": "application/json"}
            )
            
            print("\n" + "="*80)
            print("✅ ENHANCED ORCHESTRATOR RESPONSE:")
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
                            print(f"\n{text[:1500]}..." if len(text) > 1500 else f"\n{text}")
                else:
                    print(json.dumps(result, indent=2)[:1000])
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                
        except asyncio.TimeoutError:
            print("❌ Request timed out after 180 seconds")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("📊 INTER-AGENT COMMUNICATION TEST")
    print("="*80)
    print("\nThis test sends the full test.txt to the enhanced orchestrator.")
    print("The enhanced orchestrator will log exactly what it sends to each agent.")
    print("\n⚠️  IMPORTANT: Watch the orchestrator console (bash_25) to see:")
    print("   - What message is sent to the keyword agent")
    print("   - What response comes back")
    print("   - Communication with other agents")
    print("="*80 + "\n")
    
    asyncio.run(test_enhanced_orchestrator())