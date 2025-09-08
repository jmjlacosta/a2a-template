#!/usr/bin/env python3
"""
Test script to verify streaming update functionality.
Tests that the orchestrator properly relays subagent updates.
"""

import asyncio
import json
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.a2a_client import A2AClient
import uuid


async def test_streaming_support():
    """Test if agents support streaming."""
    print("Testing Agent Streaming Support")
    print("=" * 60)
    
    agents = {
        "keyword": "https://apps.healthuniverse.com/aqt-iaj-val",
        "grep": "https://apps.healthuniverse.com/noj-pue-nqe", 
        "chunk": "https://apps.healthuniverse.com/fff-gab-lmy",
        "summarize": "https://apps.healthuniverse.com/ncc-epu-rfk",
        "orchestrator": "https://apps.healthuniverse.com/jmi-umj-lwx"
    }
    
    for name, url in agents.items():
        client = A2AClient(url)
        try:
            supports = await client.supports_streaming(url)
            print(f"{name:12} : {'✓ Supports streaming' if supports else '✗ No streaming'}")
        except Exception as e:
            print(f"{name:12} : ✗ Error checking: {e}")
        finally:
            await client.close()
    
    print("=" * 60)


async def test_orchestrator_streaming():
    """Test streaming from orchestrator."""
    print("\nTesting Orchestrator Streaming")
    print("=" * 60)
    
    orchestrator_url = "http://localhost:8008"  # Local orchestrator
    client = A2AClient(orchestrator_url)
    
    # Sample document
    test_doc = """
    Patient: John Doe
    Date: 2024-01-15
    
    Chief Complaint: Diabetes follow-up
    
    Current Medications:
    - Metformin 1000mg twice daily
    - Lisinopril 10mg daily
    
    Assessment: Type 2 diabetes, well controlled
    """
    
    message = {
        "role": "user",
        "parts": [{"kind": "text", "text": test_doc}],
        "messageId": str(uuid.uuid4()),
        "kind": "message"
    }
    
    print("Sending test document to orchestrator...")
    print("-" * 40)
    
    updates_received = []
    
    async def update_callback(event):
        """Callback for streaming updates."""
        if event.get('kind') == 'status-update':
            status = event.get('status', {})
            msg = status.get('message', {})
            for part in msg.get('parts', []):
                if part.get('kind') == 'text':
                    text = part.get('text', '')
                    print(f"UPDATE: {text}")
                    updates_received.append(text)
    
    try:
        # Check if orchestrator supports streaming
        if await client.supports_streaming():
            print("Orchestrator supports streaming!")
            result = await client.send_message_streaming(message, update_callback)
            print("-" * 40)
            print(f"Received {len(updates_received)} status updates")
            
            if result:
                print("\nFinal result received:")
                print(json.dumps(result, indent=2)[:500] + "...")
        else:
            print("Orchestrator does not support streaming")
            print("Falling back to regular message/send")
            result = await client.send_message(message)
            print("Result received (no streaming)")
    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()
    
    print("=" * 60)


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("STREAMING UPDATE TEST")
    print("="*60)
    
    # Test 1: Check streaming support
    await test_streaming_support()
    
    # Test 2: Test orchestrator streaming (requires local orchestrator running)
    print("\nNote: For full test, run the pipeline locally first:")
    print("  python run_pipeline_local.py")
    print("\nThen run this test in another terminal.")
    
    # Uncomment to test with local orchestrator
    # await test_orchestrator_streaming()
    
    print("\n✓ Test complete!")


if __name__ == "__main__":
    asyncio.run(main())