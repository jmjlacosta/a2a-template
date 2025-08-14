#!/usr/bin/env python3
"""
Test examples demonstrating how to build and test A2A agents.
Run this file to see both simple and LLM-powered agents in action.
"""

import asyncio
import os
from base import A2AAgent
from typing import List, Any


class SimpleEchoAgent(A2AAgent):
    """Minimal A2A-compliant agent that echoes messages."""
    
    def get_agent_name(self) -> str:
        return "Simple Echo Agent"
    
    def get_agent_description(self) -> str:
        return "Echoes back any message sent to it"
    
    async def process_message(self, message: str) -> str:
        """Process incoming message and return response."""
        return f"Echo: {message}"


class LLMAssistantAgent(A2AAgent):
    """LLM-powered agent with tool capabilities."""
    
    def __init__(self):
        super().__init__()
        self._llm = None
    
    def get_agent_name(self) -> str:
        return "LLM Assistant"
    
    def get_agent_description(self) -> str:
        return "AI assistant powered by LLM with tool capabilities"
    
    def get_system_instruction(self) -> str:
        return """You are a helpful AI assistant. Be concise and helpful."""
    
    async def process_message(self, message: str) -> str:
        """Process message using LLM."""
        # Get LLM client with automatic provider detection
        if self._llm is None:
            self._llm = self.get_llm_client()
            
            if self._llm is None:
                return "No LLM API key configured. Please set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY"
        
        # Generate response
        try:
            response = self._llm.generate_text(message)
            return response
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _calculate(self, expression: str) -> str:
        """Evaluate a mathematical expression.
        
        Args:
            expression: Mathematical expression to evaluate (e.g., "2 + 2")
            
        Returns:
            The result of the calculation
        """
        try:
            # Only allow safe math operations
            allowed_names = {
                k: v for k, v in {
                    'abs': abs, 'round': round, 'min': min, 'max': max,
                    'sum': sum, 'pow': pow, 'len': len
                }.items()
            }
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return f"Result: {result}"
        except Exception as e:
            return f"Error evaluating expression: {e}"
    
    def _get_time(self) -> str:
        """Get the current date and time.
        
        Returns:
            Current timestamp in readable format
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def test_simple_agent():
    """Test the simple echo agent."""
    print("\n" + "="*60)
    print("Testing Simple Echo Agent")
    print("="*60)
    
    agent = SimpleEchoAgent()
    
    # Test basic message processing
    test_messages = [
        "Hello, agent!",
        "How are you?",
        "Testing A2A compliance"
    ]
    
    for msg in test_messages:
        response = await agent.process_message(msg)
        print(f"Input:  {msg}")
        print(f"Output: {response}")
        print()
    
    # Test agent metadata
    print(f"Agent Name: {agent.get_agent_name()}")
    print(f"Agent Description: {agent.get_agent_description()}")
    
    return agent


async def test_llm_agent():
    """Test the LLM-powered agent."""
    print("\n" + "="*60)
    print("Testing LLM Assistant Agent")
    print("="*60)
    
    # Check for API keys
    has_google = bool(os.getenv("GOOGLE_API_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    
    print("API Key Status:")
    print(f"  Google API: {'✓' if has_google else '✗'}")
    print(f"  OpenAI API: {'✓' if has_openai else '✗'}")
    print(f"  Anthropic API: {'✓' if has_anthropic else '✗'}")
    
    if not (has_google or has_openai or has_anthropic):
        print("\n⚠️  No LLM API keys found!")
        print("Set one of these environment variables:")
        print("  export GOOGLE_API_KEY='your-key'")
        print("  export OPENAI_API_KEY='your-key'")
        print("  export ANTHROPIC_API_KEY='your-key'")
        return None
    
    agent = LLMAssistantAgent()
    
    # Test agent metadata
    print(f"\nAgent Name: {agent.get_agent_name()}")
    print(f"Agent Description: {agent.get_agent_description()}")
    print(f"System Instruction: {agent.get_system_instruction()[:100]}...")
    print(f"Number of tools: {len(agent.get_tools())}")
    
    # Test message processing (if LLM is configured)
    test_messages = [
        "What is 2 + 2?",
        "What time is it?",
        "Tell me a short joke"
    ]
    
    print("\nTesting message processing:")
    for msg in test_messages:
        try:
            response = await agent.process_message(msg)
            print(f"\nInput:  {msg}")
            print(f"Output: {response[:200]}{'...' if len(response) > 200 else ''}")
        except Exception as e:
            print(f"\nInput:  {msg}")
            print(f"Error:  {e}")
    
    return agent


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("A2A Agent Template - Test Examples")
    print("="*60)
    
    # Test simple agent
    simple_agent = await test_simple_agent()
    
    # Test LLM agent
    llm_agent = await test_llm_agent()
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    if simple_agent:
        print("✅ Simple agent test completed successfully")
    
    if llm_agent:
        print("✅ LLM agent test completed successfully")
    elif not any([os.getenv("GOOGLE_API_KEY"), 
                  os.getenv("OPENAI_API_KEY"), 
                  os.getenv("ANTHROPIC_API_KEY")]):
        print("⚠️  LLM agent test skipped (no API keys)")
    
    print("\nTo run agents as servers:")
    print("  python test_agent_examples.py --serve")
    
    # If --serve flag is provided, run as server
    import sys
    if "--serve" in sys.argv:
        print("\nStarting Simple Echo Agent on port 8001...")
        print("Press Ctrl+C to stop")
        simple_agent.run(port=8001)


if __name__ == "__main__":
    asyncio.run(main())