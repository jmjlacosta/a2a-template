#!/usr/bin/env python3
"""
Test implementation of an LLM agent using A2AAgent.
This demonstrates an LLM-powered agent with tools.
"""

import os
import sys
import datetime
import uvicorn
from typing import List
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import A2AAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

# Try to import FunctionTool, handle if ADK not installed
try:
    from google.adk import get_llm
    from google.adk.tools import FunctionTool
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    get_llm = None
    # Create a mock FunctionTool for testing without ADK
    class FunctionTool:
        def __init__(self, func):
            self.func = func


class TestAssistant(A2AAgent):
    """Test AI assistant with simple tools."""
    
    def __init__(self):
        super().__init__()
        self._llm = None
        self._tools = None
        if ADK_AVAILABLE:
            self._initialize_tools()
    
    def get_agent_name(self) -> str:
        return "Test Assistant"
    
    def get_agent_description(self) -> str:
        return "A test AI assistant that can get time and perform calculations"
    
    def _initialize_tools(self):
        """Initialize tools if ADK is available."""
        self._tools = [
            FunctionTool(self._get_current_time),
            FunctionTool(self._calculate)
        ]
    
    async def process_message(self, message: str) -> str:
        """Process message using LLM if available, otherwise echo."""
        if ADK_AVAILABLE and get_llm:
            # Initialize LLM if needed
            if self._llm is None:
                system_instruction = """You are a helpful AI assistant for testing.
                You can get the current time and perform calculations.
                Be concise and friendly in your responses."""
                
                try:
                    self._llm = get_llm(system_instruction=system_instruction)
                except Exception as e:
                    return f"LLM initialization failed: {e}. Falling back to echo mode.\nEcho: {message}"
            
            # Generate response with tools
            try:
                if self._tools:
                    response = self._llm.generate_text(prompt=message, tools=self._tools)
                else:
                    response = self._llm.generate_text(prompt=message)
                return response
            except Exception as e:
                return f"LLM error: {e}. Message received: {message}"
        else:
            # Fallback to echo mode if no LLM
            return f"Test Echo (no LLM): {message}"
    
    def _get_current_time(self) -> str:
        """Get current date and time."""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _calculate(self, expression: str) -> str:
        """Safely evaluate a mathematical expression."""
        try:
            # Only allow safe math operations
            allowed_chars = "0123456789+-*/()., "
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                return str(result)
            else:
                return "Invalid expression. Only numbers and basic math operators are allowed."
        except Exception as e:
            return f"Calculation error: {str(e)}"


# Module-level app creation for HealthUniverse deployment
agent = TestAssistant()
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
    # Check if we have an API key configured
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if not any([
        os.getenv("GOOGLE_API_KEY"),
        os.getenv("OPENAI_API_KEY"),
        os.getenv("ANTHROPIC_API_KEY")
    ]):
        print("⚠️ Warning: No LLM API key configured!")
        print("The agent will run in non-LLM mode.")
        print("To enable LLM features, set one of:")
        print("  - GOOGLE_API_KEY")
        print("  - OPENAI_API_KEY")
        print("  - ANTHROPIC_API_KEY")
        print()
    
    port = int(os.getenv("PORT", 8002))
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host="0.0.0.0", port=port)