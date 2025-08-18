#!/usr/bin/env python3
"""
Compare the performance of enhanced vs simple orchestrators.
Tests both with Eleanor Richardson's medical text.
"""

import asyncio
import json
import uuid
import httpx
import time
from datetime import datetime


async def test_orchestrator(name: str, url: str, message: str) -> dict:
    """
    Test an orchestrator and measure performance.
    
    Returns:
        Dictionary with results and metrics
    """
    print(f"\n{'='*80}")
    print(f"🧪 Testing {name}")
    print(f"{'='*80}")
    print(f"URL: {url}")
    print(f"Message length: {len(message)} characters")
    
    # Create JSON-RPC request
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
                        "text": message
                    }
                ]
            }
        },
        "id": request_id
    }
    
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            print(f"⏳ Sending request at {datetime.now().strftime('%H:%M:%S')}...")
            
            response = await client.post(
                url,
                json=jsonrpc_request,
                headers={"Content-Type": "application/json"}
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            print(f"✅ Response received at {datetime.now().strftime('%H:%M:%S')}")
            print(f"⏱️  Execution time: {execution_time:.2f} seconds")
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract response text
                response_text = ""
                if "result" in result and "artifacts" in result["result"]:
                    artifacts = result["result"]["artifacts"]
                    if artifacts and len(artifacts) > 0:
                        artifact = artifacts[0]
                        if "parts" in artifact and len(artifact["parts"]) > 0:
                            response_text = artifact["parts"][0].get("text", "No text")
                
                print(f"📝 Response length: {len(response_text)} characters")
                
                return {
                    "name": name,
                    "success": True,
                    "execution_time": execution_time,
                    "response_length": len(response_text),
                    "response_preview": response_text[:500] + "..." if len(response_text) > 500 else response_text,
                    "status_code": response.status_code
                }
            else:
                return {
                    "name": name,
                    "success": False,
                    "execution_time": execution_time,
                    "error": f"HTTP {response.status_code}",
                    "response": response.text[:500]
                }
                
        except asyncio.TimeoutError:
            return {
                "name": name,
                "success": False,
                "execution_time": 300.0,
                "error": "Timeout after 5 minutes"
            }
        except Exception as e:
            return {
                "name": name,
                "success": False,
                "execution_time": time.time() - start_time,
                "error": str(e)
            }


async def main():
    """Compare both orchestrators."""
    
    print("\n" + "="*80)
    print("🔬 ORCHESTRATOR COMPARISON TEST")
    print("="*80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Read Eleanor's medical text
    with open("test.txt", "r") as f:
        test_content = f.read()
    
    print(f"\n📄 Test Document: Eleanor Richardson's medical record")
    print(f"   Length: {len(test_content)} characters")
    
    # Prepare test message
    test_message = f"Please analyze this medical text:\n\n{test_content}"
    
    # Test both orchestrators
    orchestrators = [
        ("Simple Orchestrator", "http://localhost:8008/"),
        ("Enhanced Orchestrator", "http://localhost:8007/")
    ]
    
    results = []
    for name, url in orchestrators:
        result = await test_orchestrator(name, url, test_message)
        results.append(result)
        
        # Brief pause between tests
        if name != orchestrators[-1][0]:
            print("\n⏸️  Pausing 5 seconds before next test...")
            await asyncio.sleep(5)
    
    # Compare results
    print("\n" + "="*80)
    print("📊 COMPARISON RESULTS")
    print("="*80)
    
    for result in results:
        print(f"\n{result['name']}:")
        print(f"  • Success: {'✅' if result.get('success') else '❌'}")
        print(f"  • Execution Time: {result.get('execution_time', 0):.2f} seconds")
        if result.get('success'):
            print(f"  • Response Length: {result.get('response_length', 0)} characters")
        else:
            print(f"  • Error: {result.get('error', 'Unknown')}")
    
    # Calculate differences
    if len(results) == 2 and all(r.get('success') for r in results):
        simple_time = results[0]['execution_time']
        enhanced_time = results[1]['execution_time']
        
        print("\n" + "-"*40)
        print("⚖️  PERFORMANCE COMPARISON:")
        print(f"  • Simple is {enhanced_time/simple_time:.2f}x {'faster' if simple_time < enhanced_time else 'slower'}")
        print(f"  • Time difference: {abs(enhanced_time - simple_time):.2f} seconds")
        
        if simple_time < enhanced_time:
            print(f"  • Simple saved {enhanced_time - simple_time:.2f} seconds")
        else:
            print(f"  • Enhanced saved {simple_time - enhanced_time:.2f} seconds")
    
    print("\n" + "="*80)
    print("✅ COMPARISON COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())