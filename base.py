"""
Full-featured A2A-compliant base class for agents.
Supports LLM integration, tools, streaming, and agent-to-agent communication.
Full A2A v0.3.0 compliance with Google ADK integration.
"""

import os
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
    TaskState
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
        Execute agent logic with full A2A protocol compliance.
        
        Supports:
        - Proper task state management (working, completed, failed)
        - Streaming updates via TaskUpdater
        - Tool-based execution via Google ADK
        - Automatic LLM integration
        
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
            
            # Get or create task (A2A spec requirement)
            task = context.current_task
            if not task:
                self.logger.info("Creating new task")
                task = new_task(context.message or new_agent_text_message("Processing..."))
                await event_queue.enqueue_event(task)
            
            # Create TaskUpdater for streaming updates (A2A spec compliant)
            updater = TaskUpdater(event_queue, task.id, task.context_id or task.id)
            
            # Set task to working state
            await updater.update_status(
                TaskState.working,
                new_agent_text_message("Processing your request...")
            )
            
            # Check if agent has tools
            tools = self.get_tools()
            
            if tools:
                # Execute with Google ADK LlmAgent and tools
                self.logger.info(f"Executing with {len(tools)} tools via Google ADK")
                await self._execute_with_tools(message, updater, task.id)
            else:
                # Simple message processing (may still use LLM via process_message)
                self.logger.info("Executing without tools")
                response = await self.process_message(message)
                
                # Add response as artifact
                await updater.add_artifact(
                    [Part(root=TextPart(text=response))],
                    name="response"
                )
            
            # Mark task as completed
            await updater.complete()
            self.logger.info("Task completed successfully")
            
        except ServerError:
            # A2A SDK errors are already properly formatted
            raise
        except Exception as e:
            # Mark task as failed and raise error
            self.logger.error(f"Error processing message: {str(e)}")
            if 'updater' in locals():
                await updater.failed(new_agent_text_message(f"Error: {str(e)}"))
            raise ServerError(error=e)
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Handle cancellation requests.
        Default implementation raises error - override if cancellation is supported.
        """
        from a2a.utils.errors import UnsupportedOperationError
        raise ServerError(error=UnsupportedOperationError("Cancellation not supported"))
    
    async def _execute_with_tools(self, message: str, updater: TaskUpdater, session_id: str) -> None:
        """
        Execute using Google ADK LlmAgent with tools and streaming.
        
        Args:
            message: The user's message
            updater: TaskUpdater for sending status updates
            session_id: Session/task ID for context
        """
        from google.adk.agents.llm_agent import LlmAgent
        from google.adk.runners import Runner
        from google.adk.artifacts import InMemoryArtifactService
        from google.adk.sessions import InMemorySessionService
        from google.adk.memory import InMemoryMemoryService
        from google.genai import types
        
        try:
            # Build LLM agent with tools
            agent = LlmAgent(
                model=self._get_llm_model(),
                name=self.get_agent_name().lower().replace(" ", "_"),
                instruction=self.get_system_instruction(),
                tools=self.get_tools()
            )
            
            # Create runner with session management
            runner = Runner(
                app_name=agent.name,
                agent=agent,
                artifact_service=InMemoryArtifactService(),
                session_service=InMemorySessionService(),
                memory_service=InMemoryMemoryService()
            )
            
            # Get or create session
            session = await runner.session_service.get_session(
                app_name=agent.name,
                user_id="user",
                session_id=session_id
            )
            if not session:
                session = await runner.session_service.create_session(
                    app_name=agent.name,
                    user_id="user",
                    state={},
                    session_id=session_id
                )
            
            # Format message for Google ADK
            formatted_message = types.Content(
                role="user", 
                parts=[types.Part(text=message)]
            )
            
            # Stream response
            full_response = ""
            async for event in runner.run_async(
                user_id="user",
                session_id=session.id,
                new_message=formatted_message
            ):
                if event.is_final_response():
                    # Final response - extract text
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                full_response += part.text
                        
                        # Add as artifact
                        await updater.add_artifact(
                            [Part(root=TextPart(text=full_response))],
                            name="response"
                        )
                else:
                    # Intermediate update - send partial response
                    if hasattr(event, "content") and event.content:
                        partial = ""
                        if hasattr(event.content, "parts"):
                            for part in event.content.parts:
                                if hasattr(part, "text") and part.text:
                                    partial += part.text
                        
                        if partial:
                            # Send streaming update
                            await updater.update_status(
                                TaskState.working,
                                new_agent_text_message(partial)
                            )
                            
        except Exception as e:
            self.logger.error(f"Error in tool execution: {str(e)}")
            raise
    
    def _get_llm_model(self) -> str:
        """
        Get the LLM model to use based on available API keys.
        
        Returns:
            Model string for Google ADK
        """
        # Check for Gemini/Google
        if os.getenv("GOOGLE_API_KEY"):
            return os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")
        # Check for OpenAI
        elif os.getenv("OPENAI_API_KEY"):
            from google.adk.models.lite_llm import LiteLlm
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            # Return LiteLLM wrapper for OpenAI
            return LiteLlm(model=model)
        # Check for Anthropic
        elif os.getenv("ANTHROPIC_API_KEY"):
            from google.adk.models.lite_llm import LiteLlm
            model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
            # Return LiteLLM wrapper for Anthropic
            return LiteLlm(model=model)
        else:
            raise ValueError("No LLM API key found. Set GOOGLE_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY")
    
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
    
    def get_tools(self) -> List[Any]:
        """
        Return list of tools for LLM-powered agents.
        
        Tools are internal implementation details (not exposed in AgentCard).
        When tools are provided, the agent will use Google ADK's LlmAgent
        with automatic tool execution and streaming support.
        
        Example:
            from google.adk.tools import FunctionTool
            
            def search(query: str) -> str:
                return f"Results for {query}"
            
            def get_tools(self):
                return [FunctionTool(func=search)]
        
        Returns:
            List of tools (e.g., Google ADK FunctionTools) or empty list
        """
        return []
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """
        Return list of agent skills for the AgentCard.
        
        Skills describe agent capabilities for discovery (A2A spec).
        These are metadata only - not function definitions.
        
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
        
        This instruction is used when tools are provided and the agent
        uses Google ADK's LlmAgent for execution.
        
        Returns:
            System instruction for the LLM
        """
        return "You are a helpful AI assistant."
    
    async def call_other_agent(self, agent_name_or_url: str, message: str, timeout: float = 30.0) -> str:
        """
        Helper method to call another A2A-compliant agent.
        
        Args:
            agent_name_or_url: Agent name (from registry) or direct URL
            message: Message to send to the agent
            timeout: Request timeout in seconds
            
        Returns:
            Response from the other agent
            
        Usage:
            # Using agent name from config/agents.json
            response = await self.call_other_agent(
                "calculator-agent",
                "What is 2+2?"
            )
            
            # Or using direct URL (e.g., HealthUniverse deployment)
            response = await self.call_other_agent(
                "https://apps.healthuniverse.com/vey-vou-nam",
                "Hello from my agent!"
            )
        """
        try:
            from utils.a2a_client import A2AAgentClient, AgentRegistry
            
            # Determine if this is a URL or agent name
            if agent_name_or_url.startswith(('http://', 'https://')):
                # Direct URL provided
                agent_url = agent_name_or_url
            else:
                # Look up agent name in registry
                registry = AgentRegistry()
                agent_url = registry.get_agent_url(agent_name_or_url)
                if not agent_url:
                    raise ValueError(f"Agent '{agent_name_or_url}' not found in registry. "
                                   f"Available agents: {', '.join(registry.list_agents()) or 'none'}")
            
            self.logger.info(f"📤 Calling agent at {agent_url}")
            self.logger.info(f"📝 Message: {message[:200]}..." if len(message) > 200 else f"📝 Message: {message}")
            
            async with A2AAgentClient(timeout=timeout) as client:
                response = await client.call_agent(agent_url, message)
                
            self.logger.info(f"📥 Response from {agent_url}: {response[:200]}..." if len(str(response)) > 200 else f"📥 Response: {response}")
            return response
        except Exception as e:
            self.logger.error(f"Failed to call agent '{agent_name_or_url}': {e}")
            raise ServerError(error=e)