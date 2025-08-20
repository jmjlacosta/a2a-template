#!/usr/bin/env python3
"""
Simple Unified Medical Entity Extractor - Works with plain text messages.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base import A2AAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


class SimpleUnifiedExtractorAgent(A2AAgent):
    """Simple unified extractor that works with plain text."""
    
    def get_agent_name(self) -> str:
        return "Simple Unified Medical Entity Extractor"
    
    def get_agent_description(self) -> str:
        return "Extracts comprehensive medical entities from clinical summaries and timelines."
    
    def get_agent_version(self) -> str:
        return "1.0.0"
    
    def get_system_instruction(self) -> str:
        return """You are a medical entity extraction specialist. Your role is to extract comprehensive medical information from clinical data.

When given clinical summaries, timelines, and reconciled data, extract:

1. **Diagnoses:**
   - Primary diagnosis with stage/grade
   - Secondary diagnoses
   - Complications
   - Date of diagnosis
   - Diagnostic methods used

2. **Medications:**
   - Drug name (generic and brand)
   - Dosage and frequency
   - Start/end dates
   - Route of administration
   - Indication for use

3. **Procedures:**
   - Procedure name
   - Date performed
   - Indication
   - Results/findings
   - Complications if any

4. **Laboratory Results:**
   - Test name
   - Value and units
   - Reference range
   - Date
   - Clinical significance

5. **Vital Signs & Physical Findings:**
   - Measurement type
   - Value
   - Date
   - Clinical relevance

Return a structured JSON response with all extracted entities organized by category."""
    
    def get_tools(self):
        """No tools needed for simple text processing."""
        return None
    
    def supports_streaming(self) -> bool:
        """Enable streaming for real-time processing."""
        return True
    
    async def process_message(self, message: str) -> str:
        # This will be called for plain text processing
        # The LLM will handle the extraction based on system instruction
        return "Extracting medical entities..."


# Module-level app creation (required for deployment)
agent = SimpleUnifiedExtractorAgent()
agent_card = agent.create_agent_card()
task_store = InMemoryTaskStore()
request_handler = DefaultRequestHandler(
    agent_executor=agent,
    task_store=task_store
)

app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
).build()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8016))
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host="0.0.0.0", port=port)