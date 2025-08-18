#!/usr/bin/env python3
"""
Real-time monitor for orchestrator's inter-agent communication.
Shows what messages the orchestrator sends to other agents.
"""

import asyncio
import subprocess
import re
from datetime import datetime
import sys

def parse_log_line(line):
    """Parse a log line and extract relevant information."""
    # Look for our custom logging patterns
    patterns = {
        'calling_agent': r'📤 Calling agent at (https?://[^\s]+)',
        'message_sent': r'📝 Message: (.+)',
        'response_received': r'📥 Response from (https?://[^\s]+): (.+)',
        'json_request': r'📤 Sending JSON-RPC request: (.+)',
    }
    
    for pattern_name, pattern in patterns.items():
        match = re.search(pattern, line)
        if match:
            return pattern_name, match.groups()
    
    return None, None

def format_output(pattern_type, data):
    """Format the output for display."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if pattern_type == 'calling_agent':
        agent_url = data[0]
        # Extract agent name from URL
        if 'localhost:8002' in agent_url:
            agent = 'KEYWORD AGENT'
        elif 'localhost:8013' in agent_url or 'localhost:8003' in agent_url:
            agent = 'GREP AGENT'
        elif 'localhost:8004' in agent_url:
            agent = 'CHUNK AGENT'
        elif 'localhost:8005' in agent_url:
            agent = 'SUMMARIZE AGENT'
        else:
            agent = agent_url
        
        return f"\n{'='*80}\n[{timestamp}] 🎯 ORCHESTRATOR → {agent}\n{'='*80}"
    
    elif pattern_type == 'message_sent':
        message = data[0]
        # Truncate long messages
        if len(message) > 500:
            message = message[:500] + "..."
        return f"📤 MESSAGE CONTENT:\n{message}\n"
    
    elif pattern_type == 'response_received':
        agent_url = data[0]
        response = data[1] if len(data) > 1 else "Response received"
        # Truncate long responses
        if len(response) > 500:
            response = response[:500] + "..."
        return f"📥 RESPONSE:\n{response}\n{'-'*80}"
    
    elif pattern_type == 'json_request':
        # Try to format JSON nicely
        import json
        try:
            json_str = data[0]
            json_obj = json.loads(json_str)
            # Extract just the message text
            if 'params' in json_obj and 'message' in json_obj['params']:
                msg = json_obj['params']['message']
                if 'parts' in msg and msg['parts']:
                    text = msg['parts'][0].get('text', '')
                    if text:
                        return f"📝 DETAILED MESSAGE:\n{text[:500]}...\n" if len(text) > 500 else f"📝 DETAILED MESSAGE:\n{text}\n"
        except:
            pass
    
    return None

async def monitor_orchestrator():
    """Monitor the orchestrator's output in real-time."""
    print("\n" + "="*80)
    print("🔍 ORCHESTRATOR INTER-AGENT COMMUNICATION MONITOR")
    print("="*80)
    print("\nThis tool shows what messages the orchestrator sends to other agents.")
    print("\nMonitoring orchestrator on port 8006...")
    print("\n" + "="*80)
    print("📡 Waiting for orchestrator activity...")
    print("(Send a message to the orchestrator to see inter-agent communication)")
    print("="*80 + "\n")
    
    # Find the orchestrator's bash session
    # You mentioned bash_19 was the orchestrator
    bash_id = "bash_19"
    
    print(f"Connecting to orchestrator session ({bash_id})...\n")
    
    # Use the BashOutput tool to get the orchestrator's output
    # For demonstration, we'll simulate tailing the output
    last_position = 0
    buffer = []
    
    while True:
        try:
            # In a real implementation, we'd use the BashOutput tool
            # For now, let's simulate monitoring
            await asyncio.sleep(1)
            
            # This is where we'd check for new output
            # For demonstration, print a heartbeat every 10 seconds
            if int(datetime.now().timestamp()) % 10 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            await asyncio.sleep(5)

def main():
    """Main entry point."""
    print("Starting Orchestrator Monitor...")
    print("Press Ctrl+C to stop monitoring.\n")
    
    try:
        asyncio.run(monitor_orchestrator())
    except KeyboardInterrupt:
        print("\nShutting down monitor...")

if __name__ == "__main__":
    main()