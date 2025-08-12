#!/usr/bin/env python3
"""
Test implementation of an LLM agent using BaseLLMAgentExecutor.
This demonstrates an LLM-powered agent with tools.
"""

from base import BaseLLMAgentExecutor
from typing import List
import datetime

# Try to import FunctionTool, handle if ADK not installed
try:
    from google.adk.tools import FunctionTool
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    # Create a mock FunctionTool for testing without ADK
    class FunctionTool:
        def __init__(self, name, description, function):
            self.name = name
            self.description = description
            self.function = function


class TestAssistant(BaseLLMAgentExecutor):
    """Test AI assistant with simple tools."""
    
    def get_agent_name(self) -> str:
        return "Test Assistant"
    
    def get_agent_description(self) -> str:
        return "A test AI assistant that can get time and perform calculations"
    
    def get_system_instruction(self) -> str:
        return """You are a helpful AI assistant for testing.
        You can get the current time and perform calculations.
        Be concise and friendly in your responses."""
    
    def get_tools(self) -> List[FunctionTool]:
        """Return list of available tools."""
        tools = []
        
        # Add time tool
        tools.append(FunctionTool(self._get_current_time))
        
        # Add calculation tool
        tools.append(FunctionTool(self._calculate))
        
        return tools
    
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


if __name__ == "__main__":
    # Check if we have an API key configured
    import os
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
    
    # Create and run the agent
    agent = TestAssistant()
    agent.run(port=8002)  # Run on port 8002 to avoid conflicts