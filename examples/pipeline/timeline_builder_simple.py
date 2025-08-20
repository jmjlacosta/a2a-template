#!/usr/bin/env python3
"""
Simplified Timeline Builder Agent - Uses LLM without complex tools.
Builds chronological timelines from JSON-structured medical data.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base import A2AAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


class SimpleTimelineBuilderAgent(A2AAgent):
    """Simplified timeline builder that processes JSON data without complex tools."""
    
    def get_agent_name(self) -> str:
        return "Simple Timeline Builder Agent"
    
    def get_agent_description(self) -> str:
        return "Builds chronological timelines from medical data using structured JSON input."
    
    def get_system_instruction(self) -> str:
        return """You are a medical timeline construction specialist. Your role is to build comprehensive chronological timelines from medical data.

When you receive medical data (as JSON or text):

1. **Extract Temporal Information**: Identify all dates, time periods, and temporal references
2. **Order Events Chronologically**: Arrange all medical events by date
3. **Link Related Events**: Connect related medical events (e.g., diagnosis -> treatment -> follow-up)
4. **Identify Patterns**: Note trends, progressions, or recurring patterns
5. **Highlight Critical Events**: Mark important milestones (diagnosis, major procedures, status changes)

For JSON input with structured data:
- Look for 'date', 'timestamp', 'encounter_date' fields
- Process 'temporal_data' sections if present
- Use 'status', 'provenance', 'confidence' fields to prioritize information

Output Format:
Return a structured JSON timeline with:
{
  "timeline": [
    {
      "date": "YYYY-MM-DD",
      "events": ["event description"],
      "type": "diagnosis|treatment|test|follow-up",
      "significance": "critical|major|routine"
    }
  ],
  "summary": "Brief overview of the timeline",
  "patterns": ["identified patterns or trends"],
  "key_milestones": ["critical events"]
}

If the input is plain text, extract temporal information and create the same structured output."""
    
    def get_tools(self) -> list:
        """No tools needed - LLM will process directly."""
        return []
    
    def supports_streaming(self) -> bool:
        """Enable streaming for real-time processing."""
        return True
    
    async def process_message(self, message: str) -> str:
        """
        Process the message - this is called when no tools are defined.
        The LLM will handle the processing based on system instruction.
        
        Args:
            message: The input message (may be JSON string or text)
            
        Returns:
            Processed timeline as JSON string
        """
        # Try to parse as JSON for better structure
        try:
            data = json.loads(message)
            
            # If it's already structured, format it nicely for LLM
            if isinstance(data, dict):
                # Check for specific fields that might help
                formatted_input = "Process this medical data into a chronological timeline:\n\n"
                
                if "summary" in data:
                    formatted_input += f"SUMMARY:\n{data['summary']}\n\n"
                
                if "temporal_data" in data:
                    formatted_input += f"TEMPORAL DATA:\n{json.dumps(data['temporal_data'], indent=2)}\n\n"
                
                if "encounters" in data:
                    formatted_input += f"ENCOUNTERS:\n{json.dumps(data['encounters'], indent=2)}\n\n"
                
                if "reconciled_data" in data:
                    formatted_input += f"RECONCILED DATA:\n{json.dumps(data['reconciled_data'], indent=2)}\n\n"
                
                # Add any remaining data
                other_keys = [k for k in data.keys() if k not in ["summary", "temporal_data", "encounters", "reconciled_data"]]
                if other_keys:
                    other_data = {k: data[k] for k in other_keys}
                    formatted_input += f"ADDITIONAL DATA:\n{json.dumps(other_data, indent=2)}\n"
                
                return formatted_input
            else:
                # If it's a list or other structure, just format it
                return f"Process this medical data into a chronological timeline:\n\n{json.dumps(data, indent=2)}"
                
        except json.JSONDecodeError:
            # Not JSON, treat as text
            return f"Process this medical information into a chronological timeline:\n\n{message}"


# Module-level app creation (required for deployment)
agent = SimpleTimelineBuilderAgent()
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
    port = int(os.getenv("PORT", 8014))
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    print(f"ℹ️  This simplified version processes JSON data without complex tools")
    uvicorn.run(app, host="0.0.0.0", port=port)