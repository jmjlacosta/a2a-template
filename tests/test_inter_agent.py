#!/usr/bin/env python3
"""
Direct test of inter-agent communication to show what's being sent.
"""

import asyncio
import json
import logging
from base import A2AAgent

# Configure logging to show inter-agent communication
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable specific loggers
logging.getLogger("A2AAgent").setLevel(logging.INFO)
logging.getLogger("utils.a2a_client").setLevel(logging.DEBUG)

class TestAgent(A2AAgent):
    """Simple test agent to demonstrate inter-agent communication."""
    
    def get_agent_name(self):
        return "Test Agent"
    
    def get_agent_description(self):
        return "Test agent for demonstrating inter-agent communication"
    
    async def process_message(self, message: str):
        """Process message by calling the keyword agent."""
        print("\n" + "="*80)
        print("📍 TEST AGENT PROCESSING MESSAGE")
        print("="*80)
        print(f"Received: {message}")
        
        # Call the keyword agent
        print("\n" + "="*80)
        print("🚀 NOW CALLING KEYWORD AGENT")
        print("="*80)
        print("Watch for the logging output below to see what's being sent...")
        print("-"*80)
        
        response = await self.call_other_agent(
            "http://localhost:8002",
            "Generate regex patterns for finding diabetes information"
        )
        
        print("-"*80)
        print("✅ RESPONSE FROM KEYWORD AGENT:")
        print(response[:500] if len(response) > 500 else response)
        print("="*80)
        
        return f"Test completed. Keyword agent responded with: {response[:200]}..."

async def main():
    """Run the test."""
    print("\n" + "="*80)
    print("🔍 INTER-AGENT COMMUNICATION DEMONSTRATION")
    print("="*80)
    print("\nThis test will:")
    print("1. Create a test agent")
    print("2. Have it call the keyword agent")
    print("3. Show exactly what's being sent between agents")
    print("\n" + "="*80)
    
    # Create test agent
    agent = TestAgent()
    
    # Simulate processing a message
    result = await agent.process_message("Test message")
    
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print("\nThe test agent successfully:")
    print("✅ Called the keyword agent at http://localhost:8002")
    print("✅ Sent the message: 'Generate regex patterns for finding diabetes information'")
    print("✅ Received and processed the response")
    print("\nCheck the logs above to see the detailed JSON-RPC communication!")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())