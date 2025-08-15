#!/usr/bin/env python3
"""
Example agent demonstrating tool usage with the enhanced base.

This shows how to:
- Define tools as Python functions
- Wrap them with Google ADK's FunctionTool
- Let the base handle LLM integration and streaming
"""

import os
import sys
import json
import uvicorn
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add parent directory to path to import base
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import A2AAgent
from google.adk.tools import FunctionTool
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


# Define tool functions
def get_current_time() -> str:
    """Get the current date and time."""
    return f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


def calculate(expression: str) -> str:
    """
    Safely evaluate a mathematical expression.
    
    Args:
        expression: Math expression to evaluate (e.g., "2 + 2")
    
    Returns:
        Result of the calculation
    """
    try:
        # Only allow safe math operations
        allowed_chars = "0123456789+-*/() ."
        if all(c in allowed_chars for c in expression):
            result = eval(expression)
            return f"Result: {result}"
        else:
            return "Error: Invalid characters in expression"
    except Exception as e:
        return f"Error: {str(e)}"


def search_knowledge(query: str, category: str = "general") -> str:
    """
    Search for information (simulated).
    
    Args:
        query: Search query
        category: Category to search in (general, science, history, etc.)
    
    Returns:
        Search results
    """
    # Simulated knowledge base
    knowledge = {
        "general": {
            "python": "Python is a high-level programming language known for its simplicity.",
            "a2a": "A2A (Agent-to-Agent) is a protocol for agent communication.",
            "llm": "Large Language Models are AI systems trained on vast amounts of text."
        },
        "science": {
            "gravity": "Gravity is a fundamental force that attracts objects with mass.",
            "dna": "DNA (Deoxyribonucleic acid) carries genetic information.",
            "photosynthesis": "Process by which plants convert light energy to chemical energy."
        }
    }
    
    category_data = knowledge.get(category, knowledge["general"])
    
    # Simple keyword matching
    for key, value in category_data.items():
        if key.lower() in query.lower():
            return f"Found in {category}: {value}"
    
    return f"No results found for '{query}' in category '{category}'"


def create_json_response(data: Dict) -> str:
    """
    Create a formatted JSON response.
    
    Args:
        data: Dictionary to format as JSON
    
    Returns:
        Formatted JSON string
    """
    return json.dumps(data, indent=2)


class ToolExampleAgent(A2AAgent):
    """Example agent that demonstrates tool usage."""
    
    def get_agent_name(self) -> str:
        return "Tool Example Agent"
    
    def get_agent_description(self) -> str:
        return "Demonstrates tool usage with calculation, time, search, and JSON formatting"
    
    def get_system_instruction(self) -> str:
        return """You are a helpful assistant with access to various tools.
        
You can:
- Get the current time
- Perform calculations
- Search for information
- Format data as JSON

Use the appropriate tools to help answer user questions.
When users ask for calculations, use the calculate tool.
When users ask for the time, use the get_current_time tool.
When users ask for information, use the search_knowledge tool.
When users want structured data, use create_json_response.

Always explain what tools you're using and why."""
    
    def get_tools(self) -> List[FunctionTool]:
        """Provide tools for the LLM to use."""
        return [
            FunctionTool(func=get_current_time),
            FunctionTool(func=calculate),
            FunctionTool(func=search_knowledge),
            FunctionTool(func=create_json_response)
        ]
    
    async def process_message(self, message: str) -> str:
        """
        This won't be called when tools are provided.
        The base will use Google ADK's LlmAgent instead.
        """
        return "This shouldn't be called - tools are handling execution"


# Module-level app creation for HealthUniverse deployment
agent = ToolExampleAgent()
agent_card = agent.create_agent_card()
task_store = InMemoryTaskStore()
request_handler = DefaultRequestHandler(
    agent_executor=agent,
    task_store=task_store
)

# Create the app
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
).build()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    print(f"🛠️ Tools available: 4")
    print("\nExample queries:")
    print("  - What time is it?")
    print("  - Calculate 15 * 23 + 42")
    print("  - Tell me about Python")
    print("  - Search for gravity in science")
    uvicorn.run(app, host="0.0.0.0", port=port)