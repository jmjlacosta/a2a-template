"""
App builder with A2A compliance endpoints.
Adds well-known and health endpoints to the Starlette app.
"""

import json
from typing import Any, Dict
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from a2a.types import AgentCard
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import RequestHandler


def create_compliant_app(
    agent_card: AgentCard,
    request_handler: RequestHandler,
    agent_name: str = None
) -> Starlette:
    """
    Create a Starlette app with A2A compliance endpoints.
    
    Args:
        agent_card: The agent's card
        request_handler: The request handler
        agent_name: Optional agent name for health endpoint
        
    Returns:
        Configured Starlette application
    """
    # Create base A2A app
    base_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    ).build()
    
    # Add compliance endpoints
    
    async def well_known_agent_card(request):
        """Serve agent card at A2A spec well-known URI."""
        # Use by_alias=True to get camelCase field names as required by A2A spec
        return JSONResponse(agent_card.model_dump(by_alias=True))
    
    async def well_known_agent(request):
        """Serve agent card at HealthUniverse expected URI."""
        # Use by_alias=True to get camelCase field names as required by A2A spec
        return JSONResponse(agent_card.model_dump(by_alias=True))
    
    async def health_check(request):
        """Health check endpoint for platform monitoring."""
        return JSONResponse({
            "status": "healthy",
            "agent": agent_name or agent_card.name,
            "version": agent_card.version,
            "protocol": agent_card.protocol_version,
            "capabilities": {
                "streaming": agent_card.capabilities.streaming if agent_card.capabilities else False,
                "push_notifications": agent_card.capabilities.push_notifications if agent_card.capabilities else False,
            }
        })
    
    # Add routes to the app
    additional_routes = [
        Route("/.well-known/agent-card.json", well_known_agent_card, methods=["GET"]),  # A2A spec compliant
        Route("/.well-known/agent.json", well_known_agent, methods=["GET"]),  # HealthUniverse expected
        Route("/health", health_check, methods=["GET"]),
    ]
    
    # Create new app with all routes
    # IMPORTANT: Put our routes FIRST to override SDK's default endpoints
    all_routes = additional_routes + list(base_app.routes)
    
    app = Starlette(
        routes=all_routes,
        debug=False
    )
    
    # Copy middleware from base app
    app.middleware_stack = base_app.middleware_stack
    
    return app