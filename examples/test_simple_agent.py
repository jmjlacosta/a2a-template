#!/usr/bin/env python3
"""
Test implementation of a simple agent using A2AAgent.
This demonstrates the minimal code needed to create an A2A-compliant agent.
"""

import os
import sys
import uvicorn
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import A2AAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


class TestEchoAgent(A2AAgent):
    """Simple echo agent that returns what you send it."""
    
    def get_agent_name(self) -> str:
        return "Test Echo Agent"
    
    def get_agent_description(self) -> str:
        return "A simple test echo agent that returns what you send it"
    
    async def process_message(self, message: str) -> str:
        """Simply echo the message back with a prefix."""
        return f"Test Echo: {message}"


# Module-level app creation for HealthUniverse deployment
agent = TestEchoAgent()
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
    port = int(os.getenv("PORT", 8001))
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host="0.0.0.0", port=port)