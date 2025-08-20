"""
A2A-compliant base class for agents (spec v0.3.0).
- Minimal but production-friendly: consistent contextId handling, clean logging,
  overridable cancellation hook, and explicit task lifecycle updates.
- The A2A framework handles LLM/tool orchestration; subclasses implement business logic.
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
    DataPart,
    TaskState,
    Task,
    TaskStatus,
    Message,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError, InvalidParamsError

# ---- sane logging config (avoid duplicate handlers across multiple agents) ----
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

logger = logging.getLogger(__name__)


class A2AAgent(AgentExecutor, ABC):
    """
    Subclass authors must implement:
      - get_agent_name()
      - get_agent_description()
      - process_message(message: str) -> str

    May override for customization:
      - get_tools(), get_system_instruction(), get_agent_skills()
      - supports_streaming(), supports_push_notifications()
      - on_cancel(task_id: str)
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._current_task_id: Optional[str] = None

    # ------------------------------- AgentCard ------------------------------- #
    def create_agent_card(self) -> AgentCard:
        """Create AgentCard for discovery (reads HU_APP_URL/A2A_BASE_URL at runtime)."""
        base_url = os.getenv("HU_APP_URL", os.getenv("A2A_BASE_URL", "https://your-agent.example.com/a2a/v1"))
        provider_org = os.getenv("A2A_PROVIDER_ORG", "A2A Template")
        provider_url = os.getenv("A2A_PROVIDER_URL", "https://github.com/jmjlacosta/a2a-template")

        return AgentCard(
            protocolVersion="0.3.0",
            name=self.get_agent_name(),
            description=self.get_agent_description(),
            version=self.get_agent_version(),
            url=base_url,
            preferredTransport="JSONRPC",
            additionalInterfaces=[{"url": base_url, "transport": "JSONRPC"}],
            provider=AgentProvider(organization=provider_org, url=provider_url),
            capabilities=AgentCapabilities(
                streaming=self.supports_streaming(),
                pushNotifications=self.supports_push_notifications(),
            ),
            skills=self.get_agent_skills(),
            securitySchemes={},  # e.g., {"apiKey":{"type":"apiKey","in":"header","name":"Authorization"}}
            security=[],
            defaultInputModes=["text/plain", "application/json"],
            defaultOutputModes=["text/plain", "application/json"],
        )

    # ------------------------------- Execution ------------------------------- #
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Minimal A2A execution:
        - normalize/create Task
        - set working
        - run business logic
        - emit final agent message (as an event)
        - mark completed with a status update (response also readable via the message event)
        """
        task: Optional[Task] = None
        try:
            message = self._extract_message(context)
            if not message:
                raise InvalidParamsError("No message provided in request")

            # Ensure we have a Task (server may provide one; otherwise create)
            task = getattr(context, "current_task", None)
            if not task:
                task = new_task(context.message or new_agent_text_message("Processing..."))
                await event_queue.enqueue_event(task)

            self._current_task_id = task.id
            context_id = self._normalize_context_id(task, context)
            updater = TaskUpdater(event_queue, task.id, context_id)

            # Working
            await updater.update_status(TaskState.working, new_agent_text_message("Processing your request..."))

            if os.getenv("SHOW_AGENT_CALLS", "false").lower() == "true":
                self.logger.info(f"📨 {self.get_agent_name()}: Processing message ({len(message)} chars)")

            # Business logic
            response = await self.process_message(message)

            # Emit the final agent message as a separate event (easy for UIs to render)
            await event_queue.enqueue_event(new_agent_text_message(response))

            # Completed (status message concise; response is in the prior event)
            await updater.update_status(TaskState.completed, new_agent_text_message("Task completed successfully"))

        except ServerError as e:
            if task:
                context_id = self._normalize_context_id(task, context)
                updater = TaskUpdater(event_queue, task.id, context_id)
                await updater.update_status(TaskState.failed, new_agent_text_message(f"Task failed: {e}"))
            raise
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            if task:
                context_id = self._normalize_context_id(task, context)
                updater = TaskUpdater(event_queue, task.id, context_id)
                await updater.update_status(TaskState.failed, new_agent_text_message(f"Task failed: {e}"))
            raise ServerError(error=e)

    # ------------------------------- Cancel ---------------------------------- #
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        tasks/cancel: try to stop work, emit a canceled Task and a status update.
        Subclasses can override `on_cancel()` for runtime-specific cleanup.
        """
        # Resolve taskId
        task_id = None
        if getattr(context, "current_task", None):
            task_id = context.current_task.id
        elif hasattr(context, "task_id"):
            task_id = context.task_id
        elif getattr(context, "metadata", None) and "task_id" in context.metadata:
            task_id = context.metadata["task_id"]
        elif self._current_task_id:
            task_id = self._current_task_id

        if not task_id:
            raise ServerError(error=InvalidParamsError("No task ID provided for cancellation"))

        ctx_id = getattr(context, "contextId", getattr(context, "context_id", task_id))
        updater = TaskUpdater(event_queue, task_id, ctx_id)

        try:
            await self.on_cancel(task_id)

            # Status: canceled
            await updater.update_status(TaskState.canceled, new_agent_text_message(f"Task {task_id} has been canceled"))

            # Return a Task object in canceled state
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
                        kind="message",
                    ),
                ),
                kind="task",
            )
            await event_queue.enqueue_event(canceled_task)
            self.logger.info(f"Task {task_id} canceled successfully")

        except Exception as e:
            self.logger.error(f"Error canceling task {task_id}: {e}")
            failed_task = Task(
                id=task_id,
                contextId=ctx_id,
                status=TaskStatus(
                    state=TaskState.failed,
                    message=Message(
                        role="agent",
                        parts=[TextPart(kind="text", text=f"Cancellation failed: {e}")],
                        messageId=f"cancel-failed-{task_id}",
                        taskId=task_id,
                        contextId=ctx_id,
                        kind="message",
                    ),
                ),
                kind="task",
            )
            await event_queue.enqueue_event(failed_task)
            raise ServerError(error=e)

    async def on_cancel(self, task_id: str) -> None:
        """Hook for subclasses to stop long-running jobs, close sockets, etc."""
        return

    # ---------------------------- Message extraction ------------------------- #
    def _extract_message(self, context: RequestContext) -> Optional[str]:
        """
        Spec-compliant Part parsing (discriminated union by 'kind': 'text'|'data'|'file').
        Returns a single string for simple agents; subclasses can override to keep structure.
        """
        msg = getattr(context, "message", None)
        parts = getattr(msg, "parts", None)
        if not msg or not parts:
            return None

        extracted: List[str] = []

        for part in parts:
            # Support both dict-like and object-like
            kind = part.get("kind") if isinstance(part, dict) else getattr(part, "kind", None)

            if kind == "text":
                text = part.get("text") if isinstance(part, dict) else getattr(part, "text", None)
                if text is not None:
                    extracted.append(str(text))

            elif kind == "data":
                data = part.get("data") if isinstance(part, dict) else getattr(part, "data", None)
                if data is not None:
                    extracted.append(json.dumps(data) if isinstance(data, (dict, list)) else str(data))

            elif kind == "file":
                file_obj = part.get("file") if isinstance(part, dict) else getattr(part, "file", None)
                if file_obj:
                    # dict-ish
                    if isinstance(file_obj, dict):
                        name = file_obj.get("name", "unnamed")
                        if "uri" in file_obj:
                            extracted.append(f"[file:{name}] {file_obj['uri']}")
                        elif "bytes" in file_obj:
                            extracted.append(f"[file-bytes:{name}] (binary data)")
                    else:
                        # object-ish
                        name = getattr(file_obj, "name", "unnamed")
                        if getattr(file_obj, "uri", None):
                            extracted.append(f"[file:{name}] {file_obj.uri}")
                        elif getattr(file_obj, "bytes", None) is not None:
                            extracted.append(f"[file-bytes:{name}] (binary data)")

            else:
                # Legacy fallbacks; warn once per part
                handled = False
                if hasattr(part, "root"):
                    if isinstance(part.root, TextPart):
                        extracted.append(part.root.text)
                        handled = True
                    elif isinstance(part.root, DataPart):
                        data = part.root.data
                        extracted.append(json.dumps(data) if isinstance(data, (dict, list)) else str(data))
                        handled = True
                elif hasattr(part, "text"):
                    extracted.append(str(part.text))
                    handled = True
                elif hasattr(part, "data"):
                    data = part.data
                    extracted.append(json.dumps(data) if isinstance(data, (dict, list)) else str(data))
                    handled = True

                if handled:
                    self.logger.warning("Handled legacy part format without 'kind' field")

        return "\n".join(extracted) if extracted else None

    # --------------------------- Abstract / Optional ------------------------- #
    @abstractmethod
    def get_agent_name(self) -> str: ...

    @abstractmethod
    def get_agent_description(self) -> str: ...

    @abstractmethod
    async def process_message(self, message: str) -> str: ...

    def get_agent_version(self) -> str:
        return "1.0.0"

    def get_system_instruction(self) -> str:
        return "You are a helpful AI assistant."

    def get_tools(self) -> List:
        return []

    def get_agent_skills(self) -> List[AgentSkill]:
        return []

    def supports_streaming(self) -> bool:
        return False

    def supports_push_notifications(self) -> bool:
        return False

    # ------------------------------- Utilities ------------------------------- #
    def _normalize_context_id(self, task: Task, context: RequestContext) -> str:
        """Prefer spec's camelCase contextId when present; fall back sensibly."""
        return (
            getattr(task, "contextId", None)
            or getattr(task, "context_id", None)
            or getattr(context, "contextId", None)
            or getattr(context, "context_id", None)
            or task.id
        )

    async def call_other_agent(self, agent_name_or_url: str, message: str, timeout: float = 30.0) -> str:
        """Utility for inter-agent calls using A2A; supports name→URL via config/agents.json."""
        from utils.a2a_client import A2AAgentClient

        agent_url = agent_name_or_url
        if not agent_name_or_url.startswith(("http://", "https://")):
            try:
                with open("config/agents.json", "r") as f:
                    config = json.load(f)
                agents = config.get("agents", {})
                if agent_name_or_url in agents:
                    agent_url = agents[agent_name_or_url]["url"]
                else:
                    raise ValueError(f"Agent '{agent_name_or_url}' not found in config")
            except FileNotFoundError:
                raise ValueError(f"Config file not found and '{agent_name_or_url}' is not a URL")

        self.logger.info(f"Calling agent at {agent_url}")
        async with A2AAgentClient() as client:
            return await client.call_agent(agent_url, message, timeout=timeout)