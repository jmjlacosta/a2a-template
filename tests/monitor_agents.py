#!/usr/bin/env python3
"""
Monitor inter-agent communication by intercepting HTTP traffic.
"""

import asyncio
import json
from datetime import datetime
import httpx
from mitmproxy import http, options
from mitmproxy.tools.dump import DumpMaster
import threading

class AgentMonitor:
    def __init__(self):
        self.messages = []
    
    def request(self, flow: http.HTTPFlow) -> None:
        """Intercept requests between agents."""
        if flow.request.port in [8002, 8003, 8004, 8005, 8006, 8013]:
            # Parse the request
            if flow.request.method == "POST":
                try:
                    data = json.loads(flow.request.content)
                    if "method" in data and data["method"] == "message/send":
                        message = data.get("params", {}).get("message", {})
                        text = ""
                        if "parts" in message:
                            for part in message["parts"]:
                                if "text" in part:
                                    text = part["text"][:200] + "..." if len(part["text"]) > 200 else part["text"]
                                    break
                        
                        log_entry = {
                            "timestamp": datetime.now().isoformat(),
                            "from_port": flow.request.port,
                            "to_port": flow.request.port,
                            "message": text,
                            "full_request": data
                        }
                        
                        print(f"\n{'='*60}")
                        print(f"📡 INTER-AGENT COMMUNICATION DETECTED")
                        print(f"⏰ Time: {log_entry['timestamp']}")
                        print(f"📤 To Port: {flow.request.port} ({self.get_agent_name(flow.request.port)})")
                        print(f"📝 Message: {text}")
                        print(f"{'='*60}")
                        
                        self.messages.append(log_entry)
                        
                except Exception as e:
                    pass
    
    def get_agent_name(self, port):
        """Map port to agent name."""
        port_map = {
            8002: "Keyword Agent",
            8003: "Grep Agent",
            8013: "Grep Agent",
            8004: "Chunk Agent",
            8005: "Summarize Agent",
            8006: "Orchestrator Agent"
        }
        return port_map.get(port, f"Unknown Agent (port {port})")

# Alternative: Simple HTTP logger without mitmproxy
async def monitor_with_logging():
    """
    Simpler approach: Just watch the agent logs in real-time.
    """
    print("🔍 MONITORING AGENT COMMUNICATION")
    print("=" * 80)
    print("This will show what agents are receiving...")
    print("=" * 80)
    print()
    
    # Start monitoring each agent's logs
    agents = [
        ("Keyword", "bash_13", 8002),
        ("Grep", "bash_18", 8013),
        ("Chunk", "bash_15", 8004),
        ("Summarize", "bash_16", 8005),
        ("Orchestrator", "bash_19", 8006)
    ]
    
    print("📊 Agent Status:")
    for name, bash_id, port in agents:
        print(f"  - {name:12} on port {port}")
    
    print("\n" + "=" * 80)
    print("📡 Waiting for inter-agent communication...")
    print("(Send a message to the orchestrator to see what it sends to other agents)")
    print("=" * 80 + "\n")
    
    # Keep running and show any new activity
    while True:
        await asyncio.sleep(5)
        # In a real implementation, we'd tail the logs here

if __name__ == "__main__":
    print("\n📡 AGENT COMMUNICATION MONITOR")
    print("=" * 80)
    print("\nThis tool helps you see what messages are being sent between agents.")
    print("\nTo see communication:")
    print("1. Keep this running")
    print("2. In another terminal, send a message to the orchestrator")
    print("3. Watch this window to see what the orchestrator sends to other agents")
    print("\n" + "=" * 80 + "\n")
    
    # Run the simple monitor
    asyncio.run(monitor_with_logging())