"""
Example A2A-compliant agent using the simplified base class.
This demonstrates how to create a deployable agent in minimal code.
"""

import os
import uvicorn
from typing import List

from base import A2AAgent
from a2a.types import AgentSkill
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


class ExampleAgent(A2AAgent):
    """
    Simple example agent that echoes messages.
    Demonstrates minimal implementation of A2A-compliant agent.
    """
    
    def get_agent_name(self) -> str:
        """Return agent name."""
        return "Example Echo Agent"
    
    def get_agent_description(self) -> str:
        """Return agent description."""
        return "A simple A2A-compliant agent that echoes messages back to the user"
    
    async def process_message(self, message: str) -> str:
        """
        Process incoming message - just echo it back.
        
        Args:
            message: The user's message
            
        Returns:
            Echoed message with prefix
        """
        return f"Echo: {message}"
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """Define agent skills."""
        return [
            AgentSkill(
                id="echo",
                name="Echo Messages",
                description="Echoes back any message sent to the agent",
                tags=["echo", "test", "example"],
                examples=[
                    "Hello, agent!",
                    "Test message",
                    "Can you hear me?"
                ],
                input_modes=["text/plain"],
                output_modes=["text/plain"]
            )
        ]


# Module-level app creation for HealthUniverse deployment
# This is the pattern HealthUniverse expects

# Create agent instance
agent = ExampleAgent()

# Create agent card
agent_card = agent.create_agent_card()

# Create task store and request handler
task_store = InMemoryTaskStore()
request_handler = DefaultRequestHandler(
    agent_executor=agent,
    task_store=task_store
)

# Create the app - THIS IS THE KEY VARIABLE FOR HEALTHUNIVERSE
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
).build()


# Direct execution for local testing
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    print("=" * 60)
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    print(f"🔧 JSON-RPC Endpoint: http://localhost:{port}/")
    print("=" * 60)
    print("\nTest with:")
    print(f'curl -X POST http://localhost:{port} \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"jsonrpc":"2.0","method":"message/send","params":{"message":{"parts":[{"text":"Hello!"}]}},"id":"1"}\'')
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=port)