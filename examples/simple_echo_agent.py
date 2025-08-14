#!/usr/bin/env python3
"""
Simple Echo Agent - The simplest possible A2A agent.

This example demonstrates:
- Minimal agent implementation
- Using the simplified A2AAgent base class
- Automatic A2A protocol compliance
- Zero configuration deployment

Usage:
    python simple_echo_agent.py

The agent will:
- Echo back any message sent to it
- Run on http://localhost:8000
- Be fully A2A compliant
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add parent directory to path to import base
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import A2AAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


class EchoAgent(A2AAgent):
    """Echo agent - returns what you send it."""
    
    def get_agent_name(self) -> str:
        return "Echo Agent"
    
    def get_agent_description(self) -> str:
        return "Simple agent that echoes messages back"
    
    async def process_message(self, message: str) -> str:
        """Simply echo the message back with a prefix."""
        return f"Echo: {message}"


# Module-level app creation for HealthUniverse deployment
agent = EchoAgent()
agent_card = agent.create_agent_card()
task_store = InMemoryTaskStore()
request_handler = DefaultRequestHandler(
    agent_executor=agent,
    task_store=task_store
)

# Create the app - for HealthUniverse deployment
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
).build()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host="0.0.0.0", port=port)