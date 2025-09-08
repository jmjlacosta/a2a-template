#!/usr/bin/env python3
"""
Run all pipeline agents locally and send a message to the orchestrator.

Ports:
    orchestrator : 8008
    keyword      : 8002
    grep         : 8003
    chunk        : 8004
    summarize    : 8005

Usage:
  python run_pipeline_local.py
  python run_pipeline_local.py "Your medical document text..."
"""

import argparse
import json
import os
import signal
import socket
import sys
import time
from pathlib import Path
from typing import Dict, List
import subprocess

try:
    import httpx
except Exception:
    print("Please `pip install httpx`", file=sys.stderr)
    sys.exit(1)

# Make sure local imports resolve
sys.path.insert(0, os.getcwd())

# Agent configurations - matching the ports in each agent's __main__
AGENTS: List[Dict] = [
    {"name": "keyword",     "module": "examples.pipeline.keyword_agent",     "port": 8002},
    {"name": "grep",        "module": "examples.pipeline.grep_agent",        "port": 8003},
    {"name": "chunk",       "module": "examples.pipeline.chunk_agent",       "port": 8004},
    {"name": "summarize",   "module": "examples.pipeline.summarize_agent",   "port": 8005},
    {"name": "orchestrator","module": "examples.pipeline.simple_orchestrator_agent", "port": 8008},
]

REGISTRY_PATH = Path("config/agents.json")

# Sample medical document for testing
SAMPLE_DOCUMENT = """
Patient: Eleanor Richardson, DOB: 03/15/1952
Visit Date: 11/20/2024

CHIEF COMPLAINT: Follow-up for diabetes management and hypertension

HISTORY OF PRESENT ILLNESS: Ms. Richardson is a 72-year-old female with Type 2 diabetes diagnosed in 2010 and hypertension since 2008. She reports good medication compliance. Blood glucose readings at home have ranged from 110-145 mg/dL fasting. No episodes of hypoglycemia. Blood pressure readings averaging 135/85 mmHg at home.

CURRENT MEDICATIONS:
- Metformin 1000mg PO BID
- Lisinopril 20mg PO daily
- Atorvastatin 40mg PO daily
- Aspirin 81mg PO daily

PHYSICAL EXAMINATION:
BP: 138/86 mmHg, HR: 72 bpm regular, Weight: 168 lbs
Heart: Regular rate and rhythm, no murmurs
Lungs: Clear to auscultation bilaterally
Extremities: No edema, pedal pulses intact

LABORATORY RESULTS (11/18/2024):
- HbA1c: 7.2% (goal <7%)
- Fasting glucose: 132 mg/dL
- Creatinine: 1.1 mg/dL
- eGFR: 58 mL/min/1.73m²
- Total cholesterol: 178 mg/dL
- LDL: 98 mg/dL
- HDL: 52 mg/dL

ASSESSMENT AND PLAN:
1. Type 2 Diabetes - Suboptimal control. Increase Metformin to 1000mg TID if tolerated.
2. Hypertension - Not at goal. Consider adding Amlodipine 5mg daily.
3. Continue current statin therapy for cardiovascular protection.
4. Follow-up in 3 months with repeat labs.
"""


def check_port_available(port: int) -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("localhost", port))
            return True
    except OSError:
        return False


def find_alternative_port(preferred_port: int) -> int:
    """Find an alternative port if the preferred one is busy."""
    for offset in range(1, 10):
        alt_port = preferred_port + offset
        if check_port_available(alt_port):
            return alt_port
    raise RuntimeError(f"Could not find an available port starting from {preferred_port}")


def check_and_resolve_ports():
    """Check all agent ports and resolve conflicts."""
    conflicts = []
    
    for agent in AGENTS:
        port = agent["port"]
        if not check_port_available(port):
            conflicts.append(agent)
    
    if conflicts:
        print("⚠️  Port conflicts detected:")
        for agent in conflicts:
            old_port = agent["port"]
            try:
                new_port = find_alternative_port(old_port)
                print(f"   {agent['name']}: {old_port} → {new_port} (conflict resolved)")
                agent["port"] = new_port
            except RuntimeError:
                print(f"   {agent['name']}: {old_port} → FAILED to find alternative")
                print(f"\n❌ Could not resolve port conflict for {agent['name']}")
                print("Try stopping services on these ports or run:")
                print(f"   lsof -ti :{old_port} | xargs kill -9")
                sys.exit(1)
        print()
    else:
        print("✅ All ports available")
    
    return len(conflicts)


def write_registry():
    """Write config/agents.json so agents can resolve names to URLs."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    agents = {}
    for a in AGENTS:
        # Each agent base URL
        agents[a["name"]] = {"url": f"http://localhost:{a['port']}"}
    
    payload = {"agents": agents}
    REGISTRY_PATH.write_text(json.dumps(payload, indent=2))
    print(f"✅ Wrote {REGISTRY_PATH}")
    print(json.dumps(payload, indent=2))


def spawn_agents() -> List[subprocess.Popen]:
    """Launch all agents via Python in subprocesses."""
    procs: List[subprocess.Popen] = []
    env_base = os.environ.copy()
    env_base.setdefault("LOG_LEVEL", "INFO")
    
    for a in AGENTS:
        env = env_base.copy()
        # Set PORT environment variable for each agent
        env["PORT"] = str(a["port"])
        
        # Run the agent module directly
        cmd = [sys.executable, "-m", a["module"]]
        
        print(f"🟢 Starting {a['name']} on port {a['port']}")
        procs.append(subprocess.Popen(cmd, env=env))
    
    return procs


def wait_until_ready(timeout: float = 30.0):
    """Poll each agent's well-known endpoint until ready."""
    deadline = time.time() + timeout
    
    with httpx.Client(timeout=2.0) as client:
        for a in AGENTS:
            url = f"http://localhost:{a['port']}/.well-known/agent-card.json"
            ok = False
            
            while time.time() < deadline:
                try:
                    r = client.get(url)
                    if r.status_code == 200:
                        card = r.json()
                        print(f"✅ {a['name']} ready: {card.get('name', 'Unknown')}")
                        ok = True
                        break
                except Exception:
                    pass
                time.sleep(0.5)
            
            if not ok:
                raise RuntimeError(f"Timed out waiting for {a['name']} on port {a['port']}")


def send_message_to_orchestrator(text: str) -> str:
    """
    Send a text message to the orchestrator using JSON-RPC protocol.
    The orchestrator has tools, so it will process the message through its pipeline.
    """
    orchestrator_port = next(a["port"] for a in AGENTS if a["name"] == "orchestrator")
    endpoint = f"http://localhost:{orchestrator_port}/"
    
    # Create JSON-RPC request
    import uuid
    payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": text}],
                "kind": "message",
                "messageId": str(uuid.uuid4())
            },
            "metadata": {}
        },
        "id": 1
    }
    
    print(f"\n📤 Sending message to orchestrator...")
    print(f"   Message length: {len(text)} characters")
    
    with httpx.Client(timeout=120.0) as client:
        r = client.post(endpoint, json=payload)
        r.raise_for_status()
        
        # Parse JSON-RPC response
        data = r.json()
        
        # Check for errors
        if "error" in data:
            error = data["error"]
            raise RuntimeError(f"JSON-RPC error {error.get('code')}: {error.get('message')}")
        
        # Extract result
        result = data.get("result", {})
        
        # The orchestrator returns an artifact with parts
        if isinstance(result, dict):
            # Look for artifact parts
            if "artifact" in result:
                artifact = result["artifact"]
                if "parts" in artifact:
                    texts = []
                    for part in artifact["parts"]:
                        if part.get("kind") == "text":
                            texts.append(part.get("text", ""))
                    if texts:
                        return "\n".join(texts)
            
            # Try direct text extraction
            if "text" in result:
                return result["text"]
            
            # Look for parts directly
            if "parts" in result:
                texts = []
                for part in result["parts"]:
                    if part.get("kind") == "text":
                        texts.append(part.get("text", ""))
                if texts:
                    return "\n".join(texts)
        
        # Fallback to string representation
        if isinstance(result, str):
            return result
        
        return json.dumps(result, indent=2)


def shutdown(procs: List[subprocess.Popen]):
    """Gracefully shutdown all agent processes."""
    print("\n🛑 Shutting down agents...")
    
    # Send SIGINT first
    for p in procs:
        try:
            if p.poll() is None:
                if os.name == "nt":
                    p.terminate()
                else:
                    p.send_signal(signal.SIGINT)
        except Exception:
            pass
    
    # Wait for graceful shutdown
    t0 = time.time()
    while time.time() - t0 < 5.0:
        if all(p.poll() is not None for p in procs):
            break
        time.sleep(0.2)
    
    # Force kill if needed
    for p in procs:
        try:
            if p.poll() is None:
                p.kill()
        except Exception:
            pass
    
    print("✅ All agents stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="Run pipeline agents locally and test with medical document."
    )
    parser.add_argument(
        "message",
        nargs="?",
        default=SAMPLE_DOCUMENT,
        help="Medical document to analyze (default: sample document)"
    )
    args = parser.parse_args()
    
    print("="*80)
    print("🚀 Medical Document Pipeline Test")
    print("="*80)
    
    print("\n🔍 Checking port availability...")
    conflicts_resolved = check_and_resolve_ports()
    
    print("\n📝 Writing agent registry...")
    write_registry()
    
    procs = []
    try:
        print("\n🚀 Starting all pipeline agents...")
        procs = spawn_agents()
        
        print("\n⏳ Waiting for agents to become ready...")
        wait_until_ready(timeout=45.0)
        
        print("\n" + "="*80)
        print("🏥 PROCESSING MEDICAL DOCUMENT")
        print("="*80)
        
        # Send the message
        result = send_message_to_orchestrator(args.message)
        
        print("\n" + "="*80)
        print("📋 PIPELINE RESULT")
        print("="*80)
        print(result)
        print("="*80)
        
        print("\n✅ Pipeline test complete!")
        print("\n💡 Press Ctrl+C to stop all agents and exit.")
        
        # Keep running until interrupted
        while True:
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\n\n👋 Stopping agents...")
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        shutdown(procs)


if __name__ == "__main__":
    main()