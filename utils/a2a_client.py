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
import uuid
from typing import Dict, Any, Optional, Union
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
        self.token = token or os.getenv("AGENT_TOKEN") or os.getenv("HU_TOKEN")
        self.debug_payloads = os.getenv("DEBUG_PAYLOADS") == "1"
        self.debug_auth = os.getenv("DEBUG_AUTH", "false").lower() == "true"
        self.session = None
        
        # Debug authentication setup
        if self.debug_auth:
            logger.info(f"A2A Client initialized for {self.base_url}")
            logger.info(f"Token source: {'AGENT_TOKEN' if os.getenv('AGENT_TOKEN') else 'HU_TOKEN' if os.getenv('HU_TOKEN') else 'None'}")
            logger.info(f"Token present: {'Yes' if self.token else 'No'}")
            if self.token:
                logger.info(f"Token prefix: {self.token[:20]}..." if len(self.token) > 20 else f"Token: {self.token}")
        
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
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "A2A-Client/1.0.0",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "Cache-Control": "no-cache"
            }
            
            # Add authentication if token is available
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
                
            # Add Health Universe specific headers if in HU environment
            if "healthuniverse.com" in self.base_url:
                headers["Origin"] = "https://healthuniverse.com"
                headers["Referer"] = "https://healthuniverse.com/"
                # Try common Health Universe header patterns
                hu_token = os.getenv("HU_API_KEY") or os.getenv("HEALTH_UNIVERSE_TOKEN")
                if hu_token and not self.token:
                    headers["Authorization"] = f"Bearer {hu_token}"
                elif hu_token:
                    headers["X-API-Key"] = hu_token
                    
            if self.debug_auth:
                logger.info("Session headers created:")
                safe_headers = {k: v if k != "Authorization" else f"{v[:20]}..." for k, v in headers.items()}
                logger.info(f"Headers: {safe_headers}")
                    
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
        # A2A compliant endpoint and payload mapping
        # Health Universe agents use JSON-RPC on root endpoint for message/send
        if method == "message/send":
            # Use JSON-RPC transport: root endpoint with JSON-RPC envelope
            endpoint = self.base_url
            payload = _jsonrpc_envelope(method, params)
        elif method == "tasks/get":
            endpoint = self.base_url  # JSON-RPC always uses root endpoint
            payload = _jsonrpc_envelope(method, params)
        else:
            # Fallback to root JSON-RPC for unmapped methods
            endpoint = self.base_url
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
                            # Enhanced error logging for troubleshooting
                            logger.error(f"❌ HTTP {response.status} error from {endpoint}")
                            logger.error(f"Request method: {response.request_info.method}")
                            logger.error(f"Request URL: {response.request_info.url}")
                            
                            # Safe header logging (mask sensitive data)
                            req_headers = dict(response.request_info.headers)
                            safe_req_headers = {}
                            for k, v in req_headers.items():
                                if k.lower() in ['authorization', 'x-api-key']:
                                    safe_req_headers[k] = f"{v[:10]}..." if len(v) > 10 else "***"
                                else:
                                    safe_req_headers[k] = v
                            logger.error(f"Request headers: {safe_req_headers}")
                            
                            logger.error(f"Response headers: {dict(response.headers)}")
                            logger.error(f"Response status: {response.status} {response.reason}")
                            logger.error(f"Response body: {response_text}")
                            
                            # Additional debugging for 403 errors
                            if response.status == 403:
                                logger.error("🚫 403 Forbidden Analysis:")
                                logger.error(f"   - Endpoint: {endpoint}")
                                logger.error(f"   - Has Auth Token: {'Yes' if self.token else 'No'}")
                                logger.error(f"   - Health Universe Domain: {'Yes' if 'healthuniverse.com' in endpoint else 'No'}")
                                logger.error(f"   - Payload Size: {len(json.dumps(payload)) if payload else 0} bytes")
                            
                            if attempt < retries - 1:
                                await asyncio.sleep(2 ** attempt + random.random())
                                continue
                            raise aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=response.status,
                                message=f"JSON-RPC request failed: {response_text}"
                            )
                        
                        # Parse response based on transport type
                        try:
                            data = json.loads(response_text)
                        except json.JSONDecodeError:
                            raise ValueError(f"Invalid JSON response: {response_text[:200]}")
                        
                        # All methods now use JSON-RPC transport for Health Universe
                        # JSON-RPC transport: check for JSON-RPC error and extract result
                        if "error" in data:
                            error = data["error"]
                            raise ValueError(f"JSON-RPC error {error.get('code')}: {error.get('message')}")
                        return data.get("result", data)
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < retries - 1:
                    logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
                    await asyncio.sleep(2 ** attempt + random.random())
                else:
                    raise
    
    async def _request_with_fallback(self, method: str, params: Dict[str, Any], 
                                   timeout_sec: Optional[float] = None) -> Any:
        """
        Make request with authentication fallback strategies for Health Universe.
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
            timeout_sec: Request timeout
            
        Returns:
            Response from the request
        """
        last_error = None
        
        # Strategy 1: Try with current token configuration
        try:
            return await self._request_jsonrpc(method, params, timeout_sec=timeout_sec)
        except aiohttp.ClientResponseError as e:
            if e.status != 403:
                raise  # Not an auth error, re-raise
            last_error = e
            logger.warning(f"Strategy 1 failed (current auth): {e}")
        
        # Strategy 2: Try without authentication (public endpoint)
        if "healthuniverse.com" in self.base_url:
            logger.info("Strategy 2: Trying without authentication...")
            original_token = self.token
            self.token = None
            # Force session recreation
            if self.session:
                await self.session.close()
                self.session = None
            
            try:
                result = await self._request_jsonrpc(method, params, timeout_sec=timeout_sec)
                logger.info("✅ Strategy 2 succeeded (no auth)")
                return result
            except aiohttp.ClientResponseError as e:
                logger.warning(f"Strategy 2 failed (no auth): {e}")
                last_error = e
            finally:
                self.token = original_token  # Restore original token
                # Force session recreation for next attempt
                if self.session:
                    await self.session.close()
                    self.session = None
        
        # Strategy 3: Try with different Health Universe token sources
        hu_tokens = [
            os.getenv("HU_API_KEY"),
            os.getenv("HEALTH_UNIVERSE_TOKEN"),  
            os.getenv("HU_ACCESS_TOKEN"),
            os.getenv("HEALTHUNIVERSE_API_KEY")
        ]
        
        for i, token in enumerate(hu_tokens):
            if not token or token == self.token:
                continue
                
            logger.info(f"Strategy {3+i}: Trying with alternative HU token...")
            original_token = self.token
            self.token = token
            # Force session recreation
            if self.session:
                await self.session.close()
                self.session = None
            
            try:
                result = await self._request_jsonrpc(method, params, timeout_sec=timeout_sec)
                logger.info(f"✅ Strategy {3+i} succeeded (alt token)")
                return result
            except aiohttp.ClientResponseError as e:
                logger.warning(f"Strategy {3+i} failed (alt token): {e}")
                last_error = e
            finally:
                self.token = original_token  # Restore original token
                # Force session recreation for next attempt
                if self.session:
                    await self.session.close()
                    self.session = None
        
        # All strategies failed, raise the last error
        raise last_error
    
    async def send_message(self, message: Union[Dict, Any], timeout_sec: Optional[float] = None) -> Any:
        """
        Send a properly formatted A2A message to the agent.
        
        Messages are for communication/requests to agents.
        For sending results/outputs, use send_artifact() instead.
        
        Args:
            message: A2A Message object or dict with proper structure:
                     - Must have 'role' field ('user', 'agent', 'system')
                     - Must have 'parts' array with valid Part objects
                     - Each part must have 'kind' discriminator ('text', 'data', 'file')
            timeout_sec: Request timeout in seconds
            
        Returns:
            Response from agent (structure preserved, not coerced to string)
            
        Raises:
            ValueError: If message is not properly formatted per A2A spec
            aiohttp.ClientError: On network errors
        """
        try:
            from a2a.utils.errors import InvalidParamsError
        except ImportError:
            # Fallback if A2A SDK structure is different
            InvalidParamsError = ValueError
        
        # Convert message to dict if it's an object
        if hasattr(message, 'model_dump'):
            message_dict = message.model_dump()
        elif hasattr(message, 'dict'):
            message_dict = message.dict()
        elif isinstance(message, dict):
            message_dict = message
        else:
            raise InvalidParamsError(
                f"Message must be a Message object or dict, got {type(message).__name__}"
            )
        
        # Validate required A2A message structure (no auto-fixing!)
        if not isinstance(message_dict.get('parts'), list):
            raise InvalidParamsError(
                "Message must have 'parts' array per A2A specification"
            )
        
        if not message_dict.get('role'):
            raise InvalidParamsError(
                "Message must have 'role' field (user/agent/system)"
            )
        
        # Validate each part has proper discriminator
        for i, part in enumerate(message_dict['parts']):
            if not isinstance(part, dict):
                raise InvalidParamsError(
                    f"Part {i} must be a dict with 'kind' discriminator"
                )
            
            kind = part.get('kind')
            if not kind:
                raise InvalidParamsError(
                    f"Part {i} missing required 'kind' discriminator"
                )
            
            if kind not in ['text', 'data', 'file']:
                raise InvalidParamsError(
                    f"Part {i} has invalid kind '{kind}'. Must be: text, data, or file"
                )
            
            # Validate part has required fields for its kind
            if kind == 'text' and 'text' not in part:
                raise InvalidParamsError(f"TextPart {i} missing 'text' field")
            elif kind == 'data' and 'data' not in part:
                raise InvalidParamsError(f"DataPart {i} missing 'data' field")
            elif kind == 'file' and 'file' not in part:
                raise InvalidParamsError(f"FilePart {i} missing 'file' field")
        
        # Add messageId if not present (this is metadata, OK to add)
        if 'messageId' not in message_dict:
            message_dict['messageId'] = str(uuid.uuid4())
        
        # Add kind field if missing (for message itself)
        if 'kind' not in message_dict:
            message_dict['kind'] = 'message'
        
        # Send via JSON-RPC
        params = {
            "message": message_dict,
            "metadata": {}
        }
        
        # Debug logging if enabled
        if os.getenv("DEBUG_A2A_MESSAGES", "false").lower() == "true":
            logger.info(f"A2A Client sending to {self.base_url}:")
            logger.info(f"Message: {json.dumps(message_dict, indent=2)}")
        
        # Use the request with fallback for auth strategies
        result = await self._request_with_fallback("message/send", params, timeout_sec=timeout_sec)
        
        # Return result as-is, preserving structure
        return result
    
    async def send_artifact(self, artifact: Union[Dict, Any], timeout_sec: Optional[float] = None) -> Any:
        """
        Send a properly formatted A2A artifact to the agent.
        
        Artifacts are for outputs/results generated by agents.
        For sending requests/communication, use send_message_v2() instead.
        
        Args:
            artifact: A2A Artifact object or dict with proper structure:
                      - Must have 'artifactId' field
                      - Must have 'parts' array with valid Part objects
                      - Each part must have 'kind' discriminator ('text', 'data', 'file')
                      - Optional: 'name', 'description', 'metadata'
            timeout_sec: Request timeout in seconds
            
        Returns:
            Response from agent (structure preserved)
            
        Raises:
            ValueError: If artifact is not properly formatted per A2A spec
            aiohttp.ClientError: On network errors
        """
        try:
            from a2a.utils.errors import InvalidParamsError
        except ImportError:
            InvalidParamsError = ValueError
        
        # Convert artifact to dict if it's an object
        if hasattr(artifact, 'model_dump'):
            artifact_dict = artifact.model_dump()
        elif hasattr(artifact, 'dict'):
            artifact_dict = artifact.dict()
        elif isinstance(artifact, dict):
            artifact_dict = artifact
        else:
            raise InvalidParamsError(
                f"Artifact must be an Artifact object or dict, got {type(artifact).__name__}"
            )
        
        # Validate required A2A artifact structure
        if not artifact_dict.get('artifactId'):
            raise InvalidParamsError(
                "Artifact must have 'artifactId' field per A2A specification"
            )
        
        if not isinstance(artifact_dict.get('parts'), list):
            raise InvalidParamsError(
                "Artifact must have 'parts' array per A2A specification"
            )
        
        # Validate each part has proper discriminator
        for i, part in enumerate(artifact_dict['parts']):
            if not isinstance(part, dict):
                raise InvalidParamsError(
                    f"Part {i} must be a dict with 'kind' discriminator"
                )
            
            kind = part.get('kind')
            if not kind:
                raise InvalidParamsError(
                    f"Part {i} missing required 'kind' discriminator"
                )
            
            if kind not in ['text', 'data', 'file']:
                raise InvalidParamsError(
                    f"Part {i} has invalid kind '{kind}'. Must be: text, data, or file"
                )
            
            # Validate part has required fields for its kind
            if kind == 'text' and 'text' not in part:
                raise InvalidParamsError(f"TextPart {i} missing 'text' field")
            elif kind == 'data' and 'data' not in part:
                raise InvalidParamsError(f"DataPart {i} missing 'data' field")
            elif kind == 'file' and 'file' not in part:
                raise InvalidParamsError(f"FilePart {i} missing 'file' field")
        
        # Send via JSON-RPC (artifacts may use a different method in the future)
        # For now, we send as a special message type
        params = {
            "artifact": artifact_dict,
            "metadata": {}
        }
        
        # Debug logging if enabled
        if os.getenv("DEBUG_A2A_MESSAGES", "false").lower() == "true":
            logger.info(f"A2A Client sending artifact to {self.base_url}:")
            logger.info(f"Artifact: {json.dumps(artifact_dict, indent=2)}")
        
        # Use the request with fallback for auth strategies
        # Note: This may need to be updated when A2A defines artifact-specific endpoints
        result = await self._request_with_fallback("artifact/send", params, timeout_sec=timeout_sec)
        
        # Return result as-is, preserving structure
        return result

    async def send_message_streaming(self, message: Dict[str, Any], 
                                    callback=None) -> Dict[str, Any]:
        """
        Send message using message/stream method (A2A section 7.2).
        
        Args:
            message: A2A Message object
            callback: Optional async function called for each TaskStatusUpdateEvent
            
        Returns:
            Final Task object when complete
        """
        from .sse_client import SSEClient
        
        # Check if agent supports streaming first
        if not await self.supports_streaming():
            # Fall back to regular send if agent doesn't support streaming
            logger.info("Agent does not support streaming, falling back to message/send")
            return await self.send_message(message, timeout_sec=30)
        
        # Prepare JSON-RPC payload for streaming
        payload = {
            "jsonrpc": "2.0",
            "method": "message/stream",
            "params": {"message": message},
            "id": next(_jsonrpc_id_counter)
        }
        
        final_task = None
        
        async with self._get_session() as session:
            # Send streaming request
            async with session.post(self.base_url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise aiohttp.ClientError(f"Stream request failed ({response.status}): {error_text}")
                
                # Check for SSE content type
                content_type = response.headers.get('Content-Type', '')
                if 'text/event-stream' not in content_type:
                    # Not streaming, return regular response
                    logger.info("Response is not SSE stream, parsing as regular JSON-RPC")
                    data = await response.json()
                    if 'error' in data:
                        raise ValueError(f"JSON-RPC error: {data['error']}")
                    return data.get('result')
                
                # Parse SSE stream
                sse = SSEClient()
                async for event in sse.parse_stream(response):
                    if 'result' in event:
                        result = event['result']
                        
                        # Handle different result types
                        if isinstance(result, dict):
                            kind = result.get('kind')
                            
                            if kind == 'status-update':
                                # TaskStatusUpdateEvent
                                if callback:
                                    await callback(result)
                            
                            elif kind == 'task':
                                # Task object - could be final or intermediate
                                final_task = result
                                
                            elif kind == 'artifact-update':
                                # TaskArtifactUpdateEvent
                                if callback:
                                    await callback(result)
                            
                            else:
                                # Unknown result type, store as final
                                final_task = result
                    
                    elif 'error' in event:
                        raise ValueError(f"Stream error: {event['error']}")
        
        return final_task

    async def supports_streaming(self, agent_url: str = None) -> bool:
        """Check if agent supports streaming via AgentCard."""
        url = agent_url or self.base_url
        card_url = f"{url}/.well-known/agent-card.json"
        
        async with self._get_session() as session:
            try:
                async with session.get(card_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        card = await response.json()
                        capabilities = card.get('capabilities', {})
                        return capabilities.get('streaming', False)
            except Exception as e:
                logger.debug(f"Could not fetch agent card: {e}")
        
        return False

    async def test_agent_accessibility(self) -> Dict[str, Any]:
        """
        Test various endpoints of a Health Universe agent for accessibility.
        Useful for debugging 403 Forbidden issues.
        
        Returns:
            Dict with test results for different endpoints
        """
        results = {
            "base_url": self.base_url,
            "has_token": bool(self.token),
            "endpoints": {}
        }
        
        test_endpoints = [
            ("health", "/health"),
            ("agent_card", "/.well-known/agent-card.json"),
            ("message_send", "/v1/message:send"),
            ("root", "/")
        ]
        
        async with self._get_session() as session:
            for name, path in test_endpoints:
                endpoint = f"{self.base_url}{path}"
                try:
                    # Use GET for non-message endpoints
                    if name in ["health", "agent_card"]:
                        async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            results["endpoints"][name] = {
                                "status": response.status,
                                "accessible": response.status < 400,
                                "headers": dict(response.headers),
                                "body_size": len(await response.text())
                            }
                    else:
                        # Use HEAD for message endpoints to avoid sending actual data
                        async with session.head(endpoint, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            results["endpoints"][name] = {
                                "status": response.status,
                                "accessible": response.status != 403,  # 405 Method Not Allowed is OK
                                "headers": dict(response.headers),
                                "method": "HEAD"
                            }
                except Exception as e:
                    results["endpoints"][name] = {
                        "error": str(e),
                        "accessible": False
                    }
        
        return results


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
