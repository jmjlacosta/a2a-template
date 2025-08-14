#!/usr/bin/env python3
"""
Multi-Agent Orchestrator - Coordinates multiple specialized agents.

This example demonstrates:
- Inter-agent communication using A2AAgentClient
- Agent registry for managing known agents
- Dynamic tool creation for each registered agent
- Parallel execution of agent tasks
- Result combination and synthesis

Usage:
    # First, deploy or run the other agents
    # Update config/agents.json with agent URLs
    export GOOGLE_API_KEY="your-key"  # or OPENAI_API_KEY or ANTHROPIC_API_KEY
    python orchestrator_agent.py

The orchestrator can:
- Discover and call registered agents
- Route tasks to appropriate specialists
- Combine results from multiple agents
- Execute agent calls in parallel
- Provide unified responses
"""

import os
import sys
import json
import asyncio
import uvicorn
from typing import List, Dict, Any
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import A2AAgent
from utils.a2a_client import A2AAgentClient, AgentRegistry
from google.adk import get_llm
from google.adk.tools import FunctionTool
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


class OrchestratorAgent(A2AAgent):
    """Coordinate multiple agents to solve complex tasks."""
    
    def __init__(self):
        super().__init__()
        self.client = A2AAgentClient()
        self.registry = AgentRegistry()
        self.available_agents = self._discover_agents()
        self._llm = None
        self._tools = None
        self._initialize_tools()
    
    def get_agent_name(self) -> str:
        return "Task Orchestrator"
    
    def get_agent_description(self) -> str:
        return "Orchestrates multiple specialized agents to handle complex tasks"
    
    def _initialize_tools(self):
        """Initialize orchestration tools."""
        tools = []
        
        # Create a tool for each registered agent
        for agent_name in self.available_agents:
            tools.append(self._create_agent_tool(agent_name))
        
        # Add orchestration-specific tools
        tools.extend([
            FunctionTool(self._parallel_execute),
            FunctionTool(self._sequential_execute),
            FunctionTool(self._combine_results)
        ])
        
        self._tools = tools
    
    async def process_message(self, message: str) -> str:
        """Process orchestration request using LLM with agent tools."""
        # Initialize LLM if needed
        if self._llm is None:
            system_instruction = self._get_system_instruction()
            self._llm = get_llm(system_instruction=system_instruction)
        
        # Generate response with tools
        response = self._llm.generate_text(
            prompt=message,
            tools=self._tools
        )
        
        return response
    
    def _get_system_instruction(self) -> str:
        agents_list = "\n".join([
            f"- {name}: {info.get('description', 'No description')}"
            for name, info in self.available_agents.items()
        ])
        
        return f"""You are a task orchestrator that coordinates multiple specialized agents.
        
Available agents:
{agents_list if agents_list else '- No agents configured (check config/agents.json)'}

Your role:
1. Analyze incoming requests to understand what needs to be done
2. Break down complex tasks into subtasks
3. Delegate subtasks to appropriate specialized agents
4. Combine and synthesize results from multiple agents
5. Provide comprehensive solutions

Guidelines:
- Use the most appropriate agent for each subtask
- Run independent tasks in parallel when possible
- Combine results intelligently
- Handle errors gracefully with fallback strategies
- Provide clear, unified responses

Remember: You're the conductor of an orchestra - coordinate the specialists to create harmony!"""
    
    def _discover_agents(self) -> Dict[str, Dict[str, Any]]:
        """Discover available agents from registry."""
        import logging
        logger = logging.getLogger(__name__)
        
        agents = {}
        for agent_name in self.registry.list_agents():
            agent_info = self.registry.get_agent_info(agent_name)
            if agent_info:
                agents[agent_name] = agent_info
                logger.info(f"Discovered agent: {agent_name}")
        
        if not agents:
            logger.warning("No agents found in registry. Check config/agents.json")
        
        return agents
    
    def _create_agent_tool(self, agent_name: str) -> FunctionTool:
        """Create a tool that calls another agent.
        
        Args:
            agent_name: Name of the agent to create a tool for
            
        Returns:
            FunctionTool that calls the specified agent
        """
        agent_info = self.available_agents.get(agent_name, {})
        agent_url = agent_info.get("url")
        description = agent_info.get("description", f"Call the {agent_name} agent")
        
        async def call_agent(message: str) -> str:
            f"""Call {agent_name} agent with a message.
            
            Args:
                message: The message to send to {agent_name}
                
            Returns:
                The agent's response
            """
            if not agent_url:
                return f"Error: No URL configured for {agent_name}"
            
            try:
                response = await self.client.call_agent(agent_url, message, timeout=30.0)
                return response
            except Exception as e:
                return f"Error calling {agent_name}: {str(e)}"
        
        # Set the function name dynamically
        call_agent.__name__ = f"call_{agent_name.replace('-', '_')}"
        
        return FunctionTool(call_agent)
    
    async def _parallel_execute(self, tasks: str) -> str:
        """Execute multiple agent calls in parallel.
        
        Args:
            tasks: JSON string containing list of tasks, each with 'agent' and 'message' fields
            
        Returns:
            JSON string with results from all agents
        """
        try:
            task_list = json.loads(tasks)
            if not isinstance(task_list, list):
                return json.dumps({"error": "Tasks must be a JSON array"})
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON format for tasks"})
        
        async def execute_task(task: Dict[str, str]) -> Dict[str, Any]:
            agent_name = task.get("agent")
            message = task.get("message")
            
            if not agent_name or not message:
                return {"error": "Task must have 'agent' and 'message' fields"}
            
            agent_info = self.available_agents.get(agent_name)
            if not agent_info:
                return {"error": f"Unknown agent: {agent_name}"}
            
            agent_url = agent_info.get("url")
            if not agent_url:
                return {"error": f"No URL for agent: {agent_name}"}
            
            try:
                result = await self.client.call_agent(agent_url, message, timeout=30.0)
                return {
                    "agent": agent_name,
                    "success": True,
                    "result": result
                }
            except Exception as e:
                return {
                    "agent": agent_name,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute all tasks in parallel
        results = await asyncio.gather(
            *[execute_task(task) for task in task_list]
        )
        
        return json.dumps({
            "execution": "parallel",
            "total_tasks": len(task_list),
            "results": results
        }, indent=2)
    
    async def _sequential_execute(self, tasks: str) -> str:
        """Execute agent calls sequentially, passing results between them.
        
        Args:
            tasks: JSON string containing list of tasks in sequence
            
        Returns:
            JSON string with results from the pipeline
        """
        try:
            task_list = json.loads(tasks)
            if not isinstance(task_list, list):
                return json.dumps({"error": "Tasks must be a JSON array"})
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON format for tasks"})
        
        results = []
        previous_result = None
        
        for i, task in enumerate(task_list):
            agent_name = task.get("agent")
            message = task.get("message")
            
            # If use_previous_result is true, append previous result to message
            if task.get("use_previous_result") and previous_result:
                message = f"{message}\n\nPrevious result:\n{previous_result}"
            
            agent_info = self.available_agents.get(agent_name)
            if not agent_info:
                results.append({
                    "step": i + 1,
                    "agent": agent_name,
                    "error": f"Unknown agent: {agent_name}"
                })
                break
            
            agent_url = agent_info.get("url")
            try:
                result = await self.client.call_agent(agent_url, message, timeout=30.0)
                results.append({
                    "step": i + 1,
                    "agent": agent_name,
                    "success": True,
                    "result": result
                })
                previous_result = result
            except Exception as e:
                results.append({
                    "step": i + 1,
                    "agent": agent_name,
                    "success": False,
                    "error": str(e)
                })
                break
        
        return json.dumps({
            "execution": "sequential",
            "total_steps": len(results),
            "results": results
        }, indent=2)
    
    def _combine_results(self, results: str) -> str:
        """Combine and summarize results from multiple agents.
        
        Args:
            results: JSON string containing results to combine
            
        Returns:
            Combined and summarized results
        """
        try:
            results_data = json.loads(results)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON format for results"})
        
        combined = {
            "summary": "Combined results from multiple agents",
            "total_results": len(results_data) if isinstance(results_data, list) else 1,
            "combined_data": results_data
        }
        
        # Extract successful results
        if isinstance(results_data, list):
            successful = [r for r in results_data if r.get("success")]
            failed = [r for r in results_data if not r.get("success")]
            
            combined["successful_count"] = len(successful)
            combined["failed_count"] = len(failed)
            
            if failed:
                combined["failures"] = [
                    {"agent": f.get("agent"), "error": f.get("error")}
                    for f in failed
                ]
        
        return json.dumps(combined, indent=2)


# Module-level app creation for HealthUniverse deployment
agent = OrchestratorAgent()
agent_card = agent.create_agent_card()
task_store = InMemoryTaskStore()
request_handler = DefaultRequestHandler(
    agent_executor=agent,
    task_store=task_store
)

# Create the app - for HealthUniverse deployment
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
).build()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8004))
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host="0.0.0.0", port=port)