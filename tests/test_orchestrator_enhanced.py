#!/usr/bin/env python3
"""
Enhanced orchestrator with direct agent calls and detailed logging.
This version actually calls agents and shows what's being sent.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from base import A2AAgent
from tools.orchestrator_tools_fixed import FIXED_ORCHESTRATOR_TOOLS
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

# Configure logging to show inter-agent communication
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class EnhancedOrchestratorAgent(A2AAgent):
    """Enhanced orchestrator that logs all inter-agent communication."""
    
    def get_agent_name(self) -> str:
        return "Enhanced Pipeline Orchestrator"
    
    def get_agent_description(self) -> str:
        return (
            "Enhanced orchestrator with detailed logging of inter-agent communication. "
            "Shows exactly what messages are sent to each agent in the pipeline."
        )
    
    def get_system_instruction(self) -> str:
        return """You are an enhanced orchestrator that coordinates a medical document analysis pipeline.

You have access to these async tools that DIRECTLY call other agents:
- call_keyword_agent: Sends document preview to keyword agent and gets search patterns
- call_grep_agent: Sends patterns to grep agent and gets search results  
- call_chunk_agent: Sends match info to chunk agent and gets extracted context
- call_summarize_agent: Sends chunks to summarize agent and gets analysis
- call_any_agent: Call any agent by name with a message

When the user provides medical text to analyze:
1. First call call_keyword_agent with the document preview
2. Then call call_grep_agent with the patterns from step 1
3. Then call call_chunk_agent for each match from step 2
4. Finally call call_summarize_agent with the extracted chunks

Each tool call will log exactly what's being sent to each agent.
Always use these tools to coordinate the pipeline."""
    
    def get_tools(self) -> List:
        """Return the fixed orchestration tools."""
        return FIXED_ORCHESTRATOR_TOOLS
    
    async def process_message(self, message: str) -> str:
        """Process messages - this won't be used since we have tools."""
        return "Processing with enhanced orchestrator tools..."


def main():
    """Run the enhanced orchestrator agent."""
    print("\n" + "="*80)
    print("🚀 Starting ENHANCED Pipeline Orchestrator")
    print("="*80)
    print("\n📊 This version includes:")
    print("  ✅ Direct agent calls (not just instructions)")
    print("  ✅ Detailed logging of all messages sent")
    print("  ✅ Clear visibility into inter-agent communication")
    print("\n" + "="*80)
    print("\n📍 Server: http://localhost:8007")
    print("📋 Agent Card: http://localhost:8007/.well-known/agent-card.json")
    print("\n🔍 Watch the console for detailed communication logs!")
    print("="*80 + "\n")
    
    # Create and configure the agent
    agent = EnhancedOrchestratorAgent()
    agent_card = agent.create_agent_card()
    
    # Create the A2A application
    task_store = InMemoryTaskStore()
    request_handler = DefaultRequestHandler(
        agent_executor=agent,
        task_store=task_store
    )
    
    app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    ).build()
    
    # Run the server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)


if __name__ == "__main__":
    main()