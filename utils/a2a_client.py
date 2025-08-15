"""
A2A Agent Client for inter-agent communication.
Simplified interface for calling other A2A-compliant agents.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, AsyncIterator, List
from datetime import datetime
import httpx

from a2a.types import (
    AgentCard,
    Task,
    TaskState,
    Message,
    Part,
    TextPart
)
from a2a.utils import new_task, new_agent_text_message

logger = logging.getLogger(__name__)


class A2AAgentClient:
    """
    Simplified client for calling other A2A agents.
    Handles agent card fetching, task lifecycle, and response processing.
    """
    
    def __init__(
        self,
        timeout: float = 30.0,
        cache_agent_cards: bool = True,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize A2A agent client.
        
        Args:
            timeout: Default timeout for agent calls
            cache_agent_cards: Whether to cache fetched agent cards
            headers: Additional headers for requests
        """
        self.timeout = timeout
        self.cache_agent_cards = cache_agent_cards
        self.agent_card_cache: Dict[str, AgentCard] = {}
        self.headers = headers or {}
        self.client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self.client:
            self.client = httpx.AsyncClient(timeout=self.timeout)
        return self.client
    
    async def fetch_agent_card(self, agent_url: str) -> AgentCard:
        """
        Fetch agent card from well-known endpoint.
        
        Args:
            agent_url: Base URL of the agent
            
        Returns:
            AgentCard object
        """
        # Check cache first
        if self.cache_agent_cards and agent_url in self.agent_card_cache:
            logger.debug(f"Using cached agent card for {agent_url}")
            return self.agent_card_cache[agent_url]
        
        # Try both possible well-known endpoints
        # A2A spec is inconsistent - examples show agent-card.json (with hyphen)
        # but spec text shows agentcard.json (no hyphen)
        # HealthUniverse may use agent.json
        possible_endpoints = [
            f"{agent_url}/.well-known/agent-card.json",  # Most common, used in examples
            f"{agent_url}/.well-known/agent.json",       # HealthUniverse might use this
            f"{agent_url}/.well-known/agentcard.json"    # Spec section 5.3 says this
        ]
        
        client = await self._get_client()
        last_error = None
        
        for card_url in possible_endpoints:
            try:
                logger.info(f"Fetching agent card from {card_url}")
                response = await client.get(card_url, headers=self.headers)
                response.raise_for_status()
                
                card_data = response.json()
                # Note: A2A spec requires camelCase in JSON (e.g., protocolVersion)
                # but Python SDK converts to snake_case for attribute access
                agent_card = AgentCard(**card_data)
                
                # Cache if enabled
                if self.cache_agent_cards:
                    self.agent_card_cache[agent_url] = agent_card
                
                logger.info(f"Fetched agent card: {agent_card.name} v{agent_card.version}")
                return agent_card
                
            except Exception as e:
                last_error = e
                logger.debug(f"Failed to fetch from {card_url}: {e}")
                continue
        
        # If we get here, all attempts failed
        raise last_error or Exception(f"Failed to fetch agent card from {agent_url}")
    
    async def call_agent(
        self,
        agent_url: str,
        message: str,
        timeout: Optional[float] = None,
        context_id: Optional[str] = None
    ) -> str:
        """
        Call an agent with a text message and get text response.
        
        Args:
            agent_url: URL of the agent to call
            message: Text message to send
            timeout: Optional timeout override
            context_id: Optional context ID for conversation continuity
            
        Returns:
            Agent's text response
        """
        # Fetch agent card
        agent_card = await self.fetch_agent_card(agent_url)
        
        # Create message
        msg = new_agent_text_message(message)
        
        # Create task
        task = new_task(msg)
        if context_id:
            task.context_id = context_id
        
        # Send JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": msg.dict(),
                "task_id": task.id,
                "context_id": context_id
            },
            "id": datetime.now().isoformat()
        }
        
        logger.info(f"Calling agent {agent_card.name} with message")
        
        client = await self._get_client()
        response = await client.post(
            agent_url,
            json=request,
            headers={**self.headers, "Content-Type": "application/json"},
            timeout=timeout or self.timeout
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Handle JSON-RPC response
        if "error" in result:
            error = result["error"]
            # Use proper A2A error codes
            error_code = error.get("code", -32603)
            error_message = error.get("message", "Unknown error")
            error_data = error.get("data")
            
            # Map to specific exceptions based on error code
            if error_code == -32001:
                raise ValueError(f"Task not found: {error_message}")
            elif error_code == -32002:
                raise ValueError(f"Task not cancelable: {error_message}")
            elif error_code == -32003:
                raise ValueError(f"Push notifications not supported: {error_message}")
            elif error_code == -32004:
                raise ValueError(f"Unsupported operation: {error_message}")
            elif error_code == -32005:
                raise ValueError(f"Content type not supported: {error_message}")
            elif error_code == -32006:
                raise ValueError(f"Invalid agent response: {error_message}")
            elif error_code == -32007:
                raise ValueError(f"No authenticated extended card: {error_message}")
            else:
                raise Exception(f"Agent error {error_code}: {error_message}")
        
        # Extract text from response
        if "result" in result:
            task_result = result["result"]
            
            # Check for artifacts (completed response)
            if "artifacts" in task_result and task_result["artifacts"]:
                artifact = task_result["artifacts"][0]
                if "parts" in artifact and artifact["parts"]:
                    part = artifact["parts"][0]
                    if "text" in part:
                        return part["text"]
            
            # Check for message in history
            if "history" in task_result and task_result["history"]:
                last_msg = task_result["history"][-1]
                if "parts" in last_msg and last_msg["parts"]:
                    part = last_msg["parts"][0]
                    if "text" in part:
                        return part["text"]
            
            # Check status for working state (may need polling)
            if "status" in task_result:
                status = task_result["status"]
                if status.get("state") == "working":
                    # For simplicity, return status message
                    return "Agent is processing your request..."
        
        return "No response from agent"
    
    async def call_agent_json(
        self,
        agent_url: str,
        data: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Call an agent with JSON data and get JSON response.
        
        Args:
            agent_url: URL of the agent to call
            data: JSON data to send
            timeout: Optional timeout override
            
        Returns:
            Agent's JSON response
        """
        # Convert dict to JSON string for sending
        message = json.dumps(data)
        
        # Call agent
        response = await self.call_agent(agent_url, message, timeout)
        
        # Try to parse response as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Return as dict with text key if not JSON
            return {"response": response}
    
    async def stream_agent_response(
        self,
        agent_url: str,
        message: str,
        context_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Stream responses from an agent using SSE.
        
        Args:
            agent_url: URL of the agent to call
            message: Text message to send
            context_id: Optional context ID
            
        Yields:
            Response chunks as they arrive
        """
        # Fetch agent card
        agent_card = await self.fetch_agent_card(agent_url)
        
        # Check if agent supports streaming
        if not agent_card.capabilities or not agent_card.capabilities.streaming:
            # Fall back to regular call
            result = await self.call_agent(agent_url, message, context_id=context_id)
            yield result
            return
        
        # Create message and task
        msg = new_agent_text_message(message)
        task = new_task(msg)
        if context_id:
            task.context_id = context_id
        
        # Send streaming request
        request = {
            "jsonrpc": "2.0",
            "method": "message/stream",
            "params": {
                "message": msg.dict(),
                "task_id": task.id,
                "context_id": context_id
            },
            "id": datetime.now().isoformat()
        }
        
        logger.info(f"Streaming from agent {agent_card.name}")
        
        client = await self._get_client()
        
        # Use SSE streaming
        async with client.stream(
            "POST",
            agent_url,
            json=request,
            headers={**self.headers, "Content-Type": "application/json"}
        ) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix
                    try:
                        event = json.loads(data)
                        
                        # Extract text from different event types
                        if "result" in event:
                            result = event["result"]
                            
                            # Check for artifact chunks
                            if "artifact" in result:
                                artifact = result["artifact"]
                                if "parts" in artifact:
                                    for part in artifact["parts"]:
                                        if "text" in part:
                                            yield part["text"]
                            
                            # Check for status updates
                            if "status" in result:
                                status = result["status"]
                                if status.get("final"):
                                    # Stream complete
                                    break
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse SSE data: {data}")
                        continue
    
    async def close(self):
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None


class AgentRegistry:
    """
    Manage known agents from configuration.
    Provides a registry of available agents and their endpoints.
    
    IMPORTANT: In HealthUniverse deployment, each agent runs in its own Kubernetes container.
    The agents.json file must be manually configured BEFORE deploying the orchestrator:
    1. Deploy all required agents first
    2. Note each agent's xxx-xxx-xxx code from HealthUniverse (e.g., vey-vou-nam)
    3. Update config/agents.json with URLs: https://apps.healthuniverse.com/xxx-xxx-xxx
    4. Commit and push to Git
    5. Deploy the orchestrator
    
    Future versions will auto-populate this, but for now it's a manual process.
    """
    
    def __init__(self, config_path: str = "config/agents.json"):
        """
        Initialize agent registry.
        
        Args:
            config_path: Path to agents configuration file
        """
        self.config_path = config_path
        self.agents = self._load_agents()
    
    def _load_agents(self) -> Dict[str, Dict[str, Any]]:
        """Load agents from configuration file."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Agent config not found at {self.config_path}")
            return {}
        
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                return config.get("agents", {})
        except Exception as e:
            logger.error(f"Failed to load agent config: {e}")
            return {}
    
    def get_agent_url(self, name: str) -> Optional[str]:
        """
        Get agent URL by name.
        
        Args:
            name: Agent name
            
        Returns:
            Agent URL or None if not found
        """
        agent = self.agents.get(name, {})
        return agent.get("url")
    
    def get_agent_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get full agent information.
        
        Args:
            name: Agent name
            
        Returns:
            Agent info dict or None
        """
        return self.agents.get(name)
    
    def list_agents(self) -> List[str]:
        """
        List all registered agent names.
        
        Returns:
            List of agent names
        """
        return list(self.agents.keys())
    
    def add_agent(self, name: str, url: str, **kwargs):
        """
        Add or update an agent in the registry (IN MEMORY ONLY).
        
        NOTE: This only updates the in-memory registry. In Kubernetes deployments,
        changes will be lost when the container restarts. Update config/agents.json
        in your Git repository and redeploy to make permanent changes.
        
        Args:
            name: Agent name
            url: Agent URL
            **kwargs: Additional agent properties
        """
        self.agents[name] = {
            "url": url,
            **kwargs
        }
        logger.warning(f"Added agent '{name}' to in-memory registry only. "
                      "Update config/agents.json and redeploy for permanent changes.")
    
    def remove_agent(self, name: str) -> bool:
        """
        Remove an agent from the registry (IN MEMORY ONLY).
        
        NOTE: This only updates the in-memory registry. In Kubernetes deployments,
        changes will be lost when the container restarts.
        
        Args:
            name: Agent name
            
        Returns:
            True if removed, False if not found
        """
        if name in self.agents:
            del self.agents[name]
            logger.warning(f"Removed agent '{name}' from in-memory registry only. "
                          "Update config/agents.json and redeploy for permanent changes.")
            return True
        return False
    
    def reload(self):
        """
        Reload the registry from the configuration file.
        Useful if the config file was updated via ConfigMap in Kubernetes.
        """
        logger.info(f"Reloading agent registry from {self.config_path}")
        self.agents = self._load_agents()
        logger.info(f"Loaded {len(self.agents)} agents from configuration")