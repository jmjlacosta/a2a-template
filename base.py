"""
Full-featured A2A-compliant base class for agents.
Minimal implementation following A2A protocol specification v0.3.0.
The A2A framework handles LLM integration, tools, streaming, and task management.
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

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

logger = logging.getLogger(__name__)


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
        """Initialize the agent with logging."""
        self._setup_logging()
        self._current_task_id = None
    
    def _setup_logging(self):
        """Set up logging configuration."""
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def create_agent_card(self) -> AgentCard:
        """
        Create the AgentCard for agent discovery.
        Fully compliant with A2A specification v0.3.0.
        
        Returns:
            AgentCard with agent metadata and capabilities
        """
        # Get base URL from environment or use default
        base_url = os.getenv("A2A_BASE_URL", "https://your-agent.example.com/a2a/v1")
        
        return AgentCard(
            # Required fields per spec
            protocolVersion="0.3.0",
            name=self.get_agent_name(),
            description=self.get_agent_description(),
            version=self.get_agent_version(),
            url=base_url,
            
            # Transport configuration
            preferredTransport="JSONRPC",
            additionalInterfaces=[
                {
                    "url": base_url,
                    "transport": "JSONRPC"
                }
                # Add more transports as supported (e.g., GRPC, HTTP+JSON)
            ],
            
            # Provider information
            provider=AgentProvider(
                organization="A2A Template",
                url="https://github.com/jmjlacosta/a2a-template"
            ),
            
            # Capabilities
            capabilities=AgentCapabilities(
                streaming=self.supports_streaming(),
                pushNotifications=self.supports_push_notifications()
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
            updater = TaskUpdater(event_queue, task.id, task.context_id or task.id)
            
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
            
            # Send response back via event queue
            # The A2A framework handles the rest (formatting, delivery, etc.)
            await event_queue.enqueue_event(
                new_agent_text_message(response)
            )
            
            # Mark task as completed (spec state: "completed")
            await updater.update_status(
                TaskState.completed,
                new_agent_text_message("Task completed successfully")
            )
            
        except ServerError as e:
            # A2A SDK errors are already properly formatted
            if task:
                updater = TaskUpdater(event_queue, task.id, task.context_id or task.id)
                await updater.update_status(
                    TaskState.failed,
                    new_agent_text_message(f"Task failed: {str(e)}")
                )
            raise
        except Exception as e:
            # Let A2A handle error formatting
            self.logger.error(f"Error processing message: {str(e)}")
            if task:
                updater = TaskUpdater(event_queue, task.id, task.context_id or task.id)
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
        # Extract task ID from context
        task_id = None
        if hasattr(context, 'task_id'):
            task_id = context.task_id
        elif context.metadata and 'task_id' in context.metadata:
            task_id = context.metadata['task_id']
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
            
            # Create updater for the task
            updater = TaskUpdater(event_queue, task_id, task_id)
            
            # Signal task is being canceled (spec state: "canceled")
            await updater.update_status(
                TaskState.canceled,
                new_agent_text_message(f"Task {task_id} has been canceled")
            )
            
            # Emit a Task event with canceled state (spec-compliant structure)
            canceled_task = Task(
                id=task_id,
                contextId=context.context_id if hasattr(context, 'context_id') else task_id,
                status=TaskStatus(
                    state=TaskState.canceled,
                    message=Message(
                        role="agent",
                        parts=[TextPart(kind="text", text="Task canceled by user request")],
                        messageId=f"cancel-{task_id}",
                        taskId=task_id,
                        contextId=context.context_id if hasattr(context, 'context_id') else task_id,
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
            failed_task = Task(
                id=task_id,
                contextId=context.context_id if hasattr(context, 'context_id') else task_id,
                status=TaskStatus(
                    state=TaskState.failed,
                    message=Message(
                        role="agent",
                        parts=[TextPart(kind="text", text=f"Cancellation failed: {str(e)}")],
                        messageId=f"cancel-failed-{task_id}",
                        taskId=task_id,
                        contextId=context.context_id if hasattr(context, 'context_id') else task_id,
                        kind="message"
                    )
                ),
                kind="task"
            )
            await event_queue.enqueue_event(failed_task)
            raise ServerError(error=e)
    
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
                # Try common patterns but log a warning
                handled = False
                
                # Check for root.text pattern (legacy)
                if hasattr(part, 'root'):
                    if isinstance(part.root, TextPart):
                        extracted.append(part.root.text)
                        handled = True
                    elif isinstance(part.root, DataPart):
                        data = part.root.data
                        if isinstance(data, (dict, list)):
                            extracted.append(json.dumps(data))
                        else:
                            extracted.append(str(data))
                        handled = True
                
                # Direct text attribute (legacy)
                elif hasattr(part, "text"):
                    extracted.append(str(part.text))
                    handled = True
                    
                # Direct data attribute (legacy)
                elif hasattr(part, "data"):
                    data = part.data
                    if isinstance(data, (dict, list)):
                        extracted.append(json.dumps(data))
                    else:
                        extracted.append(str(data))
                    handled = True
                
                if handled:
                    self.logger.warning(f"Handled legacy part format without 'kind' field")
        
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
    async def process_message(self, message: str) -> str:
        """
        Process an incoming message and return a response.
        
        Args:
            message: The extracted text message to process
            
        Returns:
            Response message as string
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
    
    async def call_other_agent(self, agent_name_or_url: str, message: str, timeout: float = 30.0) -> str:
        """
        Call another A2A-compliant agent.
        
        This utility method helps agents communicate with each other
        following the A2A protocol.
        
        Args:
            agent_name_or_url: Agent name (from config) or direct URL
            message: Message to send to the other agent
            timeout: Request timeout in seconds
            
        Returns:
            Response from the other agent as string
            
        Raises:
            Exception: If agent communication fails
        """
        from utils.a2a_client import A2AAgentClient
        
        # Resolve agent URL from config if name provided
        agent_url = agent_name_or_url
        if not agent_name_or_url.startswith(('http://', 'https://')):
            # Try to load from config
            try:
                with open('config/agents.json', 'r') as f:
                    config = json.load(f)
                    agents = config.get('agents', {})
                    if agent_name_or_url in agents:
                        agent_url = agents[agent_name_or_url]['url']
                    else:
                        raise ValueError(f"Agent '{agent_name_or_url}' not found in config")
            except FileNotFoundError:
                raise ValueError(f"Config file not found and '{agent_name_or_url}' is not a URL")
        
        # Call the agent using A2A protocol
        self.logger.info(f"Calling agent at {agent_url}")
        
        async with A2AAgentClient() as client:
            response = await client.call_agent(agent_url, message, timeout=timeout)
            return response