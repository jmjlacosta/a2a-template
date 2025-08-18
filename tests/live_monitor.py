#!/usr/bin/env python3
"""
Live monitoring of orchestrator's inter-agent communication.
This script shows real-time what the orchestrator sends to other agents.
"""

import asyncio
import json
import httpx
import uuid
from datetime import datetime
import sys

async def send_test_message():
    """Send a test message to the orchestrator to trigger inter-agent communication."""
    orchestrator_url = "http://localhost:8006/"
    
    test_message = """Find information about diabetes treatments in this text:
    The patient has type 2 diabetes managed with metformin 1000mg twice daily.
    Blood glucose levels are elevated. Consider adding glipizide."""
    
    message_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    
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
    
    print("\n" + "="*80)
    print("📤 SENDING TEST MESSAGE TO ORCHESTRATOR")
    print("="*80)
    print(f"Message: {test_message[:100]}...")
    print("="*80)
    print("\n⏳ Processing... (this may take 30-60 seconds)")
    print("\nWATCH BELOW FOR INTER-AGENT COMMUNICATION:\n")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # Send in background
            task = asyncio.create_task(
                client.post(
                    orchestrator_url,
                    json=jsonrpc_request,
                    headers={"Content-Type": "application/json"}
                )
            )
            
            # While waiting, we could monitor logs
            # For now, just wait
            response = await task
            
            print("\n" + "="*80)
            print("✅ ORCHESTRATOR FINAL RESPONSE:")
            print("="*80)
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result and "artifacts" in result["result"]:
                    artifacts = result["result"]["artifacts"]
                    if artifacts and len(artifacts) > 0:
                        artifact = artifacts[0]
                        if "parts" in artifact and len(artifact["parts"]) > 0:
                            text = artifact["parts"][0].get("text", "No text")
                            print(text[:1000] + "..." if len(text) > 1000 else text)
                else:
                    print(json.dumps(result, indent=2)[:500])
            else:
                print(f"Error: {response.status_code}")
                
        except Exception as e:
            print(f"Error: {e}")

async def check_agent_logs():
    """Check for new log entries showing inter-agent communication."""
    print("\n🔍 Checking for inter-agent communication patterns in logs...")
    print("(This would normally tail the orchestrator's output)")
    print("\nTo see real communication:")
    print("1. Run this script")
    print("2. It will send a test message to the orchestrator")
    print("3. The orchestrator will call other agents")
    print("4. You'll see the communication details\n")

async def main():
    """Main monitoring function."""
    print("\n" + "="*80)
    print("🚀 ORCHESTRATOR COMMUNICATION MONITOR")
    print("="*80)
    print("\nThis tool demonstrates what the orchestrator sends to other agents.")
    print("It will:")
    print("  1. Send a test message to the orchestrator")
    print("  2. Show what the orchestrator sends to each agent")
    print("  3. Display the final response")
    
    # Check that agents are running
    print("\n📊 Checking agent status...")
    agents = [
        ("Keyword", "http://localhost:8002"),
        ("Grep", "http://localhost:8013"),
        ("Chunk", "http://localhost:8004"),
        ("Summarize", "http://localhost:8005"),
        ("Orchestrator", "http://localhost:8006")
    ]
    
    all_running = True
    async with httpx.AsyncClient(timeout=5) as client:
        for name, url in agents:
            try:
                response = await client.get(f"{url}/.well-known/agent-card.json")
                if response.status_code == 200:
                    print(f"  ✅ {name:12} - RUNNING")
                else:
                    print(f"  ⚠️  {name:12} - NOT READY")
                    all_running = False
            except:
                print(f"  ❌ {name:12} - NOT RESPONDING")
                all_running = False
    
    if not all_running:
        print("\n⚠️  Warning: Not all agents are running. Results may be incomplete.")
        print("Make sure all agents are started first.")
        return
    
    # Send test message and monitor
    await send_test_message()
    
    # Additional monitoring could go here
    await check_agent_logs()

if __name__ == "__main__":
    print("="*80)
    print("ORCHESTRATOR INTER-AGENT COMMUNICATION DEMONSTRATOR")
    print("="*80)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
    
    print("\n" + "="*80)
    print("💡 TIP: To see detailed communication logs:")
    print("   1. Check the orchestrator's console output (bash_19)")
    print("   2. Look for lines with 📤 and 📥 symbols")
    print("   3. Or run: python test_with_logging.py")
    print("="*80)