#!/usr/bin/env python3
"""
Main entry point for A2A agent deployment on HealthUniverse.
This follows the standard pattern expected by HealthUniverse.
"""

import os
import uvicorn
from examples.regulatory_compliance_agent import RegulatoryComplianceAgent
from base.app_builder import create_compliant_app
from a2a.server.request_handlers import TaskRequestHandler
from a2a.server.tasks import InMemoryTaskStore

# Create the agent instance
agent = RegulatoryComplianceAgent()

# Create agent card
agent_card = agent._create_agent_card()

# Create task store and request handler
task_store = InMemoryTaskStore()
request_handler = TaskRequestHandler(
    agent=agent,
    task_store=task_store
)

# Create the app - THIS IS THE KEY VARIABLE HEALTHUNIVERSE EXPECTS
app = create_compliant_app(
    agent_card=agent_card,
    request_handler=request_handler,
    agent_name=agent.get_agent_name()
)

# Main entry point
if __name__ == "__main__":
    # Get port from environment or default
    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0"
    
    # Log startup info
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Agent URL: {os.getenv('HU_APP_URL', f'http://localhost:{port}')}")
    print(f"🔗 A2A endpoint: /.well-known/agent-card.json")
    print(f"🔗 HU endpoint: /.well-known/agent.json")
    print(f"💚 Health endpoint: /health")
    
    # Run the server
    uvicorn.run(app, host=host, port=port)