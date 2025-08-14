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

from base import A2AAgent
from typing import List
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


class AssistantAgent(A2AAgent):
    """AI assistant with helpful tools."""
    
    def __init__(self):
        super().__init__()
        self._client = None
    
    def get_agent_name(self) -> str:
        return "AI Assistant"
    
    def get_agent_description(self) -> str:
        return "Helpful AI assistant with tools for time, calculations, and weather"
    
    async def process_message(self, message: str) -> str:
        """Process message using OpenAI API directly."""
        # Initialize OpenAI client if needed
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return "Please set OPENAI_API_KEY environment variable to use this agent."
            
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=api_key)
            except ImportError:
                return "OpenAI library not installed. Run: pip install openai"
        
        # Add context about available tools
        system_message = """You are a helpful AI assistant. You can help with:
- Current date and time (just mention it and I'll provide it)
- Mathematical calculations (I can compute expressions)
- Weather information (I have mock weather data for demonstration)

Be concise and friendly in your responses."""
        
        # Check if message asks for tools
        current_time = None
        calculation = None
        weather_city = None
        
        # Simple keyword detection for tools
        message_lower = message.lower()
        if any(word in message_lower for word in ['time', 'date', 'now', 'today']):
            current_time = self._get_current_time()
        
        if any(word in message_lower for word in ['calculate', 'compute', 'math', '+', '-', '*', '/']):
            # Extract math expression if present
            import re
            math_match = re.search(r'[\d\+\-\*/\(\)\s]+', message)
            if math_match:
                calculation = self._calculate(math_match.group())
        
        weather_info = None
        if 'weather' in message_lower:
            # Extract city name (simple approach)
            words = message.split()
            for i, word in enumerate(words):
                if word.lower() == 'in' and i + 1 < len(words):
                    weather_city = words[i + 1].rstrip('.,?!')
                    weather_info = self._get_weather(weather_city)
                    break
        
        # Build enhanced prompt with tool results
        enhanced_message = message
        if current_time:
            enhanced_message += f"\n\n[Current time: {current_time}]"
        if calculation:
            enhanced_message += f"\n\n[Calculation result: {calculation}]"
        if weather_city:
            enhanced_message += f"\n\n[Weather data: {weather_info}]"
        
        try:
            # Call OpenAI API
            response = self._client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": enhanced_message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Error calling OpenAI API: {str(e)}"
    
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