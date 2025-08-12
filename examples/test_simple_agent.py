#!/usr/bin/env python3
"""
Test implementation of a simple agent using BaseAgentExecutor.
This demonstrates the minimal code needed to create an A2A-compliant agent.
"""

from base import BaseAgentExecutor


class EchoAgent(BaseAgentExecutor):
    """Simple echo agent that returns what you send it."""
    
    def get_agent_name(self) -> str:
        return "Echo Agent"
    
    def get_agent_description(self) -> str:
        return "A simple echo agent that returns what you send it"
    
    async def process_message(self, message: str) -> str:
        """Simply echo the message back with a prefix."""
        return f"Echo: {message}"


if __name__ == "__main__":
    # Create and run the agent
    agent = EchoAgent()
    agent.run(port=8001)  # Run on port 8001 to avoid conflicts