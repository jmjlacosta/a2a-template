#!/usr/bin/env python3
"""
LLM Assistant Agent - AI assistant with tools.

This example demonstrates:
- Using BaseLLMAgentExecutor for LLM-powered agents
- Adding custom tools (time, calculator, weather)
- Automatic LLM provider detection
- System instructions for agent behavior

Usage:
    export GOOGLE_API_KEY="your-key"  # or OPENAI_API_KEY or ANTHROPIC_API_KEY
    python llm_assistant_agent.py

The agent can:
- Answer general questions using LLM
- Get current time and date
- Perform calculations
- Get weather (mock data)
- Remember conversation context
"""

import sys
import datetime
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import BaseLLMAgentExecutor
from google.adk.tools import FunctionTool
from typing import List


class AssistantAgent(BaseLLMAgentExecutor):
    """AI assistant with helpful tools."""
    
    def get_agent_name(self) -> str:
        return "AI Assistant"
    
    def get_agent_description(self) -> str:
        return "Helpful AI assistant with tools for time, calculations, and weather"
    
    def get_system_instruction(self) -> str:
        return """You are a helpful AI assistant with access to several tools.
        
Available tools:
- get_current_time: Get the current date and time
- calculate: Perform mathematical calculations
- get_weather: Get weather information for a city (mock data)

Be concise and friendly in your responses. Use tools when appropriate.
If asked about something you can calculate or look up with tools, use them."""
    
    def get_tools(self) -> List[FunctionTool]:
        """Return list of available tools."""
        return [
            FunctionTool(self._get_current_time),
            FunctionTool(self._calculate),
            FunctionTool(self._get_weather)
        ]
    
    def _get_current_time(self) -> str:
        """Get current date and time.
        
        Returns the current date and time in ISO format.
        """
        now = datetime.datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S %Z")
    
    def _calculate(self, expression: str) -> str:
        """Perform mathematical calculation.
        
        Args:
            expression: Mathematical expression to evaluate (e.g., "2 + 2", "10 * 5")
            
        Returns:
            The result of the calculation
        """
        try:
            # Safe evaluation of mathematical expressions
            # In production, use a proper math parser
            allowed_chars = "0123456789+-*/()., "
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                return f"{result}"
            else:
                return "Invalid expression. Only numbers and basic operators allowed."
        except Exception as e:
            return f"Calculation error: {str(e)}"
    
    def _get_weather(self, city: str) -> str:
        """Get weather information for a city.
        
        Args:
            city: Name of the city to get weather for
            
        Returns:
            Weather information (mock data for demo)
        """
        # Mock weather data for demonstration
        # In production, integrate with a real weather API
        weather_data = {
            "temperature": "22°C",
            "condition": "Partly cloudy",
            "humidity": "65%",
            "wind": "10 km/h NW",
            "forecast": "Sunny spells throughout the day"
        }
        
        return json.dumps({
            "city": city,
            "current": weather_data,
            "updated": datetime.datetime.now().isoformat()
        }, indent=2)


if __name__ == "__main__":
    agent = AssistantAgent()
    agent.run(port=8002)