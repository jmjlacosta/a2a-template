"""
Enhanced A2A client with JSON-RPC support and production features.
~210 LOC - Production-ready client with retry, auth, and debug logging.
Uses JSON-RPC protocol to match A2AStarletteApplication server.
"""

import os
import json
import time
import random
import logging
import asyncio
import aiohttp
import itertools
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager


logger = logging.getLogger(__name__)

# Global counter for JSON-RPC request IDs
_jsonrpc_id_counter = itertools.count(1)


def _jsonrpc_envelope(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a JSON-RPC 2.0 request envelope.
    
    Args:
        method: The RPC method name (e.g., "message", "task.create")
        params: The method parameters
        
    Returns:
        JSON-RPC request dictionary
    """
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": next(_jsonrpc_id_counter)
    }


class A2AClient:
    """Enhanced A2A client with JSON-RPC and DataPart support."""
    
    def __init__(self, base_url: str, token: Optional[str] = None):
        """
        Initialize A2A client.
        
        Args:
            base_url: Base URL for the A2A server (no /a2a/v1 suffix for JSON-RPC)
            token: Optional bearer token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.token = token or os.getenv("AGENT_TOKEN")
        self.debug_payloads = os.getenv("DEBUG_PAYLOADS") == "1"
        self.session = None
        
    @classmethod
    def from_registry(cls, agent_name: str, token: Optional[str] = None):
        """
        Create client from registry.
        
        Args:
            agent_name: Name of agent in registry
            token: Optional bearer token
            
        Returns:
            A2AClient instance
            
        Raises:
            ValueError: If agent not found in registry
        """
        from .registry import resolve_agent_url
        return cls(resolve_agent_url(agent_name), token)
        
    @asynccontextmanager
    async def _get_session(self):
        """Get or create aiohttp session."""
        if self.session is None:
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            self.session = aiohttp.ClientSession(headers=headers)
        try:
            yield self.session
        finally:
            pass
    
    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _request_jsonrpc(self, method: str, params: Dict[str, Any], 
                               retries: int = 3, timeout_sec: Optional[float] = None) -> Any:
        """
        Make JSON-RPC request with retries.
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
            retries: Number of retry attempts
            timeout_sec: Request timeout in seconds
            
        Returns:
            The result from the JSON-RPC response
            
        Raises:
            aiohttp.ClientError: On network errors
            ValueError: On JSON-RPC errors
        """
        endpoint = self.base_url  # JSON-RPC posts to root
        payload = _jsonrpc_envelope(method, params)
        
        if self.debug_payloads:
            logger.debug(f"JSON-RPC Request to {endpoint}:")
            logger.debug(json.dumps(payload, indent=2))
        
        for attempt in range(retries):
            try:
                async with self._get_session() as session:
                    timeout = aiohttp.ClientTimeout(total=timeout_sec or 30.0)
                    
                    async with session.post(endpoint, json=payload, timeout=timeout) as response:
                        response_text = await response.text()
                        
                        if self.debug_payloads:
                            logger.debug(f"JSON-RPC Response ({response.status}):")
                            logger.debug(response_text[:1000])
                        
                        if response.status >= 400:
                            if attempt < retries - 1:
                                await asyncio.sleep(2 ** attempt + random.random())
                                continue
                            raise aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=response.status,
                                message=f"JSON-RPC request failed: {response_text}"
                            )
                        
                        # Parse JSON-RPC response
                        try:
                            data = json.loads(response_text)
                        except json.JSONDecodeError:
                            raise ValueError(f"Invalid JSON response: {response_text[:200]}")
                        
                        # Check for JSON-RPC error
                        if "error" in data:
                            error = data["error"]
                            raise ValueError(f"JSON-RPC error {error.get('code')}: {error.get('message')}")
                        
                        # Return the result
                        return data.get("result", data)
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < retries - 1:
                    logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
                    await asyncio.sleep(2 ** attempt + random.random())
                else:
                    raise
    
    async def send_message(self, message: Any, timeout_sec: Optional[float] = None) -> str:
        """
        Send a message to the agent via JSON-RPC.
        
        Args:
            message: Message object or dict with role and parts
            timeout_sec: Request timeout
            
        Returns:
            Text response from agent
        """
        # Convert message to dict if needed
        if hasattr(message, 'model_dump'):
            message_dict = message.model_dump()
        elif hasattr(message, 'dict'):
            message_dict = message.dict()
        else:
            message_dict = message
        
        # Ensure message has required structure
        if not isinstance(message_dict, dict):
            message_dict = {
                "role": "user",
                "parts": [{"kind": "text", "text": str(message_dict)}],
                "kind": "message"
            }
        elif "role" not in message_dict:
            message_dict = {
                "role": "user",
                "parts": [{"kind": "text", "text": str(message_dict)}],
                "kind": "message"
            }
        
        # Add messageId if not present
        if "messageId" not in message_dict:
            import uuid
            message_dict["messageId"] = str(uuid.uuid4())
        
        # Send via JSON-RPC with correct method name
        params = {
            "message": message_dict,
            "metadata": {}
        }
        
        result = await self._request_jsonrpc("message/send", params, timeout_sec=timeout_sec)
        
        # Extract text from various response formats
        if isinstance(result, str):
            return result
        
        if isinstance(result, dict):
            # Direct text field
            if "text" in result:
                return result["text"]
            
            # Message with parts
            msg = result.get("message") or result.get("result", {}).get("message")
            if isinstance(msg, dict):
                parts = msg.get("parts", [])
                texts = []
                for part in parts:
                    if part.get("kind") == "text":
                        texts.append(part.get("text", ""))
                    elif part.get("kind") == "data":
                        # Handle DataPart responses
                        data = part.get("data", {})
                        if isinstance(data, dict):
                            texts.append(json.dumps(data, indent=2))
                        else:
                            texts.append(str(data))
                return "\n".join(texts)
        
        return str(result)


# Convenience function for backwards compatibility
async def call_agent(agent_url: str, message: str, timeout: float = 30.0) -> str:
    """
    Call an agent with a simple text message.
    
    Args:
        agent_url: Agent URL or name (resolved via registry)
        message: Text message to send
        timeout: Request timeout in seconds
        
    Returns:
        Agent's text response
    """
    client = A2AClient.from_registry(agent_url) if not agent_url.startswith("http") else A2AClient(agent_url)
    try:
        return await client.send_message(message, timeout_sec=timeout)
    finally:
        await client.close()