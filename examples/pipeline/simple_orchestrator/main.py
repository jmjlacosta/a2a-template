#!/usr/bin/env python3
"""
Entry point for Simple Orchestrator Agent.
Starts a uvicorn server exposing the orchestrator over A2A.
"""

import os
import uvicorn
import logging

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from examples.pipeline.simple_orchestrator.simple_orchestrator_agent import SimpleOrchestratorAgent

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    # 1. Create the agent
    agent = SimpleOrchestratorAgent()

    # 2. Build agent card + request handler
    agent_card = agent.create_agent_card()
    task_store = InMemoryTaskStore()
    request_handler = DefaultRequestHandler(
        agent_executor=agent, task_store=task_store
    )

    # 3. Build the app (must be called `app` for HU deployment)
    app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    ).build()

    # 4. Run with uvicorn
    host = "0.0.0.0"
    port = int(os.getenv("AGENT_PORT", "8008"))

    print(f"🚀 {agent.get_agent_name()} running on {host}:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agentcard.json")

    uvicorn.run(app, host=host, port=port, log_level="info")
