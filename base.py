"""
Full-featured A2A-compliant base class for agents.
Minimal implementation following A2A protocol specification v0.3.0.
The A2A framework handles LLM integration, tools, streaming, and task management.
"""

import os
import json
import logging
import time
from typing import Optional, List, Dict, Any, Union
from abc import ABC, abstractmethod
from collections import defaultdict

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCard,
    AgentProvider,
    AgentCapabilities,
    AgentSkill,
    TextPart,
    Part,
    TaskState,
    DataPart,
    Task,
    TaskStatus,
    Message
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError, InvalidParamsError
from utils.logging import get_logger
from utils.message_utils import create_message_parts, create_agent_message, extract_content_from_parts

logger = logging.getLogger(__name__)

# Rate limiting for legacy warnings
_legacy_warnings = defaultdict(lambda: {"count": 0, "last_warn": 0})
_MAX_LEGACY_WARNINGS = 10  # Max warnings per type
_LEGACY_WARN_INTERVAL = 60  # Seconds between warnings


class A2AAgent(AgentExecutor, ABC):
    """
    A2A-compliant base class for all agents.
    
    This minimal implementation follows the A2A specification v0.3.0:
    - Agents declare capabilities (name, description, tools)
    - The A2A framework handles execution, LLM integration, and task management
    - We only extract messages, process them, and return responses
    
    Subclasses must implement:
    - get_agent_name()
    - get_agent_description()
    - process_message()
    
    Optional implementations:
    - get_tools() - for tool-based agents
    - get_system_instruction() - for custom LLM instructions
    - get_agent_skills() - for detailed capability declaration
    """
    
    def __init__(self):
        """Initialize the agent with logging and optional startup checks."""
        self.logger = get_logger(self.__class__.__name__)
        self._current_task_id = None
        
        # Run startup checks if not disabled
        if os.getenv("A2A_SKIP_STARTUP", "").lower() not in ("true", "1"):
            from utils.startup import run_startup_checks
            run_startup_checks(self)
    
    def create_agent_card(self) -> AgentCard:
        """
        Create the AgentCard for agent discovery.
        Fully compliant with A2A specification v0.3.0.
        
        Returns:
            AgentCard with agent metadata and capabilities
        """
        # Get base URL from HU_APP_URL environment variable (HealthUniverse standard)
        # This should be the root URL - clients will append /a2a/v1/... themselves
        base_url = os.getenv("HU_APP_URL", os.getenv("A2A_BASE_URL", "http://localhost:8000"))
        
        return AgentCard(
            # Required fields per spec
            protocolVersion="0.3.0",
            name=self.get_agent_name(),
            description=self.get_agent_description(),
            version=self.get_agent_version(),
            url=base_url,
            
            # Transport configuration - JSON-RPC is currently implemented
            preferredTransport="JSONRPC",
            additionalInterfaces=[
                {
                    "url": base_url,
                    "transport": "JSONRPC"
                }
            ],
            
            # Provider information
            provider=AgentProvider(
                organization="A2A Template",
                url="https://github.com/jmjlacosta/a2a-template"
            ),
            
            # Capabilities
            capabilities=AgentCapabilities(
                streaming=self.supports_streaming(),
                push_notifications=self.supports_push_notifications()
            ),
            
            # Skills (optional but recommended)
            skills=self.get_agent_skills(),
            
            # Security (optional, add as needed)
            securitySchemes={},  # e.g., {"oauth": {"type":"openIdConnect", "openIdConnectUrl":"..."}}
            security=[],  # e.g., [{"oauth": ["openid", "profile", "email"]}]
            
            # Input/output modes
            defaultInputModes=["text/plain", "application/json"],
            defaultOutputModes=["text/plain", "application/json"]
        )
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Execute agent logic - A2A compliant minimal implementation.
        
        The A2A framework handles:
        - Task management
        - LLM integration
        - Tool orchestration
        - Streaming and artifacts
        
        We only extract the message, process it, and return the response.
        
        Args:
            context: Request context with message and metadata
            event_queue: Queue for sending events/responses
        """
        task = None
        try:
            # Extract message from A2A protocol format
            message = self._extract_message(context)
            
            if not message:
                raise InvalidParamsError("No message provided in request")
            
            # Get or create task for proper lifecycle management
            task = context.current_task
            if not task:
                task = new_task(context.message or new_agent_text_message("Processing..."))
                await event_queue.enqueue_event(task)
            
            self._current_task_id = task.id
            
            # Create TaskUpdater for status updates (spec-compliant)
            # Use contextId (camelCase) per spec
            context_id = getattr(task, "contextId", None) or getattr(task, "context_id", None) or task.id
            updater = TaskUpdater(event_queue, task.id, context_id)
            
            # Signal task is being worked on (spec state: "working")
            await updater.update_status(
                TaskState.working,
                new_agent_text_message("Processing your request...")
            )
            
            # Log if debug mode is enabled
            if os.getenv("SHOW_AGENT_CALLS", "false").lower() == "true":
                self.logger.info(f"📨 {self.get_agent_name()}: Processing message ({len(message)} chars)")
            
            # Process message through agent's business logic
            # This is where agents implement their specific functionality
            response = await self.process_message(message)
            
            # Create artifact for the agent's output (not a message!)
            # Per A2A spec: Artifacts are outputs/results, Messages are communication
            if isinstance(response, (dict, list)):
                # Structured data uses DataPart
                parts = [DataPart(kind="data", data=response)]
            else:
                # String responses use TextPart
                parts = [TextPart(kind="text", text=str(response))]
            
            # Add artifact to the task
            # Artifacts represent the tangible outputs generated by the agent
            await updater.add_artifact(
                parts=parts,
                artifact_id=f"result-{task.id}",
                name=f"{self.get_agent_name()} Result",
                metadata={
                    "agent": self.get_agent_name(),
                    "timestamp": time.time()
                }
            )
            
            # Mark task as completed (without a message, artifacts are the output)
            await updater.update_status(
                TaskState.completed,
                new_agent_text_message(f"Task completed. Generated 1 artifact.")
            )
            
        except ServerError as e:
            # A2A SDK errors are already properly formatted
            if task:
                context_id = getattr(task, "contextId", None) or getattr(task, "context_id", None) or task.id
                updater = TaskUpdater(event_queue, task.id, context_id)
                await updater.update_status(
                    TaskState.failed,
                    new_agent_text_message(f"Task failed: {str(e)}")
                )
            raise
        except Exception as e:
            # Let A2A handle error formatting
            self.logger.error(f"Error processing message: {str(e)}")
            if task:
                context_id = getattr(task, "contextId", None) or getattr(task, "context_id", None) or task.id
                updater = TaskUpdater(event_queue, task.id, context_id)
                await updater.update_status(
                    TaskState.failed,
                    new_agent_text_message(f"Task failed: {str(e)}")
                )
            raise ServerError(error=e)
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Handle cancellation requests per A2A specification.
        Attempts cooperative cancellation and returns Task with canceled state.
        
        The spec defines tasks/cancel - we should attempt cancellation
        and return a Task with the new state rather than always erroring.
        """
        # Extract task ID from context (check multiple sources)
        task_id = None
        
        # First check current_task if present
        if hasattr(context, 'current_task') and context.current_task:
            task_id = context.current_task.id
        # Then check task_id attribute
        elif hasattr(context, 'task_id'):
            task_id = context.task_id
        # Check metadata
        elif context.metadata and 'task_id' in context.metadata:
            task_id = context.metadata['task_id']
        # Fall back to stored task ID
        elif self._current_task_id:
            task_id = self._current_task_id
        
        if not task_id:
            # If we can't identify the task, we can't cancel it
            from a2a.utils.errors import InvalidParamsError
            raise ServerError(error=InvalidParamsError("No task ID provided for cancellation"))
        
        try:
            # Attempt cooperative cancellation in the runtime
            # Subclasses can override this to implement actual cancellation logic
            self.logger.info(f"Attempting to cancel task {task_id}")
            
            # Get consistent context ID for all operations
            ctx_id = getattr(context, 'contextId', getattr(context, 'context_id', task_id))
            
            # Create updater for the task with consistent context ID
            updater = TaskUpdater(event_queue, task_id, ctx_id)
            
            # Signal task is being canceled (spec state: "canceled")
            await updater.update_status(
                TaskState.canceled,
                new_agent_text_message(f"Task {task_id} has been canceled")
            )
            
            # Emit a Task event with canceled state (spec-compliant structure)
            canceled_task = Task(
                id=task_id,
                contextId=ctx_id,
                status=TaskStatus(
                    state=TaskState.canceled,
                    message=Message(
                        role="agent",
                        parts=[TextPart(kind="text", text="Task canceled by user request")],
                        messageId=f"cancel-{task_id}",
                        taskId=task_id,
                        contextId=ctx_id,
                        kind="message"
                    )
                ),
                kind="task"
            )
            await event_queue.enqueue_event(canceled_task)
            
            self.logger.info(f"Task {task_id} canceled successfully")
            
        except Exception as e:
            self.logger.error(f"Error canceling task {task_id}: {str(e)}")
            # Even if cancellation fails, we should return a task with appropriate state
            ctx_id = getattr(context, 'contextId', getattr(context, 'context_id', task_id))
            failed_task = Task(
                id=task_id,
                contextId=ctx_id,
                status=TaskStatus(
                    state=TaskState.failed,
                    message=Message(
                        role="agent",
                        parts=[TextPart(kind="text", text=f"Cancellation failed: {str(e)}")],
                        messageId=f"cancel-failed-{task_id}",
                        taskId=task_id,
                        contextId=ctx_id,
                        kind="message"
                    )
                ),
                kind="task"
            )
            await event_queue.enqueue_event(failed_task)
            raise ServerError(error=e)
    
    def _log_legacy_warning(self, legacy_type: str) -> None:
        """
        Log rate-limited warnings for legacy Part formats.
        
        Args:
            legacy_type: Type of legacy format encountered
        """
        global _legacy_warnings
        
        warning_info = _legacy_warnings[legacy_type]
        current_time = time.time()
        
        # Check if we should log this warning
        should_warn = (
            warning_info["count"] < _MAX_LEGACY_WARNINGS and
            current_time - warning_info["last_warn"] > _LEGACY_WARN_INTERVAL
        )
        
        if should_warn:
            warning_info["count"] += 1
            warning_info["last_warn"] = current_time
            
            structured_hint = {
                "action": "migrate_to_kind_union",
                "saw": legacy_type,
                "count": warning_info["count"],
                "max_warnings": _MAX_LEGACY_WARNINGS
            }
            
            self.logger.warning(
                f"Legacy Part format detected: {legacy_type} "
                f"({warning_info['count']}/{_MAX_LEGACY_WARNINGS} warnings). "
                f"Hint: {json.dumps(structured_hint)}"
            )
    
    def _extract_message(self, context: RequestContext) -> Optional[str]:
        """
        Extract message from A2A protocol format.
        Spec-compliant parsing that handles Part as discriminated union by 'kind'.
        
        Per A2A spec, Part is a union with kind: "text" | "file" | "data"
        We must branch on part["kind"] and handle TextPart, DataPart, and FilePart.
        
        Args:
            context: Request context containing message
            
        Returns:
            Extracted message as string or None
        """
        if not context.message or not context.message.parts:
            return None
        
        extracted = []
        
        for part in context.message.parts:
            # Handle both dict-like and object-like parts defensively
            # The spec defines Part as discriminated union by 'kind'
            
            # Try to get kind from part (handles both dict and object)
            kind = None
            if isinstance(part, dict):
                kind = part.get("kind")
            elif hasattr(part, "kind"):
                kind = part.kind
            
            if kind == "text":
                # TextPart: extract text field
                text = None
                if isinstance(part, dict):
                    text = part.get("text")
                elif hasattr(part, "text"):
                    text = part.text
                if text is not None:
                    extracted.append(str(text))
                    
            elif kind == "data":
                # DataPart: serialize data as JSON
                data = None
                if isinstance(part, dict):
                    data = part.get("data")
                elif hasattr(part, "data"):
                    data = part.data
                if data is not None:
                    if isinstance(data, (dict, list)):
                        extracted.append(json.dumps(data))
                    else:
                        extracted.append(str(data))
                        
            elif kind == "file":
                # FilePart: handle file with uri or bytes
                file_obj = None
                if isinstance(part, dict):
                    file_obj = part.get("file")
                elif hasattr(part, "file"):
                    file_obj = part.file
                    
                if file_obj:
                    # Prefer URI if present
                    if isinstance(file_obj, dict):
                        name = file_obj.get("name", "unnamed")
                        if "uri" in file_obj:
                            extracted.append(f"[file:{name}] {file_obj['uri']}")
                        elif "bytes" in file_obj:
                            # Note: In production, you might want to decode/process bytes
                            extracted.append(f"[file-bytes:{name}] (binary data)")
                    elif hasattr(file_obj, "uri"):
                        name = getattr(file_obj, "name", "unnamed")
                        extracted.append(f"[file:{name}] {file_obj.uri}")
                    elif hasattr(file_obj, "bytes"):
                        name = getattr(file_obj, "name", "unnamed")
                        extracted.append(f"[file-bytes:{name}] (binary data)")
                        
            else:
                # Fallback for legacy/malformed parts
                # Try common patterns but log a rate-limited warning
                handled = False
                legacy_type = None
                
                # Check for root.text pattern (legacy)
                if hasattr(part, 'root'):
                    if isinstance(part.root, TextPart):
                        extracted.append(part.root.text)
                        handled = True
                        legacy_type = "root.text"
                    elif isinstance(part.root, DataPart):
                        data = part.root.data
                        if isinstance(data, (dict, list)):
                            extracted.append(json.dumps(data))
                        else:
                            extracted.append(str(data))
                        handled = True
                        legacy_type = "root.data"
                
                # Direct text attribute (legacy)
                elif hasattr(part, "text"):
                    extracted.append(str(part.text))
                    handled = True
                    legacy_type = "direct.text"
                    
                # Direct data attribute (legacy)
                elif hasattr(part, "data"):
                    data = part.data
                    if isinstance(data, (dict, list)):
                        extracted.append(json.dumps(data))
                    else:
                        extracted.append(str(data))
                    handled = True
                    legacy_type = "direct.data"
                
                if handled and legacy_type:
                    # Rate-limited warning only if enabled
                    if os.getenv("A2A_WARN_LEGACY_PARTS", "true").lower() == "true":
                        self._log_legacy_warning(legacy_type)
        
        if not extracted:
            return None
        
        # Join all parts with newline
        return "\n".join(extracted)
    
    # Abstract methods that subclasses must implement
    
    @abstractmethod
    def get_agent_name(self) -> str:
        """Return the agent's name for the AgentCard."""
        pass
    
    @abstractmethod
    def get_agent_description(self) -> str:
        """Return the agent's description for the AgentCard."""
        pass
    
    @abstractmethod
    async def process_message(self, message: str) -> Union[str, Dict[str, Any], List[Any]]:
        """
        Process an incoming message and return a response.
        
        Args:
            message: The extracted text message to process
            
        Returns:
            Response as string (TextPart), dict/list (DataPart), or other structured data
        """
        pass
    
    # Optional methods that subclasses can override
    
    def get_agent_version(self) -> str:
        """Return agent version. Override for custom versioning."""
        return "1.0.0"
    
    def get_system_instruction(self) -> str:
        """
        Return system instruction for LLM.
        Override to provide custom instructions.
        """
        return "You are a helpful AI assistant."
    
    def get_tools(self) -> List:
        """
        Return list of tools for the agent.
        Override to provide tool-based functionality.
        
        Tools should be langchain_core.tools.Tool instances or compatible.
        The A2A framework will handle tool execution.
        
        Returns:
            List of tools or empty list for no tools
        """
        return []
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """
        Return list of skills for the AgentCard.
        Override to declare specific capabilities.
        
        Each skill should define its own inputModes/outputModes if they
        differ from the agent's defaults.
        
        Returns:
            List of AgentSkill objects or empty list
        """
        return []
    
    def supports_streaming(self) -> bool:
        """
        Whether this agent supports streaming responses.
        Override to enable streaming support.
        
        If you return True here, you MUST implement message/stream SSE
        and send TaskStatusUpdateEvent/TaskArtifactUpdateEvent payloads.
        """
        return False
    
    def supports_push_notifications(self) -> bool:
        """
        Whether this agent supports push notifications.
        Override to enable push notification support.
        """
        return False
    
    # Utility methods for inter-agent communication
    
    async def call_agent(
        self,
        agent_name_or_url: str,
        message: Union[str, Dict, List, Any],
        timeout: float = 30.0
    ) -> Any:
        """
        Call another A2A-compliant agent with any type of message.
        
        This is the consolidated method that replaces call_other_agent() and
        call_other_agent_with_data(). It properly handles text, structured data,
        and pre-formatted A2A messages.
        
        Args:
            agent_name_or_url: Agent name (from registry) or direct URL
            message: Either:
                     - A properly formatted Message object/dict with 'parts' array
                     - A string (will be wrapped in TextPart for convenience)
                     - Structured data dict/list (will be wrapped in DataPart)
            timeout: Request timeout in seconds
            
        Returns:
            Response from the agent (structure preserved, not coerced)
            
        Raises:
            InvalidParamsError: If message cannot be formatted per A2A spec
            Exception: If agent communication fails
        """
        from utils.a2a_client import A2AClient
        from a2a.types import Message
        try:
            from a2a.utils.errors import InvalidParamsError
        except ImportError:
            # Fallback if A2A SDK structure is different
            InvalidParamsError = ValueError
        
        # Create client based on input type
        if agent_name_or_url.startswith(('http://', 'https://')):
            client = A2AClient(agent_name_or_url)
            self.logger.info(f"Calling agent at URL: {agent_name_or_url}")
        else:
            try:
                client = A2AClient.from_registry(agent_name_or_url)
                self.logger.info(f"Calling agent '{agent_name_or_url}' from registry")
            except ValueError as e:
                raise ValueError(f"Failed to resolve agent '{agent_name_or_url}': {e}")
        
        try:
            # Format message based on type
            if isinstance(message, Message):
                # Already a Message object
                formatted_message = message
            elif isinstance(message, dict) and 'parts' in message:
                # Already formatted as dict with parts
                formatted_message = message
            elif isinstance(message, str):
                # Convenience: wrap string in TextPart
                formatted_message = {
                    "role": "user",
                    "parts": [{"kind": "text", "text": message}],
                    "kind": "message"
                }
            elif isinstance(message, (dict, list)):
                # Convenience: wrap structured data in DataPart
                formatted_message = {
                    "role": "user",
                    "parts": [{"kind": "data", "data": message}],
                    "kind": "message"
                }
            else:
                raise InvalidParamsError(
                    f"Cannot format {type(message).__name__} as A2A message. "
                    "Provide Message object, dict with 'parts', string, or JSON-serializable data."
                )
            
            # Send message using the proper method
            result = await client.send_message(formatted_message, timeout_sec=timeout)
            
            # Extract artifacts from response if present
            # Agents should return artifacts (outputs) not messages
            if isinstance(result, dict):
                # Check if response is a Task with artifacts
                if "artifacts" in result and isinstance(result["artifacts"], list):
                    # Return the first artifact (or all if multiple)
                    artifacts = result["artifacts"]
                    return artifacts[0] if len(artifacts) == 1 else artifacts
                
                # Check if response is directly an artifact
                if "artifactId" in result and "parts" in result:
                    return result
                
                # Check if response has a task with artifacts
                if "task" in result and isinstance(result["task"], dict):
                    task = result["task"]
                    if "artifacts" in task and task["artifacts"]:
                        artifacts = task["artifacts"]
                        return artifacts[0] if len(artifacts) == 1 else artifacts
            
            # Fallback: return raw result if no artifacts found
            return result
            
        finally:
            await client.close()
