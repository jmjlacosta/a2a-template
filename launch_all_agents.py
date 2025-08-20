#!/usr/bin/env python3
"""
Script to launch all pipeline agents for testing.
Checks ports, launches agents, and provides health checks.
"""

import asyncio
import subprocess
import sys
import time
import socket
import signal
import atexit
from pathlib import Path
from typing import Dict, List, Optional
import json
import httpx
import psutil

# Agent configuration - ports match actual defaults in agent files
AGENTS = {
    "keyword": {
        "port": 8002,
        "file": "examples/pipeline/keyword_agent.py",
        "name": "Keyword Pattern Agent"
    },
    "grep": {
        "port": 8003,
        "file": "examples/pipeline/grep_agent.py",
        "name": "Grep Search Agent"
    },
    "chunk": {
        "port": 8004,
        "file": "examples/pipeline/chunk_agent.py", 
        "name": "Chunk Extractor Agent"
    },
    "summarize": {
        "port": 8005,
        "file": "examples/pipeline/summarize_agent.py",
        "name": "Summarizer Agent"
    },
    "orchestrator": {
        "port": 8006,
        "file": "examples/pipeline/orchestrator_agent.py",
        "name": "LLM Orchestrator Agent"
    },
    "simple_orchestrator": {
        "port": 8008,
        "file": "examples/pipeline/simple_orchestrator_agent.py",
        "name": "Simple Sequential Orchestrator"
    },
    "cancer_summarization": {
        "port": 8009,
        "file": "examples/pipeline/cancer_summarization_agent.py",
        "name": "Cancer Summarization Agent"
    },
    "temporal_tagging": {
        "port": 8010,
        "file": "examples/pipeline/temporal_tagging_agent.py",
        "name": "Temporal Tagging Agent"
    },
    "encounter_grouping": {
        "port": 8011,
        "file": "examples/pipeline/encounter_grouping_agent.py",
        "name": "Encounter Grouping Agent"
    },
    "reconciliation": {
        "port": 8012,
        "file": "examples/pipeline/reconciliation_agent.py",
        "name": "Reconciliation Agent"
    },
    "summary_extractor": {
        "port": 8013,
        "file": "examples/pipeline/summary_extractor_agent.py",
        "name": "Summary Extractor Agent"
    },
    "timeline_builder": {
        "port": 8014,
        "file": "examples/pipeline/timeline_builder_agent.py",
        "name": "Timeline Builder Agent"
    },
    "checker": {
        "port": 8015,
        "file": "examples/pipeline/checker_agent.py",
        "name": "Checker Agent"
    },
    "unified_extractor": {
        "port": 8016,
        "file": "examples/pipeline/unified_extractor_agent.py",
        "name": "Unified Extractor Agent"
    },
    "unified_verifier": {
        "port": 8017,
        "file": "examples/pipeline/unified_verifier_agent.py",
        "name": "Unified Verifier Agent"
    },
    "narrative_synthesis": {
        "port": 8018,
        "file": "examples/pipeline/narrative_synthesis_agent.py",
        "name": "Narrative Synthesis Agent"
    }
}

# Track running processes
running_processes: Dict[str, subprocess.Popen] = {}


def check_port_available(port: int) -> bool:
    """Check if a port is available for use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', port))
            return True
        except socket.error:
            return False


def kill_process_on_port(port: int) -> bool:
    """Kill any process using the specified port."""
    try:
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.status == 'LISTEN':
                process = psutil.Process(conn.pid)
                process.terminate()
                time.sleep(0.5)
                if process.is_running():
                    process.kill()
                return True
    except Exception as e:
        print(f"Error killing process on port {port}: {e}")
    return False


async def check_agent_health(port: int, max_retries: int = 30) -> bool:
    """Check if an agent is responding at the given port."""
    url = f"http://localhost:{port}/.well-known/agent-card.json"
    
    async with httpx.AsyncClient() as client:
        for i in range(max_retries):
            try:
                response = await client.get(url, timeout=2.0)
                if response.status_code == 200:
                    return True
            except (httpx.RequestError, httpx.TimeoutException):
                pass
            
            if i < max_retries - 1:
                await asyncio.sleep(1)
    
    return False


def launch_agent(name: str, config: Dict) -> Optional[subprocess.Popen]:
    """Launch a single agent."""
    port = config["port"]
    file_path = Path(config["file"])
    
    if not file_path.exists():
        print(f"❌ Agent file not found: {file_path}")
        return None
    
    # Check if port is available
    if not check_port_available(port):
        print(f"⚠️  Port {port} is in use, attempting to free it...")
        if kill_process_on_port(port):
            print(f"✅ Freed port {port}")
            time.sleep(1)
        else:
            print(f"❌ Could not free port {port}")
            return None
    
    # Launch the agent with logging enabled
    env = {**subprocess.os.environ, 
           "PORT": str(port),
           "LOG_LEVEL": "INFO",
           "SHOW_AGENT_CALLS": "true"}
    
    # Launch with output visible (not piped) for debugging
    process = subprocess.Popen(
        [sys.executable, str(file_path)],
        env=env,
        stdout=None,  # Show stdout
        stderr=None,  # Show stderr
        text=True
    )
    
    return process


async def launch_all_agents(agents_to_launch: Optional[List[str]] = None) -> Dict[str, bool]:
    """Launch all specified agents and verify they're running."""
    global running_processes
    
    if agents_to_launch is None:
        agents_to_launch = list(AGENTS.keys())
    
    results = {}
    
    print("\n" + "="*60)
    print("🚀 LAUNCHING AGENTS")
    print("="*60)
    
    # Launch each agent
    for name in agents_to_launch:
        if name not in AGENTS:
            print(f"❌ Unknown agent: {name}")
            results[name] = False
            continue
        
        config = AGENTS[name]
        print(f"\n📦 Launching {config['name']}...")
        print(f"   Port: {config['port']}")
        print(f"   File: {config['file']}")
        
        process = launch_agent(name, config)
        if process:
            running_processes[name] = process
            print(f"   Process started (PID: {process.pid})")
            
            # Wait for agent to be ready
            print(f"   Waiting for agent to be ready...")
            is_healthy = await check_agent_health(config['port'])
            
            if is_healthy:
                print(f"✅ {config['name']} is running on port {config['port']}")
                results[name] = True
            else:
                print(f"❌ {config['name']} failed to start properly")
                process.terminate()
                running_processes.pop(name, None)
                results[name] = False
        else:
            print(f"❌ Failed to launch {config['name']}")
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("📊 LAUNCH SUMMARY")
    print("="*60)
    
    successful = [name for name, success in results.items() if success]
    failed = [name for name, success in results.items() if not success]
    
    print(f"✅ Successfully launched: {len(successful)}/{len(agents_to_launch)}")
    if successful:
        for name in successful:
            print(f"   • {AGENTS[name]['name']} (port {AGENTS[name]['port']})")
    
    if failed:
        print(f"\n❌ Failed to launch: {len(failed)}")
        for name in failed:
            print(f"   • {AGENTS[name]['name']}")
    
    return results


def stop_all_agents():
    """Stop all running agents."""
    global running_processes
    
    if not running_processes:
        return
    
    print("\n" + "="*60)
    print("🛑 STOPPING AGENTS")
    print("="*60)
    
    for name, process in running_processes.items():
        try:
            print(f"Stopping {AGENTS[name]['name']} (PID: {process.pid})...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            print(f"✅ Stopped {AGENTS[name]['name']}")
        except Exception as e:
            print(f"❌ Error stopping {name}: {e}")
    
    running_processes.clear()


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\n\n⚠️  Received shutdown signal, stopping agents...")
    stop_all_agents()
    sys.exit(0)


async def main():
    """Main function to launch agents."""
    # Register cleanup handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(stop_all_agents)
    
    # Parse command line arguments
    agents_to_launch = None
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("Usage: python launch_all_agents.py [agent1 agent2 ...]")
            print("\nAvailable agents:")
            for name, config in AGENTS.items():
                print(f"  {name:20} - {config['name']} (port {config['port']})")
            return
        else:
            agents_to_launch = sys.argv[1:]
    
    # Launch agents
    results = await launch_all_agents(agents_to_launch)
    
    # If all agents launched successfully, keep running
    if all(results.values()):
        print("\n" + "="*60)
        print("✅ ALL AGENTS RUNNING")
        print("="*60)
        print("\nPress Ctrl+C to stop all agents...")
        
        try:
            # Keep the script running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        print("\n⚠️  Some agents failed to launch")
        stop_all_agents()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())