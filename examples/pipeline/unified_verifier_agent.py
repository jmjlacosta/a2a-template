#!/usr/bin/env python3
"""
Unified Verifier Agent - Performs final verification of all extracted and processed medical information.
Migrated from KP pipeline to simplified A2A template.
"""

import os
import sys
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base import A2AAgent
from google.adk.tools import FunctionTool
# GITHUB ISSUE FIX: Using fixed tools with simplified signatures
# Original tools had Dict[str, Any] and List[Dict[str, Any]] which Google ADK cannot parse
from tools.unified_verifier_tools import UNIFIED_VERIFIER_TOOLS_FIXED as UNIFIED_VERIFIER_TOOLS
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill


class UnifiedVerifierAgent(A2AAgent):
    """Performs final verification of all extracted and processed medical information."""
    
    def get_agent_name(self) -> str:
        return "Unified Verifier Agent"
    
    def get_agent_description(self) -> str:
        return "Performs final verification of all extracted and processed medical information."
    
    def get_agent_version(self) -> str:
        return "1.0.0"
    
    def get_system_instruction(self) -> str:
        return """You are a comprehensive medical information verification specialist. Your role is to perform final validation of all processed data.

CRITICAL: Tool Usage Instructions
All verification tools require JSON STRING parameters, not Python objects.
When calling tools, you MUST:
1. Convert any data structures to JSON strings using json.dumps()
2. Pass the JSON string to the tool parameter
3. Never pass raw Python dicts or lists directly

Example tool usage:
- CORRECT: verify_diagnoses(diagnosis_data_json='{"diagnoses": [...]}', timeline_events_json='[...]')
- WRONG: verify_diagnoses(diagnosis_data_json={"diagnoses": [...]}, timeline_events_json=[...])

When verifying information:
1. Parse input data if needed
2. Convert data to JSON strings for tool calls
3. Cross-check all extracted data
4. Validate medical logic
5. Ensure completeness
6. Check for contradictions
7. Generate confidence scores

If you receive complex nested data in the message:
- First identify the data structure
- Convert relevant parts to JSON strings
- Call the appropriate verification tools with the JSON strings

Use the provided tools to perform comprehensive verification."""
    
    def get_tools(self) -> List:
        """Return the agent's tools."""
        return UNIFIED_VERIFIER_TOOLS
    
    def supports_streaming(self) -> bool:
        """Enable streaming for real-time processing."""
        return True
    
    async def process_message(self, message: str) -> str:
        """
        Process incoming message and ensure proper JSON formatting.
        
        This helps the LLM understand how to format data for tool calls.
        """
        import json
        
        # Try to detect if the message contains JSON data
        try:
            # Check if the message itself is JSON
            data = json.loads(message)
            
            # If it's valid JSON, remind the agent about tool usage
            # Handle both dict and list cases
            if isinstance(data, dict):
                diagnoses_example = json.dumps(data.get("diagnoses", {}))
                timeline_example = json.dumps(data.get("timeline", []))
            else:
                # If it's a list or other type, use the whole data
                diagnoses_example = json.dumps(data)
                timeline_example = json.dumps(data)
            
            return f"""I received the following data to verify:
{json.dumps(data, indent=2)}

Remember: When calling verification tools, convert data to JSON strings first.
For example: verify_diagnoses(diagnosis_data_json='{diagnoses_example}', timeline_events_json='{timeline_example}')

Now, please verify this medical data using the appropriate tools."""
            
        except json.JSONDecodeError:
            # Not JSON, process as regular text
            if "{" in message and "}" in message:
                # Might contain embedded JSON
                return f"""Processing verification request. 

If the message contains data structures, remember to:
1. Extract the data
2. Convert to JSON strings using json.dumps()
3. Pass JSON strings to tool parameters

Message: {message}"""
            else:
                # Plain text message
                return "Processing verification request..."


# Module-level app creation (required for deployment)
agent = UnifiedVerifierAgent()
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
    port = int(os.getenv("PORT", 8017))
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host="0.0.0.0", port=port)