#!/usr/bin/env python3
"""
Hybrid Reconciliation Agent - Uses simplified tools to preserve verification functionality.
Maintains critical deduplication and status tagging capabilities.
"""

import os
import sys
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base import A2AAgent
# GITHUB ISSUE FIX: Using fixed tools with all functionality
from tools.reconciliation_tools import RECONCILIATION_TOOLS
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


class HybridReconciliationAgent(A2AAgent):
    """Hybrid reconciliation agent with simplified tools for verification."""
    
    def get_agent_name(self) -> str:
        return "Hybrid Reconciliation Agent"
    
    def get_agent_description(self) -> str:
        return "Reconciles clinical data with deduplication, status tagging, and cross-encounter analysis."
    
    def get_system_instruction(self) -> str:
        return """You are a medical data reconciliation specialist with access to verification tools.
Your role is to resolve conflicts and inconsistencies in temporal medical data while maintaining accuracy.

CRITICAL RESPONSIBILITIES:
1. **Deduplication**: Use the detect_duplicates tool to identify repeated information
2. **Status Tagging**: Apply Final/Corrected/In Process/Ordered status to each fact
3. **Provenance Tracking**: Mark facts as Primary/Updated/Previously Reported
4. **Cross-Encounter Analysis**: Track how facts evolve across visits
5. **Conflict Resolution**: Apply medical logic to resolve inconsistencies
6. **Confidence Scoring**: Assign confidence levels to reconciled facts

When reconciling:
- ALWAYS use tools to verify duplicates and assign status
- Maintain source references for traceability
- Flag irreconcilable conflicts for review
- Preserve all unique clinical information
- Document reconciliation decisions

Output Format:
Return reconciled data as structured JSON with:
{
  "reconciled_facts": [
    {
      "content": "fact text",
      "status": "Final|Corrected|In Process|Ordered",
      "provenance": "Primary|Updated|Previously Reported",
      "confidence": 0.95,
      "encounter_date": "YYYY-MM-DD",
      "is_carry_forward": false
    }
  ],
  "duplicates_removed": count,
  "conflicts_resolved": count,
  "irreconcilable_conflicts": []
}"""
    
    def get_tools(self) -> List:
        """Return reconciliation tools."""
        return RECONCILIATION_TOOLS
    
    def supports_streaming(self) -> bool:
        """Enable streaming for real-time processing."""
        return True
    
    async def process_message(self, message: str) -> str:
        """
        Format message for tool-based processing.
        
        The tools will be invoked by the LLM to perform reconciliation.
        """
        import json
        
        # Format the input to guide tool usage
        try:
            data = json.loads(message)
            
            instructions = """Reconcile this clinical data using the available tools:

1. First, use detect_duplicates to identify repeated information
2. Then use assign_status_tags for each unique fact
3. Use reconcile_encounter_json for comprehensive reconciliation
4. If multiple encounters, use cross_encounter_analysis
5. Return fully reconciled data with all metadata

INPUT DATA:
"""
            
            if isinstance(data, dict):
                instructions += json.dumps(data, indent=2)
            else:
                instructions += str(data)
                
            return instructions
            
        except json.JSONDecodeError:
            # Plain text input
            return f"""Reconcile this clinical information using available tools:

{message}

Use tools to detect duplicates, assign status tags, and perform reconciliation."""


# Module-level app creation (required for deployment)
agent = HybridReconciliationAgent()
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
    print(f"🛠️ Tools: {len(agent.get_tools())} reconciliation tools with fixed signatures")
    print(f"✓ Deduplication | ✓ Status tagging | ✓ Cross-encounter | ✓ Summary | ✓ Registry")
    uvicorn.run(app, host="0.0.0.0", port=port)