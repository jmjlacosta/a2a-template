#!/usr/bin/env python3
"""
Explicit test that tells orchestrator to use the keyword agent.
"""

import asyncio
import json
import logging
import uuid
import httpx

# Configure detailed logging to see inter-agent communication
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_explicit_keyword_call():
    """Test with explicit instruction to use keyword agent."""
    
    # Create JSON-RPC request
    request_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    
    # Read test.txt content
    with open("test.txt", "r") as f:
        test_content = f.read()
    
    # Explicit instruction to use keyword agent
    test_message = f"""Please use the keyword agent to generate search patterns for finding medical information in this text, then tell me what search patterns it generated:

{test_content}"""
    
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
    print("🚀 EXPLICIT KEYWORD AGENT TEST")
    print("="*80)
    print("\n📝 Instruction: Use keyword agent to generate search patterns")
    print("\n⏳ Waiting for orchestrator to call keyword agent...")
    print("="*80 + "\n")
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            # Monitor the keyword agent in parallel
            keyword_monitor = asyncio.create_task(monitor_keyword_agent())
            
            # Send request to orchestrator
            response = await client.post(
                orchestrator_url, 
                json=jsonrpc_request,
                headers={"Content-Type": "application/json"}
            )
            
            # Cancel monitor
            keyword_monitor.cancel()
            
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
                            print(f"\n{text[:2000]}..." if len(text) > 2000 else f"\n{text}")
                else:
                    print(json.dumps(result, indent=2)[:1000])
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                
        except asyncio.TimeoutError:
            print("❌ Request timed out after 180 seconds")
        except Exception as e:
            print(f"❌ Error: {e}")

async def monitor_keyword_agent():
    """Monitor keyword agent for incoming requests."""
    print("👁️  Monitoring keyword agent for incoming requests...")
    
    # In a real implementation, this would tail the keyword agent's logs
    # For now, we'll just print periodic updates
    try:
        while True:
            await asyncio.sleep(5)
            print("   ... still waiting for keyword agent call ...")
    except asyncio.CancelledError:
        print("   Monitor stopped.")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("📊 TESTING WHAT ORCHESTRATOR SENDS TO KEYWORD AGENT")
    print("="*80)
    print("\nThis test explicitly asks the orchestrator to use the keyword agent.")
    print("Watch the console to see if/when the keyword agent is called.\n")
    
    asyncio.run(test_explicit_keyword_call())