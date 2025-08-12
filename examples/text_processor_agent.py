#!/usr/bin/env python3
"""
Text Processor Agent - Demonstrates business logic without LLM.

This example demonstrates:
- Text processing operations (uppercase, word count, reverse, etc.)
- Command-based message parsing
- BaseAgentExecutor for deterministic operations
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

import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import BaseAgentExecutor


class TextProcessorAgent(BaseAgentExecutor):
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


if __name__ == "__main__":
    agent = TextProcessorAgent()
    agent.run(port=8001)