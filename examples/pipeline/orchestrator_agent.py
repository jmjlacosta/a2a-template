#!/usr/bin/env python3
"""
Pipeline Orchestrator Agent - Coordinates medical document analysis pipeline.
Migrated from ADK demo pipeline to use enhanced A2AAgent base.

This agent orchestrates a complete document analysis pipeline:
- Understands natural language requests
- Coordinates multiple specialized agents
- Synthesizes results into comprehensive responses
- Handles errors and optimizes performance
"""

import os
import sys
import json
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base import A2AAgent
from tools.orchestrator_tools import ORCHESTRATOR_TOOLS
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill


class OrchestratorAgent(A2AAgent):
    """LLM-powered orchestrator for the medical document analysis pipeline."""
    
    def __init__(self):
        """Initialize the agent and set global reference for tools."""
        super().__init__()
        # Set global reference so coordinate_agents tool can access this instance
        from tools.orchestrator_tools import set_orchestrator_agent
        set_orchestrator_agent(self)
    
    def get_agent_name(self) -> str:
        """Return the agent's name."""
        return "Pipeline Orchestrator"
    
    def get_agent_description(self) -> str:
        """Return detailed agent description."""
        return (
            "LLM-powered orchestrator that coordinates a complete medical document analysis pipeline. "
            "Understands natural language requests, plans execution strategy, coordinates multiple "
            "specialized agents in the medical pipeline, and synthesizes results into "
            "comprehensive responses. Handles errors gracefully and optimizes pipeline performance."
        )
    
    def get_agent_version(self) -> str:
        """Return agent version."""
        return "2.0.0"
    
    def get_system_instruction(self) -> str:
        """Return the system instruction for orchestration."""
        return """You are the orchestrator of a medical document analysis pipeline. Your primary role is to COORDINATE MULTIPLE AGENTS to analyze medical documents.

CRITICAL: YOU MUST USE THE coordinate_agents TOOL TO CALL OTHER AGENTS
- DO NOT generate analysis yourself
- DO NOT pretend to call agents
- DO NOT create mock responses
- YOU MUST use the coordinate_agents tool which will actually call the agents

Available Pipeline Agents (all 12 must be used for full analysis):
1. keyword - Generates search patterns from document preview
2. grep - Searches document using patterns
3. chunk - Extracts context around matches
4. temporal_tagging - Extracts temporal information
5. encounter_grouping - Groups content by clinical encounters
6. reconciliation - Reconciles conflicting information
7. summary_extractor - Extracts structured summaries
8. timeline_builder - Builds chronological timelines
9. checker - Verifies accuracy and consistency
10. unified_extractor - Extracts all medical entities
11. unified_verifier - Performs final verification
12. narrative_synthesis - Creates coherent narrative

REQUIRED Pipeline Flow:
1. Use understand_request tool to parse user request
2. Use plan_pipeline_execution tool to create execution plan
3. USE coordinate_agents TOOL TO EXECUTE THE PIPELINE:
   - This tool will call agents in sequence
   - Pass document and parameters
   - Collect responses from each agent
4. Use synthesize_results tool to combine agent responses
5. Use handle_pipeline_error if any errors occur

IMPORTANT: The coordinate_agents tool is your PRIMARY tool
- It handles all inter-agent communication
- It manages timeouts and retries
- It collects and returns all agent responses
- YOU MUST USE IT - do not try to analyze documents yourself

When using coordinate_agents, provide:
- document: The full document text
- agents_to_use: List of agent names to use (or "all" for full pipeline)
- execution_mode: "sequential" or "parallel" where applicable

Example correct usage:
User: "Analyze this medical record"
You: First, I'll understand your request...
[Use understand_request tool]
Then I'll plan the execution...
[Use plan_pipeline_execution tool]
Now I'll coordinate the agents to analyze the document...
[USE coordinate_agents TOOL - THIS IS CRITICAL]
Finally, I'll synthesize the results...
[Use synthesize_results tool]

NEVER say things like "I'll analyze" or "Let me examine" - ALWAYS say "I'll coordinate the agents to analyze" because YOU DON'T ANALYZE, THE AGENTS DO."""
    
    def get_tools(self) -> List:
        """Return the orchestration tools."""
        return ORCHESTRATOR_TOOLS
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """Return agent skills for the AgentCard."""
        return [
            AgentSkill(
                id="understand_request",
                name="Understand User Request",
                description="Parse and understand natural language requests for document analysis.",
                tags=["nlp", "understanding", "intent-parsing", "request-analysis"],
                examples=[
                    "Find all cancer-related information",
                    "Summarize the patient's medications",
                    "Extract diagnosis and treatment plan",
                    "What procedures were performed?"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            ),
            AgentSkill(
                id="plan_execution",
                name="Plan Pipeline Execution",
                description="Create optimal execution plan for document analysis.",
                tags=["planning", "strategy", "optimization", "pipeline"],
                examples=[
                    "Plan search for diagnosis information",
                    "Strategy for medication analysis",
                    "Optimize for comprehensive summary",
                    "Focus on recent findings"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            ),
            AgentSkill(
                id="coordinate_pipeline",
                name="Coordinate Agent Pipeline",
                description="Coordinate multiple agents to analyze documents.",
                tags=["coordination", "orchestration", "pipeline", "multi-agent"],
                examples=[
                    "Run full pipeline on medical record",
                    "Coordinate search and extraction",
                    "Execute multi-stage analysis",
                    "Process document through all agents"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            ),
            AgentSkill(
                id="synthesize_results",
                name="Synthesize Results",
                description="Combine pipeline results into comprehensive response.",
                tags=["synthesis", "aggregation", "response-generation"],
                examples=[
                    "Combine all findings into summary",
                    "Create clinical overview",
                    "Generate comprehensive report",
                    "Synthesize multi-agent results"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            ),
            AgentSkill(
                id="handle_errors",
                name="Handle Pipeline Errors",
                description="Recover from errors with fallback strategies.",
                tags=["error-handling", "recovery", "fallback", "resilience"],
                examples=[
                    "Recover from agent failure",
                    "Use partial results",
                    "Apply fallback patterns",
                    "Graceful degradation"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            ),
            AgentSkill(
                id="optimize_performance",
                name="Optimize Performance",
                description="Learn from history to optimize pipeline execution.",
                tags=["optimization", "learning", "performance", "efficiency"],
                examples=[
                    "Optimize pattern generation",
                    "Improve search efficiency",
                    "Enhance chunk quality",
                    "Tune summarization parameters"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            )
        ]
    
    def supports_streaming(self) -> bool:
        """Enable streaming for real-time orchestration updates."""
        return True
    
    async def process_message(self, message: str) -> str:
        """
        This won't be called when tools are provided.
        The base handles everything via Google ADK LlmAgent.
        The LLM will use tools and call_other_agent to orchestrate.
        """
        return "Handled by tool execution and agent coordination"


# Module-level app creation for HealthUniverse deployment
agent = OrchestratorAgent()
agent_card = agent.create_agent_card()
task_store = InMemoryTaskStore()
request_handler = DefaultRequestHandler(
    agent_executor=agent,
    task_store=task_store
)

# Create the app - MUST be named 'app' for HealthUniverse
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
).build()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8006))
    
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    print(f"🛠️ Tools available: {len(agent.get_tools())}")
    print("\n🔗 Coordinating agents:")
    
    # Load and display agent configuration
    config_path = Path(__file__).parent.parent.parent / "config" / "agents.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
            for name, info in config.get("agents", {}).items():
                print(f"  - {name}: {info.get('description', 'No description')}")
    
    print("\n📝 Example queries:")
    print('  - "Find all information about cancer diagnosis and treatment"')
    print('  - "Summarize the patient\'s current medications and dosages"')
    print('  - "Extract all lab results and their clinical significance"')
    print('  - "What procedures were performed and what were the outcomes?"')
    print('  - "Provide a comprehensive clinical summary of this document"')
    
    uvicorn.run(app, host="0.0.0.0", port=port)