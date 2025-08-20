#!/usr/bin/env python3
"""
Simple Reconciliation Agent - Works with plain text messages.
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


class SimpleReconciliationAgent(A2AAgent):
    """Simple reconciliation agent that works with plain text."""
    
    def get_agent_name(self) -> str:
        return "Simple Reconciliation Agent"
    
    def get_agent_description(self) -> str:
        return "Reconciles clinical information and identifies conflicts or duplicates."
    
    def get_agent_version(self) -> str:
        return "1.0.0"
    
    def get_system_instruction(self) -> str:
        return """You are a medical data reconciliation specialist. Your role is to resolve conflicts and inconsistencies in temporal medical data.

When given clinical information to reconcile:
1. Identify any conflicting dates or information
2. Detect duplicate or carry-forward information
3. Apply medical logic to resolve conflicts
4. Maintain data integrity and traceability
5. Document reconciliation decisions
6. Flag irreconcilable conflicts for review

Provide a clear summary of:
- What information was reconciled
- Any conflicts found and how they were resolved
- The final reconciled timeline
- Status of each piece of information (Final, In Process, Ordered, etc.)"""
    
    def get_tools(self):
        """No tools needed for simple text processing."""
        return None
    
    def supports_streaming(self) -> bool:
        """Enable streaming for real-time processing."""
        return True
    
    async def process_message(self, message: str) -> str:
        """
        Format the input message for LLM processing.
        
        This method is called by base.py before sending to the LLM.
        We format the input to provide clear structure for reconciliation.
        
        Args:
            message: The input message (may be JSON or text)
            
        Returns:
            Formatted message for the LLM
        """
        import json
        
        # Try to parse as JSON for better structure
        try:
            data = json.loads(message)
            
            # Format for reconciliation
            formatted = "Please reconcile the following clinical information:\n\n"
            
            if isinstance(data, dict):
                # Check for specific fields
                if "encounters" in data:
                    formatted += f"ENCOUNTER DATA:\n{json.dumps(data['encounters'], indent=2)}\n\n"
                
                if "temporal_data" in data:
                    formatted += f"TEMPORAL DATA:\n{data['temporal_data']}\n\n"
                
                if "facts" in data:
                    formatted += f"CLINICAL FACTS:\n{json.dumps(data['facts'], indent=2)}\n\n"
                
                # Add any other data
                other_keys = [k for k in data.keys() if k not in ["encounters", "temporal_data", "facts"]]
                if other_keys:
                    other_data = {k: data[k] for k in other_keys}
                    formatted += f"ADDITIONAL DATA:\n{json.dumps(other_data, indent=2)}\n"
            else:
                formatted += json.dumps(data, indent=2)
            
            formatted += "\nProvide reconciled data with status tags and conflict resolution."
            return formatted
            
        except json.JSONDecodeError:
            # Not JSON, treat as text
            return f"Please reconcile the following clinical information:\n\n{message}\n\nProvide reconciled data with status tags and conflict resolution."


# Module-level app creation (required for deployment)
agent = SimpleReconciliationAgent()
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
    port = int(os.getenv("PORT", 8012))
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host="0.0.0.0", port=port)