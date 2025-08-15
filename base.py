"""
Simplified A2A-compliant base class for agents.
Leverages the A2A SDK instead of reimplementing functionality.
Full A2A v0.3.0 compliance in ~200 lines.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    AgentCard,
    AgentProvider,
    AgentCapabilities,
    AgentSkill,
    TextPart,
    Part
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError, InvalidParamsError

logger = logging.getLogger(__name__)


class A2AAgent(AgentExecutor, ABC):
    """
    Base class for A2A-compliant agents.
    
    Provides:
    - Automatic AgentCard creation with required fields
    - Proper error handling using SDK error classes
    - Message extraction from A2A protocol format
    - Compliance with A2A v0.3.0 specification
    
    Subclasses must implement:
    - get_agent_name(): Return agent name
    - get_agent_description(): Return agent description
    - process_message(): Process incoming messages
    """
    
    def __init__(self):
        """Initialize the A2A-compliant agent."""
        super().__init__()
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for the agent."""
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
        Create A2A-compliant agent card with all required fields.
        
        Returns:
            AgentCard with all required fields for A2A v0.3.0 compliance
        """
        return AgentCard(
            # Required fields from subclass
            name=self.get_agent_name(),
            description=self.get_agent_description(),
            
            # A2A specification required fields
            version=os.getenv("AGENT_VERSION", "1.0.0"),
            protocolVersion="0.3.0",  # A2A protocol version
            url=os.getenv("HU_APP_URL", f"http://localhost:{os.getenv('PORT', '8000')}"),
            preferredTransport="JSONRPC",
            
            # Required input/output modes
            defaultInputModes=self.get_input_modes(),
            defaultOutputModes=self.get_output_modes(),
            
            # Skills (can be empty list but must exist)
            skills=self.get_agent_skills(),
            
            # Required provider information
            provider=AgentProvider(
                organization=os.getenv("AGENT_ORG", "Agent Organization"),
                url=os.getenv("AGENT_ORG_URL", "https://example.com")
            ),
            
            # Capabilities
            capabilities=AgentCapabilities(
                streaming=self.supports_streaming(),
                push_notifications=self.supports_push_notifications()
            )
        )
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Execute agent logic with proper A2A protocol handling.
        
        This method:
        1. Extracts the message from A2A protocol format
        2. Processes the message using subclass implementation
        3. Returns response in A2A protocol format
        4. Handles errors with proper JSON-RPC error codes
        
        Args:
            context: Request context with message and metadata
            event_queue: Queue for sending events/responses
        """
        try:
            # Extract message from A2A protocol format
            message = self._extract_message(context)
            
            if not message:
                raise InvalidParamsError("No message provided in request")
            
            self.logger.info(f"Processing message: {message[:100]}...")
            
            # Process message using subclass implementation
            response = await self.process_message(message)
            
            # Send response in A2A protocol format
            await event_queue.enqueue_event(
                new_agent_text_message(response)
            )
            
            self.logger.info("Message processed successfully")
            
        except ServerError:
            # A2A SDK errors are already properly formatted
            raise
        except Exception as e:
            # Wrap other errors in ServerError for proper JSON-RPC format
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
        Extract text message from A2A protocol format.
        
        Handles both message part formats:
        - part.root.text (standard format)
        - part.text (alternative format)
        
        Args:
            context: Request context containing message
            
        Returns:
            Extracted text message or None if no message found
        """
        if not context.message or not context.message.parts:
            return None
        
        for part in context.message.parts:
            # Check for standard format (part.root.text)
            if hasattr(part, 'root') and isinstance(part.root, TextPart):
                return part.root.text
            # Check for alternative format (part.text)
            elif hasattr(part, 'text'):
                return part.text
        
        return None
    
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
            Response text to send back to the user
        """
        pass
    
    # Optional methods that subclasses can override
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """
        Return list of agent skills.
        Override to provide specific skills.
        
        Returns:
            List of AgentSkill objects (empty by default)
        """
        return []
    
    def get_input_modes(self) -> List[str]:
        """
        Return supported input modes.
        Override to customize.
        
        Returns:
            List of supported input MIME types
        """
        return ["text/plain", "application/json"]
    
    def get_output_modes(self) -> List[str]:
        """
        Return supported output modes.
        Override to customize.
        
        Returns:
            List of supported output MIME types
        """
        return ["text/plain", "application/json"]
    
    def supports_streaming(self) -> bool:
        """
        Whether agent supports streaming responses.
        Override to enable streaming.
        
        Returns:
            False by default
        """
        return False
    
    def supports_push_notifications(self) -> bool:
        """
        Whether agent supports push notifications.
        Override to enable push notifications.
        
        Returns:
            False by default
        """
        return False
    
    # Optional LLM helper methods
    
    def get_llm_client(self):
        """
        Helper to get an LLM client with automatic provider detection.
        Detects and uses ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY.
        
        Usage in your process_message method:
            llm = self.get_llm_client()
            response = llm.generate_text("Your prompt here")
        
        Returns:
            LLM client with generate_text method, or None if no API key found
        """
        try:
            from utils.llm_utils import get_llm
            return get_llm(system_instruction=self.get_system_instruction())
        except (ImportError, RuntimeError) as e:
            self.logger.warning(f"LLM initialization failed: {e}")
            return None
    
    def get_system_instruction(self) -> str:
        """
        Override to provide custom system instruction for LLM agents.
        
        Returns:
            System instruction for the LLM
        """
        return "You are a helpful AI assistant."
    
    async def call_other_agent(self, agent_url: str, message: str, timeout: float = 30.0) -> str:
        """
        Helper method to call another A2A-compliant agent.
        
        Args:
            agent_url: URL of the agent to call
            message: Message to send to the agent
            timeout: Request timeout in seconds
            
        Returns:
            Response from the other agent
            
        Usage:
            response = await self.call_other_agent(
                "https://other-agent.example.com",
                "Hello from my agent!"
            )
        """
        try:
            from utils.a2a_client import A2AAgentClient
            async with A2AAgentClient(timeout=timeout) as client:
                return await client.call_agent(agent_url, message)
        except Exception as e:
            self.logger.error(f"Failed to call agent at {agent_url}: {e}")
            raise ServerError(error=e)