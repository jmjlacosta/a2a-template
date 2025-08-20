#!/usr/bin/env python3
"""
Simplified test for orchestrators that launches only required agents.
For testing just the orchestrators with their essential dependencies.
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
import signal

# Test with minimal agents - just what the simple orchestrator needs
MINIMAL_AGENTS = [
    ("keyword", 8002, "examples/pipeline/keyword_agent.py"),
    ("grep", 8003, "examples/pipeline/grep_agent.py"),
    ("chunk", 8004, "examples/pipeline/chunk_agent.py"),
    ("summarize", 8005, "examples/pipeline/summarize_agent.py"),
    ("orchestrator", 8006, "examples/pipeline/orchestrator_agent.py"),
    ("simple_orchestrator", 8008, "examples/pipeline/simple_orchestrator_agent.py"),
]

processes = []

def cleanup():
    """Stop all launched processes."""
    print("\n🛑 Stopping agents...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=2)
        except:
            p.kill()
    processes.clear()

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

async def launch_agent(name, port, file):
    """Launch a single agent."""
    print(f"  Launching {name} on port {port}...")
    env = {**subprocess.os.environ, "PORT": str(port)}
    p = subprocess.Popen(
        [sys.executable, file],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    processes.append(p)
    return p

async def wait_for_agent(name, port, timeout=30):
    """Wait for an agent to be ready."""
    import httpx
    url = f"http://localhost:{port}/.well-known/agent-card.json"
    
    for i in range(timeout):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=2.0)
                if response.status_code == 200:
                    print(f"  ✅ {name} is ready on port {port}")
                    return True
        except:
            pass
        await asyncio.sleep(1)
    
    print(f"  ❌ {name} failed to start on port {port}")
    return False

async def test_orchestrator(name, port, message):
    """Test an orchestrator."""
    import httpx
    from utils.a2a_client import A2AAgentClient
    
    print(f"\n🧪 Testing {name} on port {port}...")
    
    try:
        async with A2AAgentClient(timeout=60.0) as client:
            response = await client.call_agent(
                f"http://localhost:{port}",
                message
            )
            
            if response:
                print(f"  ✅ Success! Response length: {len(response)} chars")
                print(f"  Sample: {response[:200]}...")
                return True
            else:
                print(f"  ❌ Empty response")
                return False
                
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

async def main():
    """Main test function."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("="*60)
    print("🚀 SIMPLIFIED ORCHESTRATOR TEST")
    print("="*60)
    
    # Launch minimal agents
    print("\n📦 Launching agents...")
    for name, port, file in MINIMAL_AGENTS:
        await launch_agent(name, port, file)
    
    # Wait for agents to be ready
    print("\n⏳ Waiting for agents to initialize...")
    all_ready = True
    for name, port, _ in MINIMAL_AGENTS:
        if not await wait_for_agent(name, port):
            all_ready = False
    
    if not all_ready:
        print("\n❌ Some agents failed to start")
        cleanup()
        return 1
    
    # Test document
    test_doc = """
PATIENT: Eleanor Richardson
DATE: March 15, 2024

CHIEF COMPLAINT: Follow-up for melanoma treatment

HISTORY: 68-year-old female with Stage IIIB melanoma diagnosed January 2024.
Currently on pembrolizumab (Keytruda) 200mg IV every 3 weeks.

ASSESSMENT: Responding well to treatment. No evidence of progression.

PLAN: Continue current treatment. Next infusion March 22, 2024.
"""
    
    # Test both orchestrators
    print("\n" + "="*60)
    print("🧪 RUNNING TESTS")
    print("="*60)
    
    # Test simple orchestrator
    simple_success = await test_orchestrator(
        "Simple Orchestrator", 
        8008, 
        test_doc
    )
    
    # Test LLM orchestrator  
    llm_success = await test_orchestrator(
        "LLM Orchestrator",
        8006,
        f"Please analyze this medical document:\n\n{test_doc}"
    )
    
    # Results
    print("\n" + "="*60)
    print("📊 RESULTS")
    print("="*60)
    print(f"Simple Orchestrator: {'✅ PASS' if simple_success else '❌ FAIL'}")
    print(f"LLM Orchestrator:    {'✅ PASS' if llm_success else '❌ FAIL'}")
    
    cleanup()
    return 0 if (simple_success and llm_success) else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))