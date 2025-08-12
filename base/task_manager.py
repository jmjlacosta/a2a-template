"""
Task State Machine Manager for A2A Protocol.
Handles complete task lifecycle with proper state transitions, validation, and events.
"""

import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from a2a.types import Task, TaskState, Message
from a2a.server.tasks import TaskUpdater
from a2a.server.events import EventQueue
from a2a.utils import new_task, new_agent_text_message

logger = logging.getLogger(__name__)


# Valid state transitions according to A2A protocol v0.3.0
VALID_TRANSITIONS: Dict[str, List[str]] = {
    "submitted": ["working", "rejected", "canceled"],
    "working": ["input_required", "completed", "failed", "canceled"],
    "input_required": ["working", "canceled"],
    "completed": [],  # Terminal state
    "canceled": [],   # Terminal state  
    "failed": [],     # Terminal state
    "rejected": [],   # Terminal state
    "auth_required": ["working", "canceled"],
    "unknown": ["working", "failed"]
}


class TaskStateError(Exception):
    """Raised when invalid state transition is attempted."""
    pass


class TaskManager:
    """
    Manages task state machine with full A2A protocol compliance.
    Handles state transitions, validation, history, and events.
    """
    
    def __init__(self, task: Task, event_queue: EventQueue):
        """
        Initialize task manager.
        
        Args:
            task: The A2A task to manage
            event_queue: Event queue for emitting state changes
        """
        self.task = task
        self.task_id = task.id
        self.context_id = task.context_id
        self.event_queue = event_queue
        
        # Initialize with current task state
        self.state = self._get_current_state()
        
        # Task lifecycle tracking
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.state_history: List[Dict[str, Any]] = []
        
        # Task updater for sending updates
        self.updater = TaskUpdater(event_queue, task.id, task.context_id)
        
        # Heartbeat management
        self._heartbeat_task = None
        self._heartbeat_interval = 10.0  # seconds
        
        logger.info(f"📋 TaskManager initialized for task {self.task_id} in state: {self.state}")
    
    def _get_current_state(self) -> str:
        """Get current state from task."""
        if hasattr(self.task, 'state'):
            return self.task.state
        return "submitted"
    
    async def transition_to(self, new_state: str, message: Optional[str] = None) -> bool:
        """
        Transition to a new state with validation.
        
        Args:
            new_state: Target state (must be valid TaskState value)
            message: Optional message describing the transition
            
        Returns:
            True if transition successful
            
        Raises:
            TaskStateError: If transition is invalid
        """
        # Validate new state - A2A spec uses specific state names
        # Convert underscore to proper format if needed
        valid_states = ["submitted", "working", "input_required", "completed", 
                       "canceled", "failed", "rejected", "auth_required", "unknown"]
        
        if new_state not in valid_states:
            raise TaskStateError(f"Invalid state: {new_state}. Must be one of {valid_states}")
        
        # Check if transition is valid
        if not self._is_valid_transition(new_state):
            error_msg = f"Invalid transition: {self.state} -> {new_state}"
            logger.error(f"❌ {error_msg}")
            raise TaskStateError(error_msg)
        
        old_state = self.state
        self.state = new_state
        self.updated_at = datetime.utcnow()
        
        # Add to history
        self.state_history.append({
            "from": old_state,
            "to": new_state,
            "timestamp": self.updated_at.isoformat(),
            "message": message
        })
        
        logger.info(f"✅ Task {self.task_id}: {old_state} -> {new_state}")
        if message:
            logger.info(f"   Message: {message}")
        
        # Update task state using appropriate method
        await self._update_task_state(new_state, message)
        
        # Stop heartbeat if terminal state
        if self._is_terminal_state(new_state):
            await self.stop_heartbeat()
        
        return True
    
    def _is_valid_transition(self, new_state: str) -> bool:
        """Check if transition is valid according to A2A protocol."""
        current = self.state
        return new_state in VALID_TRANSITIONS.get(current, [])
    
    def _is_terminal_state(self, state: str) -> bool:
        """Check if state is terminal (no further transitions allowed)."""
        return state in ["completed", "canceled", "failed", "rejected"]
    
    async def _update_task_state(self, state: str, message: Optional[str] = None):
        """Update task state through TaskUpdater."""
        try:
            if state == "working":
                # Start working on the task
                await self.updater.start_work()
                if message:
                    await self.updater.new_agent_message(message)
            elif state == "completed":
                await self.updater.complete(message)
            elif state == "failed":
                await self.updater.failed(message or "Task failed")
            elif state == "canceled":
                await self.updater.cancel(message or "Task cancelled")
            elif state == "input_required":
                # Request input from user
                await self.updater.requires_input(
                    message or "Additional input required to continue"
                )
            elif state == "rejected":
                # Agent cannot handle this task
                await self.updater.reject(message or "Cannot process this request")
            elif state == "auth_required":
                # Authentication needed
                await self.updater.requires_auth(
                    message or "Authentication required to continue"
                )
            
            # Note: Task objects from A2A SDK are immutable, state is managed internally
            
        except Exception as e:
            logger.error(f"❌ Error updating task state: {e}")
            raise
    
    async def start_working(self, initial_message: Optional[str] = None):
        """
        Convenience method to transition from submitted to working.
        Starts heartbeat for long-running tasks.
        """
        if self.state == "submitted":
            await self.transition_to("working", initial_message or "Processing task...")
            await self.start_heartbeat()
    
    async def complete_task(self, result: Optional[str] = None):
        """Convenience method to mark task as completed."""
        if self.state in ["working", "input_required"]:
            await self.transition_to("completed", result or "Task completed successfully")
    
    async def fail_task(self, error: str):
        """Convenience method to mark task as failed."""
        if not self._is_terminal_state(self.state):
            await self.transition_to("failed", error)
    
    async def cancel_task(self, reason: Optional[str] = None):
        """Convenience method to cancel task."""
        if not self._is_terminal_state(self.state):
            await self.transition_to("canceled", reason or "Task cancelled by user")
    
    async def request_input(self, prompt: str):
        """Request additional input from user."""
        if self.state == "working":
            await self.transition_to("input_required", prompt)
    
    async def reject_task(self, reason: str):
        """Reject task that agent cannot handle."""
        if self.state == "submitted":
            await self.transition_to("rejected", reason)
    
    async def require_auth(self, message: str):
        """Indicate authentication is required."""
        if self.state in ["submitted", "working"]:
            await self.transition_to("auth_required", message)
    
    # Heartbeat Management
    
    async def start_heartbeat(self):
        """Start sending periodic heartbeats for long-running tasks."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info(f"💓 Started heartbeat for task {self.task_id}")
    
    async def stop_heartbeat(self):
        """Stop sending heartbeats."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info(f"🛑 Stopped heartbeat for task {self.task_id}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats while task is running."""
        try:
            while self.state == "working":
                await asyncio.sleep(self._heartbeat_interval)
                if self.state == "working":
                    # Send status update as heartbeat
                    await self.updater.update_status("Still processing...")
                    logger.debug(f"💓 Heartbeat sent for task {self.task_id}")
        except asyncio.CancelledError:
            logger.debug(f"Heartbeat loop cancelled for task {self.task_id}")
            raise
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")
    
    def set_heartbeat_interval(self, interval: float):
        """Set heartbeat interval in seconds."""
        self._heartbeat_interval = interval
    
    # Context Management
    
    def get_or_create_context_id(self) -> str:
        """Get existing context ID or create new one for conversation continuity."""
        if self.context_id:
            # Check if existing context ID has correct format
            if not self.context_id.startswith("ctx_"):
                # Preserve existing but mark it properly
                return self.context_id
            return self.context_id
        
        # Generate new context ID
        self.context_id = f"ctx_{uuid.uuid4().hex[:8]}"
        # Note: Task objects are immutable, can't update context_id
        logger.info(f"🔗 Created new context ID: {self.context_id}")
        return self.context_id
    
    # State Recovery
    
    async def recover_interrupted_task(self):
        """
        Recover task that was interrupted (e.g., by agent restart).
        Called on startup to handle tasks left in working state.
        """
        if self.state == "working":
            logger.warning(f"⚠️ Recovering interrupted task {self.task_id}")
            await self.fail_task("Task interrupted by agent restart")
            return True
        return False
    
    # State Inspection
    
    def is_terminal(self) -> bool:
        """Check if task is in terminal state."""
        return self._is_terminal_state(self.state)
    
    def is_active(self) -> bool:
        """Check if task is actively being processed."""
        return self.state in ["working", "input_required", "auth_required"]
    
    def can_cancel(self) -> bool:
        """Check if task can be cancelled."""
        return not self.is_terminal()
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get comprehensive state information."""
        return {
            "task_id": self.task_id,
            "context_id": self.context_id,
            "current_state": self.state,
            "is_terminal": self.is_terminal(),
            "is_active": self.is_active(),
            "can_cancel": self.can_cancel(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "state_history": self.state_history,
            "history_count": len(self.state_history)
        }


class TaskHeartbeat:
    """
    Standalone heartbeat manager for multiple tasks.
    Can be used to manage heartbeats across multiple TaskManager instances.
    """
    
    def __init__(self, interval: float = 10.0):
        """
        Initialize heartbeat manager.
        
        Args:
            interval: Heartbeat interval in seconds
        """
        self.interval = interval
        self.tasks: Dict[str, TaskManager] = {}
        self._heartbeat_task = None
        self.running = False
    
    def add_task(self, task_manager: TaskManager):
        """Add task to heartbeat monitoring."""
        self.tasks[task_manager.task_id] = task_manager
        logger.info(f"Added task {task_manager.task_id} to heartbeat monitor")
    
    def remove_task(self, task_id: str):
        """Remove task from heartbeat monitoring."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"Removed task {task_id} from heartbeat monitor")
    
    async def start(self):
        """Start heartbeat monitoring."""
        if not self.running:
            self.running = True
            self._heartbeat_task = asyncio.create_task(self._monitor_loop())
            logger.info("🚀 Started global heartbeat monitor")
    
    async def stop(self):
        """Stop heartbeat monitoring."""
        self.running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Stopped global heartbeat monitor")
    
    async def _monitor_loop(self):
        """Monitor all tasks and send heartbeats."""
        try:
            while self.running:
                await asyncio.sleep(self.interval)
                
                # Send heartbeats for all active tasks
                for task_id, task_manager in list(self.tasks.items()):
                    if task_manager.state == "working":
                        try:
                            await task_manager.updater.update_status("Still processing...")
                            logger.debug(f"💓 Heartbeat sent for task {task_id}")
                        except Exception as e:
                            logger.error(f"Error sending heartbeat for {task_id}: {e}")
                    elif task_manager.is_terminal():
                        # Remove completed tasks
                        self.remove_task(task_id)
                        
        except asyncio.CancelledError:
            logger.debug("Heartbeat monitor loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in heartbeat monitor: {e}")


def create_task_manager(
    task: Optional[Task],
    event_queue: EventQueue,
    message: Optional[Message] = None
) -> TaskManager:
    """
    Factory function to create TaskManager with proper initialization.
    
    Args:
        task: Existing task or None to create new
        event_queue: Event queue for updates
        message: Initial message if creating new task
        
    Returns:
        Initialized TaskManager
    """
    if not task:
        # Create new task
        if not message:
            message = new_agent_text_message("Processing request...")
        task = new_task(message)
        logger.info(f"✨ Created new task: {task.id}")
    
    return TaskManager(task, event_queue)