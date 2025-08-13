"""
LLM-powered A2A Nutrition Agent Server
Enhanced with Google ADK for intelligent nutrition analysis and recommendations.
"""

import os
import json
import uvicorn
import logging
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any, Optional, AsyncIterable

# Google ADK and Gemini imports
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.tools import FunctionTool

from a2a.utils import new_task
from a2a.types import Task, TaskState
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.server.apps import A2AStarletteApplication
from a2a.types import (
    AgentCard,
    AgentProvider,
    AgentSkill,
    AgentCapabilities,
    Part,
    TextPart,
)
from a2a.utils import new_agent_text_message
from a2a.utils.errors import ServerError, UnsupportedOperationError
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler, RequestHandler

# Import nutrition tools
from nutrition_tools import (
    analyze_nutrition,
    calculate_meal_totals,
    get_nutrition_recommendations,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LLMNutritionAgentExecutor(AgentExecutor):
    """LLM-powered A2A Agent Executor for intelligent nutrition analysis and recommendations."""

    def __init__(self):
        super().__init__()
        logger.info("🚀 Initializing LLM Nutrition Agent Executor")
        logger.info("📊 Loading environment configuration...")

        load_dotenv()

        # Check API key configuration
        google_api_key = os.getenv("GOOGLE_API_KEY")
        nutritionix_api_key = os.getenv("NUTRITIONIX_API_KEY")

        logger.info(
            f"🔑 Google API Key: {'✅ Configured' if google_api_key else '❌ Missing'}"
        )
        logger.info(
            f"🍎 Nutritionix API Key: {'✅ Configured' if nutritionix_api_key else '❌ Missing'}"
        )

        if not google_api_key:
            logger.warning("⚠️ GOOGLE_API_KEY not set. LLM features may not work.")

        self._model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")
        self._user_id = "nutrition_agent_user"

        logger.info(f"🤖 Configuring LLM agent with model: {self._model}")
        logger.info(f"👤 Agent user ID: {self._user_id}")

        # Build the LLM agent
        logger.info("🔧 Building LLM agent with nutrition-specific configuration...")
        self._agent = self._build_llm_agent()
        logger.info(f"✅ LLM agent '{self._agent.name}' created successfully")

        # Create runner with services for session management
        logger.info("🏃 Creating runner with session management services...")
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        logger.info("📝 Session management services initialized")
        logger.info("🎯 Memory management services initialized")
        logger.info("📦 Artifact management services initialized")

        logger.info("✅ LLM Nutrition Agent Executor initialization complete!")
        logger.info(
            f"🎯 Agent ready to handle nutrition queries with {len(self._agent.tools)} tools available"
        )

    def _build_llm_agent(self) -> LlmAgent:
        """Build the LLM agent with nutrition-specific configuration."""
        logger.info("📝 Creating nutrition-specific system instructions...")

        instruction = """
You are a specialized AI nutrition assistant with access to comprehensive food and nutrition data. Your role is to help users understand their nutritional intake, make informed food choices, and achieve their health goals.

CORE CAPABILITIES:
1. Analyze nutritional content of individual foods and complete meals
2. Calculate daily nutrition totals and compare against recommended values  
3. Provide personalized nutrition recommendations
4. Answer questions about nutrition, health, and dietary choices
5. Help with meal planning and food substitutions

INTERACTION PRINCIPLES:
- Always be helpful, accurate, and supportive
- Use the nutrition analysis tools to provide precise data when discussing specific foods
- Consider the user's dietary restrictions, goals, and preferences
- Provide context and explanations, not just raw numbers
- Suggest practical, actionable advice

DECISION PROCESS:
1. If the user asks about specific foods or meals, use the analyze_nutrition or calculate_meal_totals tools
2. If they want recommendations, use get_nutrition_recommendations after analyzing their current intake
3. For general nutrition questions, provide evidence-based information
4. Always explain the nutritional significance of the data you provide

RESPONSE STYLE:
- Be conversational and engaging
- Break down complex nutritional information into understandable terms
- Use specific numbers from your analysis tools when relevant
- Provide actionable next steps or suggestions
- Ask clarifying questions if needed to give better advice

IMPORTANT: Always use the available tools when analyzing specific foods or calculating nutritional values. Don't estimate or guess nutritional information when you have tools available to provide accurate data.
"""

        logger.info("🛠️ Registering nutrition analysis tools...")
        function_tools = [
            analyze_nutrition,
            calculate_meal_totals,
            get_nutrition_recommendations,
        ]
        logger.info(
            f"📋 Raw functions registered: {[tool.__name__ for tool in function_tools]}"
        )

        # Wrap functions as FunctionTool objects
        logger.info("🔧 Wrapping functions as FunctionTool objects...")
        tools = [FunctionTool(func=tool) for tool in function_tools]
        logger.info(f"✅ Created {len(tools)} FunctionTool instances")

        logger.info("🔨 Creating LlmAgent instance...")
        agent = LlmAgent(
            model=self._model,
            name="ai_nutrition_assistant",
            description="AI-powered nutrition analysis and meal planning assistant with access to comprehensive food database",
            instruction=instruction,
            tools=tools,
        )
        logger.info(f"✅ LlmAgent created: {agent.name}")
        logger.info(f"📖 Agent description: {agent.description[:100]}...")

        return agent

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute method with LLM streaming support."""
        request_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        logger.info(f"🚀 [{request_id}] Starting LLM request execution")
        logger.info(f"📥 [{request_id}] Request context received")

        try:
            # Extract the user's message
            logger.info(f"📝 [{request_id}] Extracting user message from context...")
            message_parts = context.message.parts if context.message else []
            user_message = ""

            logger.info(f"📊 [{request_id}] Message parts count: {len(message_parts)}")
            logger.info(f"📊 [{request_id}] Message parts: {message_parts}")

            if message_parts and len(message_parts) > 0:
                first_part = message_parts[0]
                logger.info(
                    f"🔍 [{request_id}] First part type: {type(first_part).__name__}"
                )

                # Properly differentiate TextPart from other part types
                if hasattr(first_part, "root") and isinstance(
                    first_part.root, TextPart
                ):
                    user_message = first_part.root.text
                    logger.info(
                        f"💬 [{request_id}] TextPart extracted ({len(user_message)} chars): {user_message[:200]}..."
                    )
                elif hasattr(first_part, "text"):
                    # Fallback for direct text attribute (legacy support)
                    user_message = first_part.text
                    logger.info(
                        f"💬 [{request_id}] Text attribute extracted ({len(user_message)} chars): {user_message[:200]}..."
                    )
                else:
                    logger.warning(
                        f"⚠️ [{request_id}] First message part is not a TextPart and has no text attribute"
                    )
                    logger.warning(f"⚠️ [{request_id}] Part structure: {first_part}")
            else:
                logger.warning(f"⚠️ [{request_id}] No message parts found")

            if not user_message.strip():
                logger.warning(f"❌ [{request_id}] Empty user message received")
                response_msg = "Please provide a nutrition-related question or food description to analyze."
                logger.info(
                    f"📤 [{request_id}] Sending empty message response: {response_msg}"
                )
                await event_queue.enqueue_event(new_agent_text_message(response_msg))
                return

            # Check if this is a continuing task or new task
            logger.info(f"🔍 [{request_id}] Checking task context...")
            task = context.current_task
            session_id = None

            if not task:
                # Create new task for this conversation
                logger.info(
                    f"✨ [{request_id}] No existing task found - creating new task"
                )
                # Provide a default message if none exists
                default_message = new_agent_text_message(
                    "Welcome to the AI Nutrition Assistant!"
                )
                task = new_task(context.message if context.message else default_message)
                if task:
                    logger.info(
                        f"📋 [{request_id}] New task created with ID: {task.id}"
                    )
                    await event_queue.enqueue_event(task)
                    session_id = task.id  # Use task ID as session ID
                    logger.info(f"🆔 [{request_id}] Session ID set to: {session_id}")
                else:
                    logger.error(f"❌ [{request_id}] Failed to create new task")
            else:
                session_id = task.context_id or task.id
                logger.info(f"♻️ [{request_id}] Continuing existing task ID: {task.id}")
                logger.info(f"🆔 [{request_id}] Using session ID: {session_id}")

            # Create task updater for streaming updates
            # Ensure session_id is always a valid string
            logger.info(f"📡 [{request_id}] Creating task updater for streaming...")
            logger.info(
                f"🔧 [{request_id}] Task ID: {task.id}, Context ID: {task.context_id}"
            )
            updater = TaskUpdater(event_queue, task.id, task.context_id)
            logger.info(f"✅ [{request_id}] Task updater created successfully")

            # Stream responses from the LLM agent
            logger.info(
                f"🌊 [{request_id}] Starting LLM streaming for session: {session_id}"
            )
            logger.info(
                f"🎯 [{request_id}] Query will be processed by model: {self._model}"
            )

            has_updates = False
            chunk_count = 0
            logger.info(
                f"📥 [{request_id}] Beginning to process streaming response chunks..."
            )

            async for response_chunk in self._stream_llm_response(
                user_message, session_id
            ):
                chunk_count += 1
                logger.info(f"📦 [{request_id}] Processing chunk #{chunk_count}")

                if response_chunk.get("is_task_complete", True):
                    # Final response - complete the task
                    final_content = response_chunk.get("content", "")
                    has_updates = True  # Mark that we received a final response
                    logger.info(f"✅ [{request_id}] Task completed with final response")
                    logger.info(
                        f"📊 [{request_id}] Final response length: {len(final_content)} characters"
                    )
                    logger.info(
                        f"🏁 [{request_id}] Total chunks processed: {chunk_count}"
                    )

                    # Send the final response as a streaming update BEFORE completing the task
                    if final_content.strip():
                        logger.info(
                            f"📤 [{request_id}] Sending final response to client"
                        )
                        await updater.update_status(
                            TaskState.working,
                            new_agent_text_message(final_content, session_id, task.id),
                        )
                        logger.info(f"✅ [{request_id}] Final response sent to client")

                    # Add the response as an artifact and complete the task
                    logger.info(
                        f"📎 [{request_id}] Adding response as artifact 'nutrition_analysis'"
                    )
                    await updater.add_artifact(
                        [Part(root=TextPart(text=final_content))],
                        name="nutrition_analysis",
                    )
                    logger.info(f"✅ [{request_id}] Artifact added successfully")

                    logger.info(f"🏁 [{request_id}] Completing task...")
                    await updater.complete()
                    logger.info(f"✅ [{request_id}] Task completion confirmed")
                    break
                else:
                    # Intermediate update
                    update_content = response_chunk.get("updates", "")
                    if update_content:
                        has_updates = True
                        logger.info(
                            f"📝 [{request_id}] Streaming update #{chunk_count}: {len(update_content)} chars"
                        )
                        logger.debug(
                            f"🔤 [{request_id}] Update content: {update_content[:100]}..."
                        )

                        logger.info(
                            f"📤 [{request_id}] Sending streaming update to client"
                        )
                        await updater.update_status(
                            TaskState.working,
                            new_agent_text_message(update_content, session_id, task.id),
                        )
                        logger.info(
                            f"✅ [{request_id}] Streaming update sent successfully"
                        )
                    else:
                        logger.warning(
                            f"⚠️ [{request_id}] Chunk #{chunk_count} had no update content"
                        )

            if not has_updates:
                logger.error(
                    f"❌ [{request_id}] No updates received from LLM agent after {chunk_count} chunks"
                )
                error_msg = (
                    "I'm sorry, I couldn't process your request. Please try again."
                )
                logger.info(f"🚨 [{request_id}] Creating error response: {error_msg}")
                await updater.add_artifact(
                    [Part(root=TextPart(text=error_msg))],
                    name="error_response",
                )
                logger.info(f"📝 [{request_id}] Error artifact created")
                await updater.complete()
                logger.info(f"✅ [{request_id}] Error task completion confirmed")

        except Exception as e:
            logger.error(
                f"💥 [{request_id}] Critical error during LLM execution: {str(e)}",
                exc_info=True,
            )
            logger.error(f"🔍 [{request_id}] Exception type: {type(e).__name__}")
            error_message = (
                f"An error occurred while processing your nutrition query: {str(e)}"
            )
            logger.info(
                f"📤 [{request_id}] Sending error message to client: {error_message[:100]}..."
            )
            await event_queue.enqueue_event(new_agent_text_message(error_message))
            logger.info(f"✅ [{request_id}] Error message sent to client")

    async def cancel(self, request: RequestContext, event_queue: EventQueue) -> None:
        """Cancel the current request."""
        logger.info("🛑 Cancellation request received for nutrition agent")
        logger.warning(
            "⚠️ Cancel operation not supported - raising UnsupportedOperationError"
        )
        raise ServerError(error=UnsupportedOperationError())

    async def _stream_llm_response(
        self, query: str, session_id: Optional[str] = None
    ) -> AsyncIterable[Dict[str, Any]]:
        """Stream responses from the LLM agent."""
        logger.info(f"🧠 Processing LLM query: {query[:100]}...")
        logger.info(f"📏 Query length: {len(query)} characters")
        logger.info(f"🆔 Target session ID: {session_id}")

        try:
            # Get or create session
            logger.info(
                f"🔍 Attempting to retrieve session for app: {self._agent.name}"
            )
            logger.info(f"👤 User ID: {self._user_id}")
            session = await self._runner.session_service.get_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                session_id=session_id,
            )
            logger.info(
                f"📊 Session lookup result: {'Found' if session else 'Not found'}"
            )

            if session is None:
                logger.info(f"✨ Creating new session for user {self._user_id}")
                session = await self._runner.session_service.create_session(
                    app_name=self._agent.name,
                    user_id=self._user_id,
                    state={},
                    session_id=session_id,
                )
                logger.info(f"✅ Created new session: {session.id}")
                logger.info(f"📝 Session state: {session.state}")
            else:
                logger.info(f"♻️ Using existing session: {session.id}")
                logger.info(
                    f"📊 Session state keys: {list(session.state.keys()) if session.state else 'empty'}"
                )

            # Stream the LLM response
            logger.info(f"🚀 Starting LLM runner for session {session.id}")
            logger.info(
                f"🎯 Runner configuration: app={self._agent.name}, user={self._user_id}"
            )

            # Format the message properly for Google ADK
            # The ADK expects a structured message format, not a plain string
            from google.genai import types

            logger.info(f"📝 Formatting message for Google ADK...")
            # Create properly structured content for the ADK
            formatted_message = types.Content(
                role="user", parts=[types.Part(text=query)]
            )
            logger.info(f"✅ Message formatted successfully")

            event_count = 0
            async for event in self._runner.run_async(
                user_id=self._user_id,
                session_id=session.id,
                new_message=formatted_message,
            ):
                event_count += 1
                logger.info(f"📨 Received event #{event_count} from LLM runner")
                logger.info(f"🔍 Event type: {type(event).__name__}")
                logger.info(f"✅ Is final response: {event.is_final_response()}")

                if event.is_final_response():
                    # Final response with complete content
                    logger.info(f"🏁 Processing final response event")
                    if event.content and event.content.parts:
                        logger.info(
                            f"📦 Event has content with {len(event.content.parts)} parts"
                        )
                        full_response = ""
                        for i, part in enumerate(event.content.parts):
                            if hasattr(part, "text"):
                                part_text = part.text
                                if part_text is not None:
                                    full_response += part_text
                                    logger.info(
                                        f"📝 Part {i+1}: {len(part_text)} characters"
                                    )
                                else:
                                    logger.warning(
                                        f"⚠️ Part {i+1} has text attribute but value is None"
                                    )
                            else:
                                logger.warning(f"⚠️ Part {i+1} has no text attribute")

                        logger.info(
                            f"✅ Completed response generation for session {session.id}"
                        )
                        logger.info(
                            f"📊 Total response length: {len(full_response)} characters"
                        )
                        logger.info(
                            f"🎯 Final response preview: {full_response[:100]}..."
                        )

                        yield {
                            "is_task_complete": True,
                            "content": full_response,
                            "session_id": session.id,
                        }
                    else:
                        logger.warning(f"⚠️ Final event has no content or parts")
                        fallback_msg = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
                        logger.info(f"🔄 Using fallback response: {fallback_msg}")
                        yield {
                            "is_task_complete": True,
                            "content": fallback_msg,
                            "session_id": session.id,
                        }
                else:
                    # Intermediate streaming update
                    logger.info(f"📝 Processing intermediate streaming event")
                    if hasattr(event, "content") and event.content:
                        logger.info(f"📦 Event has streaming content")
                        partial_content = ""
                        if hasattr(event.content, "parts") and event.content.parts:
                            logger.info(
                                f"📄 Content has {len(event.content.parts)} parts"
                            )
                            for i, part in enumerate(event.content.parts):
                                if hasattr(part, "text"):
                                    part_text = part.text
                                    if part_text is not None:
                                        partial_content += part_text
                                        logger.info(
                                            f"📝 Streaming part {i+1}: {len(part_text)} chars"
                                        )
                                    else:
                                        logger.warning(
                                            f"⚠️ Streaming part {i+1} has text attribute but value is None"
                                        )

                        if partial_content:
                            logger.info(
                                f"📤 Yielding streaming update: {len(partial_content)} characters"
                            )
                            logger.debug(
                                f"🔤 Streaming content: {partial_content[:50]}..."
                            )
                            yield {
                                "is_task_complete": False,
                                "updates": partial_content,
                                "session_id": session.id,
                            }
                        else:
                            logger.warning(f"⚠️ Intermediate event had no text content")
                    else:
                        # Generic processing update
                        logger.info(f"📊 Sending generic processing update")
                        yield {
                            "is_task_complete": False,
                            "updates": "Analyzing nutrition data...",
                            "session_id": session.id,
                        }

            logger.info(
                f"📈 LLM streaming completed - processed {event_count} events total"
            )

        except Exception as e:
            logger.error(
                f"💥 Critical error during LLM streaming: {str(e)}", exc_info=True
            )
            logger.error(f"🔍 Exception type: {type(e).__name__}")
            logger.error(f"🆔 Session ID when error occurred: {session_id}")

            error_response = f"I encountered an error while processing your request: {str(e)}. Please try again or rephrase your question."
            logger.info(f"🚨 Yielding error response: {error_response[:100]}...")

            yield {
                "is_task_complete": True,
                "content": error_response,
                "session_id": session_id,
            }


# Create enhanced agent card for LLM-powered nutrition agent
logger.info("📋 Creating enhanced agent card for LLM-powered nutrition agent...")

agent_card = AgentCard(
    name="AI Nutrition Assistant",
    description="Intelligent nutrition analysis and meal planning assistant powered by advanced AI. Get personalized nutrition insights, meal analysis, and dietary recommendations.",
    version="2.0.0",
    url=os.getenv("HU_APP_URL") or "http://localhost:8003",
    capabilities=AgentCapabilities(
        streaming=True, push_notifications=False, state_transition_history=True
    ),
    skills=[
        AgentSkill(
            id="intelligent_nutrition_analysis",
            name="Intelligent Nutrition Analysis",
            description="AI-powered analysis of foods and meals with personalized insights and recommendations",
            tags=["nutrition", "AI", "health", "analysis", "personalized", "smart"],
            examples=[
                "Analyze the nutrition in my breakfast: scrambled eggs, toast, and orange juice",
                "What are the health benefits of eating salmon twice a week?",
                "I'm trying to lose weight - is this meal good for me?",
                "Calculate the total nutrition for my lunch: chicken salad sandwich and apple",
                "What foods should I eat to get more protein in my diet?",
                "Compare the nutrition between brown rice and quinoa",
                "I'm diabetic - help me plan a low-carb dinner",
                "What are the nutritional differences between grass-fed and regular beef?",
            ],
            input_modes=["application/json", "text/plain"],
            output_modes=["application/json", "text/plain"],
        ),
        AgentSkill(
            id="meal_planning_assistant",
            name="AI Meal Planning",
            description="Intelligent meal planning with dietary restrictions, preferences, and health goals",
            tags=["meal-planning", "dietary-restrictions", "health-goals", "AI"],
            examples=[
                "Help me plan a high-protein meal for post-workout",
                "Suggest a heart-healthy dinner with less than 500 calories",
                "I'm vegetarian and need more iron - what should I eat?",
                "Plan a diabetic-friendly breakfast with good fiber content",
            ],
            input_modes=["application/json", "text/plain"],
            output_modes=["application/json", "text/plain"],
        ),
        AgentSkill(
            id="nutrition_education",
            name="Nutrition Education & Guidance",
            description="Educational content about nutrition science, health recommendations, and dietary guidance",
            tags=["education", "health", "science", "guidance"],
            examples=[
                "Explain the role of antioxidants in my diet",
                "What's the difference between good and bad cholesterol?",
                "How much water should I drink per day?",
                "What are the signs of vitamin D deficiency?",
            ],
            input_modes=["application/json", "text/plain"],
            output_modes=["application/json", "text/plain"],
        ),
    ],
    default_input_modes=["application/json", "text/plain"],
    default_output_modes=["application/json", "text/plain"],
    provider=AgentProvider(
        organization="AI Nutrition Solutions",
        url="https://www.nutritionix.com",
    ),
)

# Create the A2A Starlette application with LLM agent
logger.info("🏗️ Building A2A application components...")

logger.info("🤖 Creating LLM Nutrition Agent Executor...")
agent_executor = LLMNutritionAgentExecutor()
logger.info("✅ Agent executor created successfully")

logger.info("📋 Creating task store (In-Memory)...")
task_store = InMemoryTaskStore()
logger.info("✅ Task store initialized")

logger.info("🔄 Creating default request handler...")
request_handler = DefaultRequestHandler(
    agent_executor=agent_executor,
    task_store=task_store,
)
logger.info("✅ Request handler configured")

logger.info("🌐 Building A2A Starlette application...")
logger.info(f"📋 Agent card: {agent_card.name} v{agent_card.version}")
logger.info(f"🎯 Skills available: {len(agent_card.skills)}")
logger.info(f"🔧 Capabilities: streaming={agent_card.capabilities.streaming}")

app = A2AStarletteApplication(
    agent_card=agent_card, http_handler=request_handler
).build()

logger.info("✅ A2A Starlette application built successfully")
logger.info("🎯 Application ready for deployment")

if __name__ == "__main__":
    logger.info("🚀 Starting LLM-powered AI Nutrition Assistant")
    logger.info("🤖 Enhanced with Google ADK for intelligent responses")
    logger.info("🌐 Server will be available at http://0.0.0.0:8003")
    logger.info(
        "📋 Agent capabilities: streaming, session management, tool integration"
    )

    # Detailed environment setup check
    logger.info("🔍 Performing environment configuration check...")
    google_api_key = os.getenv("GOOGLE_API_KEY")
    nutritionix_api_key = os.getenv("NUTRITIONIX_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")

    logger.info(f"🔑 Environment Variables Status:")
    logger.info(f"   • GOOGLE_API_KEY: {'✅ Set' if google_api_key else '❌ Missing'}")
    logger.info(
        f"   • NUTRITIONIX_API_KEY: {'✅ Set' if nutritionix_api_key else '❌ Missing'}"
    )
    logger.info(f"   • GEMINI_MODEL: {model}")

    if not google_api_key:
        logger.warning(
            "⚠️ GOOGLE_API_KEY not properly configured. Please set your Google API key in .env file."
        )
        logger.warning(
            "⚠️ The agent will use fallback nutrition data until the API key is configured."
        )
        logger.warning("⚠️ LLM features may be limited or non-functional")
    else:
        logger.info("✅ Google API key configured - Full LLM features enabled")
        logger.info(f"🎯 Agent will use {model} for intelligent responses")

    if not nutritionix_api_key:
        logger.warning(
            "⚠️ NUTRITIONIX_API_KEY not configured - will use mock nutrition data"
        )
    else:
        logger.info("✅ Nutritionix API key configured - Real nutrition data available")

    logger.info("🏗️ Application components initialized:")
    logger.info("   • LLM Agent Executor: Ready")
    logger.info("   • Request Handler: Ready")
    logger.info("   • A2A Starlette Application: Ready")
    logger.info("   • Task Store: In-Memory")

    logger.info("🎯 Agent Skills Available:")
    for skill in agent_card.skills:
        logger.info(f"   • {skill.name}: {skill.description}")

    logger.info("🔧 Starting Uvicorn server...")
    logger.info("📡 Ready to accept nutrition queries!")

    uvicorn.run(app, host="0.0.0.0", port=8003)