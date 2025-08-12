"""
Base class for simple non-LLM A2A agents.
Provides minimal boilerplate with full A2A compliance.
"""

import os
import logging
from datetime import datetime
from typing import Optional
from abc import ABC, abstractmethod

from dotenv import load_dotenv

# A2A imports
from a2a.utils import new_task, new_agent_text_message
from a2a.types import Task, TaskState
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
# Import directly to avoid protobuf issues
from a2a.server.apps import A2AStarletteApplication
from a2a.types import (
    AgentCard,
    AgentProvider,
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BaseAgentExecutor(AgentExecutor, ABC):
    """
    Base class for simple non-LLM A2A agents.
    Provides minimal boilerplate with full A2A protocol compliance.
    Perfect for deterministic processing, routing, validation, etc.
    """
    
    def __init__(self):
        """Initialize the base agent executor."""
        super().__init__()
        logger.info(f"🚀 Initializing {self.__class__.__name__}")
        
        # Load environment configuration
        load_dotenv()
        
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
            logger.info("💻 Running in local development mode")
        
        logger.info(f"✅ {self.__class__.__name__} initialization complete!")
    
    @abstractmethod
    def get_agent_name(self) -> str:
        """Return the agent's name."""
        pass
    
    @abstractmethod
    def get_agent_description(self) -> str:
        """Return the agent's description for AgentCard."""
        pass
    
    @abstractmethod
    async def process_message(self, message: str) -> str:
        """
        Process an incoming message and return a response.
        This is the main method to implement for non-LLM agents.
        
        Args:
            message: The input message to process
            
        Returns:
            The response message
        """
        pass
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Execute method that handles A2A protocol requirements.
        Extracts message, calls process_message, and manages task state.
        """
        request_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        logger.info(f"🚀 [{request_id}] Starting request execution")
        
        try:
            # Extract the user's message
            logger.info(f"📝 [{request_id}] Extracting user message...")
            message_parts = context.message.parts if context.message else []
            user_message = ""
            
            if message_parts and len(message_parts) > 0:
                first_part = message_parts[0]
                
                # Handle different part types
                if hasattr(first_part, "root"):
                    if hasattr(first_part.root, "text"):
                        user_message = first_part.root.text
                elif hasattr(first_part, "text"):
                    user_message = first_part.text
                else:
                    logger.warning(f"⚠️ [{request_id}] Unsupported message part type")
            
            if not user_message.strip():
                logger.warning(f"❌ [{request_id}] Empty message received")
                response_msg = f"Please provide input for {self.get_agent_name()}"
                await event_queue.enqueue_event(new_agent_text_message(response_msg))
                return
            
            logger.info(f"💬 [{request_id}] Processing message: {user_message[:100]}...")
            
            # Handle task context
            task = context.current_task
            
            if not task:
                logger.info(f"✨ [{request_id}] Creating new task")
                task = new_task(context.message)
                if task:
                    logger.info(f"📋 [{request_id}] Task created: {task.id}")
                    await event_queue.enqueue_event(task)
            else:
                logger.info(f"♻️ [{request_id}] Using existing task: {task.id}")
            
            # Create task updater
            updater = TaskUpdater(event_queue, task.id, task.context_id)
            
            # Set task to working state
            await updater.set_working()
            
            # Process the message
            try:
                response = await self.process_message(user_message)
                
                if response:
                    # Send response
                    await updater.send_agent_text_message(response)
                    logger.info(f"✅ [{request_id}] Response sent successfully")
                else:
                    # Empty response
                    await updater.send_agent_text_message("No response generated")
                    logger.warning(f"⚠️ [{request_id}] Empty response from process_message")
                
                # Mark task as completed
                await updater.set_completed()
                logger.info(f"✅ [{request_id}] Task completed successfully")
                
            except NotImplementedError as e:
                logger.error(f"❌ [{request_id}] Not implemented: {str(e)}")
                await updater.send_agent_text_message(f"Feature not implemented: {str(e)}")
                await updater.set_failed("Not implemented")
                
            except ValueError as e:
                logger.error(f"❌ [{request_id}] Validation error: {str(e)}")
                await updater.send_agent_text_message(f"Invalid input: {str(e)}")
                await updater.set_failed(str(e))
                
            except Exception as e:
                logger.error(f"💥 [{request_id}] Error processing message: {str(e)}")
                await updater.send_agent_text_message(f"Error: {str(e)}")
                await updater.set_failed(str(e))
                raise
        
        except Exception as e:
            logger.error(f"💥 [{request_id}] Fatal error in execute: {str(e)}", exc_info=True)
            if task:
                updater = TaskUpdater(event_queue, task.id, task.context_id)
                await updater.set_failed(f"Fatal error: {str(e)}")
            raise
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle task cancellation requests."""
        if context.current_task:
            logger.info(f"🛑 Cancelling task: {context.current_task.id}")
            updater = TaskUpdater(event_queue, context.current_task.id, context.current_task.context_id)
            await updater.set_cancelled("Cancelled by user")
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
        logger.info(f"🔗 Well-known endpoint: {self.agent_url}/.well-known/agentcard.json")
        logger.info(f"💚 Health endpoint: {self.agent_url}/health")
        uvicorn.run(app, host=host, port=port)
    
    def _create_agent_card(self) -> AgentCard:
        """Create the agent card with automatic compliance."""
        agent_card = create_compliant_agent_card(
            name=self.get_agent_name(),
            description=self.get_agent_description(),
            streaming=False  # Simple agents don't stream by default
        )
        
        # Validate on startup
        validate_startup(agent_card, raise_on_error=True)
        
        return agent_card