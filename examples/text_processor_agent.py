#!/usr/bin/env python3
"""
Text Processor Agent - Demonstrates business logic without LLM.

This example demonstrates:
- Text processing operations (uppercase, word count, reverse, etc.)
- Command-based message parsing
- A2AAgent for deterministic operations
- No LLM required for simple transformations

Usage:
    python text_processor_agent.py

Commands:
    uppercase: <text>    - Convert text to uppercase
    lowercase: <text>    - Convert text to lowercase
    wordcount: <text>    - Count words in text
    reverse: <text>      - Reverse the text
    remove_spaces: <text> - Remove all spaces
    extract_numbers: <text> - Extract all numbers from text

Example messages:
    "uppercase: hello world" -> "HELLO WORLD"
    "wordcount: this is a test" -> "Word count: 4"
    "reverse: hello" -> "olleh"
"""

import os
import sys
import re
import uvicorn
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import A2AAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


class TextProcessorAgent(A2AAgent):
    """Process text with various operations."""
    
    def get_agent_name(self) -> str:
        return "Text Processor"
    
    def get_agent_description(self) -> str:
        return "Performs text transformations and analysis"
    
    async def process_message(self, message: str) -> str:
        """Process text based on commands."""
        # Parse command and text
        if ":" in message:
            command, text = message.split(":", 1)
            command = command.strip().lower()
            text = text.strip()
        else:
            return self._get_help()
        
        # Execute command
        if command == "uppercase":
            return text.upper()
        
        elif command == "lowercase":
            return text.lower()
        
        elif command == "wordcount":
            count = len(text.split())
            return f"Word count: {count}"
        
        elif command == "reverse":
            return text[::-1]
        
        elif command == "remove_spaces":
            return text.replace(" ", "")
        
        elif command == "extract_numbers":
            numbers = re.findall(r'\d+', text)
            return f"Numbers found: {', '.join(numbers)}" if numbers else "No numbers found"
        
        else:
            return self._get_help()
    
    def _get_help(self) -> str:
        """Return help message with available commands."""
        return """Available commands:
• uppercase: <text> - Convert to uppercase
• lowercase: <text> - Convert to lowercase  
• wordcount: <text> - Count words
• reverse: <text> - Reverse text
• remove_spaces: <text> - Remove spaces
• extract_numbers: <text> - Extract numbers"""


# Module-level app creation for HealthUniverse deployment
agent = TextProcessorAgent()
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