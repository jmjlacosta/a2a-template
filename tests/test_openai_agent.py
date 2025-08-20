#\!/usr/bin/env python3
import os
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)

# Ensure we're using OpenAI
os.environ.pop('GOOGLE_API_KEY', None)
os.environ.pop('GEMINI_API_KEY', None)

print(f"OPENAI_API_KEY set: {bool(os.getenv('OPENAI_API_KEY'))}")
print(f"GOOGLE_API_KEY set: {bool(os.getenv('GOOGLE_API_KEY'))}")

from base import A2AAgent

class TestAgent(A2AAgent):
    def get_agent_name(self):
        return "Test"
    
    def get_agent_description(self):
        return "Test"
    
    async def process_message(self, message):
        return "Test"
    
    def _get_llm_model(self):
        print("Getting LLM model...")
        model = super()._get_llm_model()
        print(f"Selected model: {model}")
        return model

agent = TestAgent()
model = agent._get_llm_model()
print(f"Final model: {model}")
