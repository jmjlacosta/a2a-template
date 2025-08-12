#!/usr/bin/env python3
"""
Simple Echo Agent - The simplest possible A2A agent.

This example demonstrates:
- Minimal agent implementation (< 20 lines)
- Using BaseAgentExecutor for non-LLM agents
- Automatic A2A protocol compliance
- Zero configuration deployment

Usage:
    python simple_echo_agent.py

The agent will:
- Echo back any message sent to it
- Run on http://localhost:8000
- Be fully A2A compliant
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import BaseAgentExecutor


class EchoAgent(BaseAgentExecutor):
    """Echo agent - returns what you send it."""
    
    def get_agent_name(self) -> str:
        return "Echo Agent"
    
    def get_agent_description(self) -> str:
        return "Simple agent that echoes messages back"
    
    async def process_message(self, message: str) -> str:
        """Simply echo the message back with a prefix."""
        return f"Echo: {message}"


if __name__ == "__main__":
    # That's it! Full A2A compliance in < 20 lines
    agent = EchoAgent()
    agent.run(port=8000)