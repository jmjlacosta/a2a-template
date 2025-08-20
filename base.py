"""
Full-featured A2A-compliant base class for agents.
Minimal implementation following A2A protocol specification.
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
    DataPart
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError, InvalidParamsError

logger = logging.getLogger(__name__)


class A2AAgent(AgentExecutor, ABC):
    """
    A2A-compliant base class for all agents.
    
    This minimal implementation follows the A2A specification:
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
        
        Returns:
            AgentCard with agent metadata and capabilities
        """
        return AgentCard(
            name=self.get_agent_name(),
            description=self.get_agent_description(),
            version=self.get_agent_version(),
            # URL will be set by the server based on deployment
            url="",
            provider=AgentProvider(
                name="A2AAgent",
                version="1.0.0",
                organization="A2A Template",
                url="https://github.com/jmjlacosta/a2a-template"
            ),
            skills=self.get_agent_skills(),
            capabilities=AgentCapabilities(
                streaming=self.supports_streaming(),
                push_notifications=self.supports_push_notifications()
            ),
            defaultInputModes=["text/plain"],
            defaultOutputModes=["text/plain"]
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
        try:
            # Extract message from A2A protocol format
            message = self._extract_message(context)
            
            if not message:
                raise InvalidParamsError("No message provided in request")
            
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
            
        except ServerError:
            # A2A SDK errors are already properly formatted
            raise
        except Exception as e:
            # Let A2A handle error formatting
            self.logger.error(f"Error processing message: {str(e)}")
            raise ServerError(error=e)
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Handle cancellation requests.
        Default implementation raises error - override if cancellation is supported.
        """
        from a2a.utils.errors import UnsupportedOperationError
        raise ServerError(error=UnsupportedOperationError("Cancellation not supported"))
    
    def _extract_message(self, context: RequestContext) -> Optional[str]:
        """
        Extract message from A2A protocol format.
        
        Handles multiple part formats:
        - TextPart: part.root.text (standard text format)
        - DataPart: part.root.data (JSON/structured data format)
        - Alternative: part.text (backwards compatibility)
        
        For DataPart (JSON), converts to string representation.
        
        Args:
            context: Request context containing message
            
        Returns:
            Extracted message as string (JSON string for DataPart) or None
        """
        if not context.message or not context.message.parts:
            return None
        
        extracted_parts = []
        
        for part in context.message.parts:
            # Check for standard TextPart format (part.root.text)
            if hasattr(part, 'root'):
                if isinstance(part.root, TextPart):
                    extracted_parts.append(part.root.text)
                elif isinstance(part.root, DataPart):
                    # Handle DataPart with JSON data (A2A spec 6.5.3)
                    # Convert to JSON string for processing
                    data = part.root.data
                    if isinstance(data, dict) or isinstance(data, list):
                        extracted_parts.append(json.dumps(data))
                    else:
                        extracted_parts.append(str(data))
            # Check for alternative format (part.text)
            elif hasattr(part, 'text'):
                extracted_parts.append(part.text)
            # Check for direct DataPart
            elif hasattr(part, 'data'):
                data = part.data
                if isinstance(data, dict) or isinstance(data, list):
                    extracted_parts.append(json.dumps(data))
                else:
                    extracted_parts.append(str(data))
        
        # Combine all extracted parts
        if not extracted_parts:
            return None
        elif len(extracted_parts) == 1:
            return extracted_parts[0]
        else:
            # Multiple parts - join with newline
            return "\n".join(extracted_parts)
    
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
        
        Returns:
            List of AgentSkill objects or empty list
        """
        return []
    
    def supports_streaming(self) -> bool:
        """
        Whether this agent supports streaming responses.
        Override to enable streaming support.
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