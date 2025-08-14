#!/usr/bin/env python3
"""
Automatic LLM Agent - Demonstrates automatic provider detection.

This agent automatically uses whichever LLM provider you have configured:
- ANTHROPIC_API_KEY -> Uses Claude
- OPENAI_API_KEY -> Uses GPT-3.5/GPT-4  
- GOOGLE_API_KEY -> Uses Gemini

No code changes needed - just set your preferred API key!

Usage:
    export OPENAI_API_KEY="your-key"  # or ANTHROPIC_API_KEY or GOOGLE_API_KEY
    python auto_llm_agent.py
"""

import os
import sys
import uvicorn
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import A2AAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


class AutoLLMAgent(A2AAgent):
    """Agent that automatically uses any available LLM provider."""
    
    def __init__(self):
        super().__init__()
        self._llm = None
    
    def get_agent_name(self) -> str:
        return "Auto LLM Agent"
    
    def get_agent_description(self) -> str:
        return "Automatically detects and uses Claude, GPT, or Gemini based on API keys"
    
    def get_system_instruction(self) -> str:
        """Custom system instruction for this agent."""
        return """You are a knowledgeable AI assistant that can help with a wide variety of tasks.
        Be helpful, accurate, and concise in your responses.
        If asked about yourself, mention that you automatically adapt to use Claude, GPT, or Gemini
        based on which API key is configured."""
    
    async def process_message(self, message: str) -> str:
        """Process message using automatically detected LLM."""
        # Get LLM client with automatic provider detection
        if self._llm is None:
            self._llm = self.get_llm_client()
            
            if self._llm is None:
                return (
                    "No LLM API key configured. Please set one of:\n"
                    "- ANTHROPIC_API_KEY (for Claude)\n"
                    "- OPENAI_API_KEY (for GPT-3.5/GPT-4)\n"
                    "- GOOGLE_API_KEY (for Gemini)\n\n"
                    "Example: export OPENAI_API_KEY='your-key-here'"
                )
            
            # Log which provider was detected
            if os.getenv("ANTHROPIC_API_KEY"):
                self.logger.info("Using Claude (Anthropic)")
            elif os.getenv("OPENAI_API_KEY"):
                self.logger.info("Using GPT (OpenAI)")
            elif os.getenv("GOOGLE_API_KEY"):
                self.logger.info("Using Gemini (Google)")
        
        try:
            # Generate response using whichever LLM is available
            response = self._llm.generate_text(message)
            return response
        except Exception as e:
            self.logger.error(f"LLM error: {e}")
            return f"Error generating response: {str(e)}"


# Module-level app creation for HealthUniverse deployment
agent = AutoLLMAgent()
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
    port = int(os.getenv("PORT", 8000))
    
    # Show which LLM will be used
    print("=" * 60)
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    print("-" * 60)
    
    # Check which API key is available
    if os.getenv("ANTHROPIC_API_KEY"):
        print("🤖 LLM Provider: Claude (Anthropic)")
    elif os.getenv("OPENAI_API_KEY"):
        print("🤖 LLM Provider: GPT (OpenAI)")
    elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        print("🤖 LLM Provider: Gemini (Google)")
    else:
        print("⚠️  No LLM API key detected!")
        print("   Set one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY")
    
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=port)