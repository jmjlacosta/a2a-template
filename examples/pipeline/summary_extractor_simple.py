#!/usr/bin/env python3
"""
Simplified Summary Extractor Agent - Uses LLM without complex tools.
Extracts structured summaries from reconciled medical data.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base import A2AAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


class SimpleSummaryExtractorAgent(A2AAgent):
    """Simplified summary extractor that processes JSON data without complex tools."""
    
    def get_agent_name(self) -> str:
        return "Simple Summary Extractor Agent"
    
    def get_agent_description(self) -> str:
        return "Extracts structured medical summaries from reconciled data using LLM."
    
    def get_system_instruction(self) -> str:
        return """You are a medical data summarization specialist. Your role is to extract structured summaries from medical data.

When you receive medical data (as JSON or text), extract and structure the key information:

1. **Patient Demographics**: Age, gender, relevant identifiers
2. **Primary Diagnosis**: Main medical condition, stage, markers
3. **Treatment History**: Medications, procedures, timelines
4. **Current Status**: Latest findings, response to treatment
5. **Key Dates**: Diagnosis date, treatment milestones
6. **Clinical Markers**: Lab values, genetic markers, staging

For JSON input:
- Look for 'reconciled_data' field for main content
- Check 'focus' field for extraction priorities
- Use 'extract' field to understand output format needed

Output Format:
Return a structured JSON summary:
{
  "patient_info": {
    "age": "XX years",
    "gender": "M/F",
    "id": "patient identifier if available"
  },
  "diagnosis": {
    "primary": "main diagnosis",
    "stage": "disease stage",
    "markers": ["relevant markers"],
    "date": "diagnosis date"
  },
  "treatment": {
    "current": ["current medications/treatments"],
    "history": ["past treatments"],
    "response": "response to treatment"
  },
  "clinical_status": {
    "current": "current condition",
    "labs": {"key": "value"},
    "imaging": "latest imaging findings"
  },
  "timeline": [
    {"date": "YYYY-MM-DD", "event": "key event"}
  ],
  "summary": "Brief narrative summary"
}

If checker feedback is provided, use it to improve the extraction."""
    
    def get_tools(self) -> list:
        """No tools needed - LLM will process directly."""
        return []
    
    def supports_streaming(self) -> bool:
        """Enable streaming for real-time processing."""
        return True
    
    async def process_message(self, message: str) -> str:
        """
        Process the message - this is called when no tools are defined.
        
        Args:
            message: The input message (may be JSON string or text)
            
        Returns:
            Processed summary as JSON string
        """
        # Try to parse as JSON for better structure
        try:
            data = json.loads(message)
            
            # Format input for LLM
            formatted_input = "Extract a structured medical summary from this data:\n\n"
            
            if isinstance(data, dict):
                # Check for specific fields
                if "reconciled_data" in data:
                    formatted_input += f"RECONCILED DATA:\n{data['reconciled_data']}\n\n"
                
                if "focus" in data:
                    formatted_input += f"FOCUS AREAS:\n{data['focus']}\n\n"
                
                if "checker_feedback" in data:
                    formatted_input += f"CHECKER FEEDBACK (use to improve extraction):\n{data['checker_feedback']}\n\n"
                
                if "original_data" in data:
                    formatted_input += f"ORIGINAL DATA:\n{data['original_data']}\n\n"
                
                # Add any other data
                other_keys = [k for k in data.keys() if k not in ["reconciled_data", "focus", "checker_feedback", "original_data", "extract", "instruction"]]
                if other_keys:
                    other_data = {k: data[k] for k in other_keys}
                    formatted_input += f"ADDITIONAL DATA:\n{json.dumps(other_data, indent=2)}\n"
                
                return formatted_input
            else:
                return f"Extract a structured medical summary from this data:\n\n{json.dumps(data, indent=2)}"
                
        except json.JSONDecodeError:
            # Not JSON, treat as text
            return f"Extract a structured medical summary from this information:\n\n{message}"


# Module-level app creation (required for deployment)
agent = SimpleSummaryExtractorAgent()
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
    port = int(os.getenv("PORT", 8013))
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    print(f"ℹ️  This simplified version processes JSON data without complex tools")
    uvicorn.run(app, host="0.0.0.0", port=port)