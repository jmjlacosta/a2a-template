"""
Base class for LLM-powered A2A agents.
Handles all A2A protocol compliance, LLM integration, and session management.
"""

import os
import sys
import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, AsyncIterable, List, AsyncIterator
from abc import ABC, abstractmethod
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Google ADK imports
try:
    from google.adk.agents.llm_agent import LlmAgent
    from google.adk.runners import Runner
    from google.adk.artifacts import InMemoryArtifactService
    from google.adk.sessions import InMemorySessionService
    from google.adk.memory import InMemoryMemoryService
    from google.adk.tools import FunctionTool
    from google.adk.models.lite_llm import LiteLlm
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    print("Warning: Google ADK not installed. LLM features will be limited.")

# A2A imports
from a2a.utils import new_task, new_agent_text_message
from a2a.types import Task, TaskState, Message, Part, TextPart
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
# Import directly to avoid protobuf issues
from a2a.server.apps import A2AStarletteApplication
from a2a.types import (
    AgentCard,
    AgentProvider,
    AgentSkill,
    AgentCapabilities,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler

# Import compliance module
from .compliance import (
    create_compliant_agent_card,
    validate_startup,
    PlatformDetector
)
from .task_manager import TaskManager, create_task_manager
from .errors import (
    ErrorHandler,
    create_error_response,
    enrich_error_context,
    TaskTerminalStateError,
    A2AException
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BaseLLMAgentExecutor(AgentExecutor, ABC):
    """
    Base class for LLM-powered A2A agents.
    Provides automatic A2A protocol compliance and LLM integration.
    """
    
    def __init__(self, use_llm: bool = True):
        """
        Initialize the base LLM agent executor.
        
        Args:
            use_llm: Whether to use LLM capabilities (default True)
        """
        super().__init__()
        logger.info(f"🚀 Initializing {self.__class__.__name__}")
        
        # Load environment configuration
        logger.info("📊 Loading environment configuration...")
        load_dotenv()
        
        self.use_llm = use_llm and ADK_AVAILABLE
        self._agent = None
        self._runner = None
        
        if self.use_llm:
            # Check API key configuration
            self._configure_llm_provider()
            
            # Build the LLM agent
            logger.info("🔧 Building LLM agent...")
            self._agent = self._build_llm_agent()
            logger.info(f"✅ LLM agent '{self._agent.name}' created successfully")
            
            # Create runner with services for session management
            logger.info("🏃 Creating runner with session management services...")
            self._session_service = InMemorySessionService()
            self._runner = Runner(
                app_name=self._agent.name,
                agent=self._agent,
                artifact_service=InMemoryArtifactService(),
                session_service=self._session_service,
                memory_service=InMemoryMemoryService(),
            )
            logger.info("📝 Session management services initialized")
            
            # Create a default session for the agent
            self._default_session_id = f"agent_session_{self._agent.name.replace(' ', '_').lower()}"
            self._default_user_id = "default_user"
            
            # Initialize the session using the synchronous method
            self._session_service.create_session_sync(
                app_name=self._agent.name,
                user_id=self._default_user_id,
                session_id=self._default_session_id
            )
            logger.info(f"✅ Created default session: {self._default_session_id}")
        else:
            logger.info("🔌 Running in non-LLM mode")
        
        # Heartbeat configuration for long-running tasks
        self._heartbeat_interval = float(os.getenv("AGENT_HEARTBEAT_INTERVAL", "10.0"))
        self._chunk_timeout = float(os.getenv("AGENT_CHUNK_TIMEOUT", "120.0"))
        logger.info(f"💓 Heartbeat interval: {self._heartbeat_interval}s")
        logger.info(f"⏱️ Chunk timeout: {self._chunk_timeout}s")
        
        # Error handling configuration
        self.error_handler = ErrorHandler(
            enable_retry=os.getenv("A2A_ENABLE_RETRY", "true").lower() == "true",
            enable_timeout=os.getenv("A2A_ENABLE_TIMEOUT", "true").lower() == "true",
            enable_circuit_breaker=os.getenv("A2A_ENABLE_CIRCUIT_BREAKER", "false").lower() == "true",
            timeout=self._chunk_timeout,
            max_retries=int(os.getenv("A2A_MAX_RETRIES", "3"))
        )
        
        # Platform detection
        self.platform_info = PlatformDetector.detect()
        self.agent_url = self.platform_info["agent_url"]
        self.is_healthuniverse = self.platform_info["is_healthuniverse"]
        self.agent_id = self.platform_info["agent_id"]
        
        if self.is_healthuniverse:
            logger.info(f"🌐 Running on HealthUniverse: {self.agent_url}")
            if self.agent_id:
                logger.info(f"🆔 Agent ID: {self.agent_id}")
        else:
            logger.info(f"💻 Running in local development mode")
        
        logger.info(f"✅ {self.__class__.__name__} initialization complete!")
    
    def _configure_llm_provider(self):
        """Auto-detect and configure LLM provider based on available API keys."""
        google_api_key = os.getenv("GOOGLE_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        provider_override = os.getenv("LLM_PROVIDER", "").lower()
        
        logger.info(f"🔑 Google API Key: {'✅ Configured' if google_api_key else '❌ Missing'}")
        logger.info(f"🔑 OpenAI API Key: {'✅ Configured' if openai_api_key else '❌ Missing'}")
        logger.info(f"🔑 Anthropic API Key: {'✅ Configured' if anthropic_api_key else '❌ Missing'}")
        
        if provider_override:
            logger.info(f"🎛️ LLM provider override: {provider_override}")
        
        # Provider configuration with fallback support
        provider_config = self._get_provider_config(
            google_api_key, openai_api_key, anthropic_api_key, provider_override
        )
        
        self._provider = provider_config["provider"]
        self._model = provider_config["model"]
        self._api_key = provider_config["key"]
        
        # Set environment variables for LiteLLM
        if self._provider == "openai" and openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
        elif self._provider == "anthropic" and anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key
        
        logger.info(f"🎯 Selected provider: {self._provider} with model: {self._model}")
        
        self._user_id = f"{self.get_agent_name()}_user"
        logger.info(f"👤 Agent user ID: {self._user_id}")
    
    def _get_provider_config(self, google_key, openai_key, anthropic_key, override=None):
        """Get provider configuration with fallback support."""
        available_providers = []
        
        # Build list of available providers
        if google_key:
            available_providers.append({
                "provider": "google",
                "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001"),
                "key": google_key
            })
        
        if openai_key:
            available_providers.append({
                "provider": "openai", 
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "key": openai_key
            })
            
        if anthropic_key:
            available_providers.append({
                "provider": "anthropic",
                "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"),
                "key": anthropic_key
            })
        
        if not available_providers:
            raise ValueError(
                "❌ No LLM API key found! Please set either GOOGLE_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY"
            )
        
        # Handle provider override
        if override:
            for provider in available_providers:
                if provider["provider"] == override:
                    logger.info(f"✅ Using override provider: {override}")
                    return provider
            
            logger.warning(f"⚠️ Override provider '{override}' not available, falling back to auto-detection")
        
        # Return first available provider (priority: Google > OpenAI > Anthropic)
        selected = available_providers[0]
        logger.info(f"✅ Auto-selected provider: {selected['provider']}")
        return selected
    
    @abstractmethod
    def get_agent_name(self) -> str:
        """Return the agent's name."""
        pass
    
    @abstractmethod
    def get_agent_description(self) -> str:
        """Return the agent's description for AgentCard."""
        pass
    
    @abstractmethod
    def get_system_instruction(self) -> str:
        """Return the system instruction for the LLM agent."""
        pass
    
    @abstractmethod
    def get_tools(self) -> List[FunctionTool]:
        """Return the list of tools for this agent."""
        pass
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """Return list of agent skills (optional override)."""
        return []
    
    def supports_streaming(self) -> bool:
        """Whether agent supports SSE streaming (optional override)."""
        return True  # Default true for LLM agents
    
    def _build_llm_agent(self) -> LlmAgent:
        """Build the LLM agent with tools and instructions."""
        if not ADK_AVAILABLE:
            raise RuntimeError("Google ADK is not installed")
        
        logger.info("📝 Creating agent-specific system instructions...")
        
        instruction = self.get_system_instruction()
        tools = self.get_tools()
        
        logger.info(f"🛠️ Registering {len(tools)} tools...")
        if tools:
            logger.info(f"📋 Tools: {[tool.name for tool in tools]}")
        
        logger.info("🔨 Creating LlmAgent instance...")
        
        # Check if we need to use LiteLLM for non-Gemini models
        if self._provider in ["openai", "anthropic"]:
            logger.info(f"🔄 Using LiteLLM for {self._provider} model: {self._model}")
            model = LiteLlm(model=self._model)
        else:
            # Use the model string directly (for Gemini)
            model = self._model
        
        agent = LlmAgent(
            model=model,
            name=self.get_agent_name().lower().replace(" ", "_"),
            description=f"LLM-powered {self.get_agent_name()}",
            instruction=instruction,
            tools=tools,
        )
        logger.info(f"✅ LlmAgent created: {agent.name}")
        
        return agent
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Execute method with LLM streaming support, complete state management, and error handling.
        Handles A2A protocol requirements automatically with resilience patterns.
        """
        request_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        logger.info(f"🚀 [{request_id}] Starting request execution")
        
        # Add request_id to context for error handling
        if hasattr(context, '__dict__'):
            context.request_id = request_id
        
        task_manager = None
        try:
            # Extract the user's message
            logger.info(f"📝 [{request_id}] Extracting user message from context...")
            message_parts = context.message.parts if context.message else []
            user_message = ""
            
            if message_parts and len(message_parts) > 0:
                first_part = message_parts[0]
                logger.info(f"🔍 [{request_id}] First part type: {type(first_part).__name__}")
                
                # Handle different part types
                if hasattr(first_part, "root") and isinstance(first_part.root, TextPart):
                    user_message = first_part.root.text
                elif hasattr(first_part, "text"):
                    user_message = first_part.text
                else:
                    logger.warning(f"⚠️ [{request_id}] First message part is not a TextPart")
            
            if not user_message.strip():
                logger.warning(f"❌ [{request_id}] Empty user message received")
                response_msg = f"Please provide input for the {self.get_agent_name()}"
                await event_queue.enqueue_event(new_agent_text_message(response_msg))
                return
            
            logger.info(f"💬 [{request_id}] User message: {user_message[:100]}...")
            
            # Check if task is in terminal state before processing
            if context.current_task:
                current_state = getattr(context.current_task, 'state', None)
                if current_state in ['completed', 'canceled', 'failed', 'rejected']:
                    raise TaskTerminalStateError(
                        context.current_task.id,
                        current_state
                    )
            
            # Create or get task with TaskManager
            logger.info(f"🔍 [{request_id}] Initializing task management...")
            task_manager = create_task_manager(
                context.current_task,
                event_queue,
                context.message
            )
            
            # Get session ID for context
            session_id = task_manager.get_or_create_context_id()
            logger.info(f"🔗 [{request_id}] Using session ID: {session_id}")
            
            # Start task processing
            await task_manager.start_working(f"Processing with {self.get_agent_name()}...")
            
            # Get task updater for backward compatibility
            updater = task_manager.updater
            
            if self.use_llm and self._runner:
                # Stream responses from the LLM agent
                logger.info(f"🌊 [{request_id}] Starting LLM streaming for session: {session_id}")
                
                has_updates = False
                chunk_count = 0
                last_heartbeat_time = time.time()
                accumulated_response = ""
                
                try:
                    # Create Content message for the runner
                    from google.adk.runners import types
                    text_part = types.Part(text=user_message)
                    message = types.Content(parts=[text_part], role="user")
                    
                    # Use run_async which actually exists
                    async for event in self._runner.run_async(
                        user_id=self._default_user_id,
                        session_id=self._default_session_id,
                        new_message=message,
                    ):
                        chunk_count += 1
                        has_updates = True
                        
                        # Extract text from event
                        chunk = ""
                        if hasattr(event, 'text'):
                            chunk = event.text
                        elif hasattr(event, 'content') and hasattr(event.content, 'text'):
                            chunk = event.content.text
                        
                        # Accumulate response
                        if chunk:
                            accumulated_response += chunk
                            
                            # Send update through task updater
                            if chunk_count % 5 == 0:  # Send every 5 chunks to reduce overhead
                                await updater.new_agent_message(accumulated_response)
                        
                        # Send heartbeat if needed
                        current_time = time.time()
                        if current_time - last_heartbeat_time > self._heartbeat_interval:
                            logger.info(f"💓 [{request_id}] Sending heartbeat at chunk {chunk_count}")
                            await updater.update_status("Still processing...")
                            last_heartbeat_time = current_time
                    
                    # Send final accumulated response
                    if accumulated_response and chunk_count % 5 != 0:
                        await updater.new_agent_message(accumulated_response)
                    
                    # Mark task as completed
                    await task_manager.complete_task("Task completed successfully")
                    logger.info(f"✅ [{request_id}] Task completed successfully after {chunk_count} chunks")
                    
                except asyncio.TimeoutError:
                    logger.error(f"⏱️ [{request_id}] Timeout after {self._chunk_timeout}s")
                    await task_manager.fail_task("Request timed out")
                except Exception as e:
                    logger.error(f"❌ [{request_id}] Error during streaming: {str(e)}")
                    await task_manager.fail_task(str(e))
                    raise
                
                if not has_updates:
                    logger.warning(f"⚠️ [{request_id}] No updates received from LLM")
                    await updater.new_agent_message("No response generated")
                    await task_manager.complete_task("No response generated")
            else:
                # Non-LLM mode - call process_message
                logger.info(f"🔌 [{request_id}] Processing in non-LLM mode")
                response = await self.process_message(user_message)
                await updater.new_agent_message(response)
                await task_manager.complete_task("Task completed")
        
        except A2AException as e:
            # Handle A2A-specific exceptions
            logger.error(f"💥 [{request_id}] A2A Error: {str(e)}", exc_info=True)
            
            # Create error response
            error_response = create_error_response(
                exc=e,
                request_id=request_id,
                context=enrich_error_context(e, context)
            )
            
            # Send error through event queue
            await event_queue.enqueue_event(error_response)
            
            # Update task state if applicable
            if task_manager and not task_manager.is_terminal():
                await task_manager.fail_task(str(e))
                
        except Exception as e:
            # Handle unexpected exceptions
            logger.error(f"💥 [{request_id}] Unexpected error: {str(e)}", exc_info=True)
            
            # Create error response
            error_response = create_error_response(
                exc=e,
                request_id=request_id,
                context=enrich_error_context(e, context)
            )
            
            # Send error through event queue
            await event_queue.enqueue_event(error_response)
            
            # Update task state if applicable
            if task_manager and not task_manager.is_terminal():
                await task_manager.fail_task(str(e))
            
            # Re-raise for debugging if configured
            if os.getenv("A2A_RAISE_ERRORS", "false").lower() == "true":
                raise
                
        finally:
            # Ensure heartbeat is stopped
            if task_manager:
                await task_manager.stop_heartbeat()
    
    async def process_message(self, message: str) -> str:
        """
        Process a message without LLM. Override this for non-LLM functionality.
        
        Args:
            message: The input message to process
            
        Returns:
            The response message
        """
        return f"Received: {message} (LLM not configured)"
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle task cancellation requests with proper state management."""
        if context.current_task:
            logger.info(f"🛑 Cancelling task: {context.current_task.id}")
            task_manager = TaskManager(context.current_task, event_queue)
            await task_manager.cancel_task("Cancelled by user")
        else:
            logger.warning("⚠️ No task to cancel")
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """
        Run the agent as a standalone server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        import uvicorn
        from a2a.server.request_handlers import DefaultRequestHandler
        from a2a.server.tasks import InMemoryTaskStore
        from .app_builder import create_compliant_app
        
        # Create agent card
        agent_card = self._create_agent_card()
        
        # Create request handler
        request_handler = DefaultRequestHandler(
            agent_executor=self,
            task_store=InMemoryTaskStore(),
        )
        
        # Create app with compliance endpoints
        app = create_compliant_app(
            agent_card=agent_card,
            request_handler=request_handler,
            agent_name=self.get_agent_name()
        )
        
        # Run server
        logger.info(f"🚀 Starting {self.get_agent_name()} on {host}:{port}")
        logger.info(f"📍 Agent URL: {self.agent_url}")
        logger.info(f"🔗 A2A endpoint: {self.agent_url}/.well-known/agent-card.json")
        logger.info(f"🔗 HU endpoint: {self.agent_url}/.well-known/agent.json")
        logger.info(f"💚 Health endpoint: {self.agent_url}/health")
        uvicorn.run(app, host=host, port=port)
    
    def _create_agent_card(self) -> AgentCard:
        """Create the agent card with automatic compliance."""
        agent_card = create_compliant_agent_card(
            name=self.get_agent_name(),
            description=self.get_agent_description(),
            skills=self.get_agent_skills(),
            streaming=self.supports_streaming()
        )
        
        # Validate on startup
        validate_startup(agent_card, raise_on_error=True)
        
        return agent_card