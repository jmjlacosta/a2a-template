"""
Session management utilities for A2A agents.

Handles conversation sessions, context management, and history tracking.
"""

import uuid
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Represents a message in a conversation."""
    role: str  # "user", "agent", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    

@dataclass
class SessionContext:
    """Context for a conversation session."""
    session_id: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    task_id: Optional[str] = None
    parent_session_id: Optional[str] = None
    

class SessionManager:
    """Manages conversation sessions for agents."""
    
    def __init__(
        self,
        max_sessions: int = 100,
        max_messages_per_session: int = 1000,
        session_timeout: timedelta = timedelta(hours=1)
    ):
        self.sessions: Dict[str, SessionContext] = {}
        self.max_sessions = max_sessions
        self.max_messages_per_session = max_messages_per_session
        self.session_timeout = session_timeout
        self.logger = logging.getLogger(f"{__name__}.SessionManager")
        self._cleanup_task = None
        
    async def start(self):
        """Start the session manager."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.logger.info("🚀 Session manager started")
        
    async def stop(self):
        """Stop the session manager."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        self.logger.info("🛑 Session manager stopped")
        
    async def _cleanup_loop(self):
        """Periodically clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self.cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                
    async def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        now = datetime.utcnow()
        expired = []
        
        for session_id, session in self.sessions.items():
            if now - session.updated_at > self.session_timeout:
                expired.append(session_id)
                
        for session_id in expired:
            await self.end_session(session_id)
            self.logger.info(f"🗑️ Cleaned up expired session: {session_id}")
            
    def create_session(
        self,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        parent_session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionContext:
        """
        Create a new conversation session.
        
        Args:
            session_id: Optional session ID (generates if not provided)
            task_id: Associated task ID
            parent_session_id: Parent session for nested conversations
            metadata: Session metadata
            
        Returns:
            New session context
        """
        if len(self.sessions) >= self.max_sessions:
            self._evict_oldest_session()
            
        session_id = session_id or str(uuid.uuid4())
        now = datetime.utcnow()
        
        session = SessionContext(
            session_id=session_id,
            created_at=now,
            updated_at=now,
            task_id=task_id,
            parent_session_id=parent_session_id,
            metadata=metadata or {}
        )
        
        self.sessions[session_id] = session
        self.logger.info(f"📝 Created session: {session_id}")
        
        return session
        
    def _evict_oldest_session(self):
        """Evict the oldest session when at capacity."""
        if not self.sessions:
            return
            
        oldest_id = min(
            self.sessions.keys(),
            key=lambda k: self.sessions[k].updated_at
        )
        
        del self.sessions[oldest_id]
        self.logger.info(f"🗑️ Evicted oldest session: {oldest_id}")
        
    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Get a session by ID."""
        session = self.sessions.get(session_id)
        if session:
            session.updated_at = datetime.utcnow()
        return session
        
    async def end_session(self, session_id: str) -> bool:
        """
        End a session and clean up resources.
        
        Args:
            session_id: Session to end
            
        Returns:
            True if session was ended
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            
            if session.parent_session_id:
                await self._merge_to_parent(session)
                
            del self.sessions[session_id]
            self.logger.info(f"🏁 Ended session: {session_id}")
            return True
            
        return False
        
    async def _merge_to_parent(self, session: SessionContext):
        """Merge child session context to parent."""
        parent = self.sessions.get(session.parent_session_id)
        if parent:
            parent.variables.update(session.variables)
            parent.metadata.update({
                f"child_{session.session_id}": {
                    "messages": len(session.messages),
                    "variables": session.variables,
                    "ended_at": datetime.utcnow().isoformat()
                }
            })
            
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """
        Add a message to a session.
        
        Args:
            session_id: Session ID
            role: Message role (user/agent/system)
            content: Message content
            metadata: Optional message metadata
            
        Returns:
            The created message or None if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return None
            
        if len(session.messages) >= self.max_messages_per_session:
            self._truncate_messages(session)
            
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        session.messages.append(message)
        session.updated_at = datetime.utcnow()
        
        self.logger.debug(f"💬 Added {role} message to session {session_id}")
        
        return message
        
    def _truncate_messages(self, session: SessionContext):
        """Truncate old messages when at capacity."""
        keep_count = self.max_messages_per_session // 2
        session.messages = session.messages[-keep_count:]
        
        session.metadata["truncated"] = True
        session.metadata["truncated_at"] = datetime.utcnow().isoformat()
        
        self.logger.info(f"✂️ Truncated messages in session {session.session_id}")
        
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        role: Optional[str] = None
    ) -> List[Message]:
        """
        Get messages from a session.
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to return
            role: Filter by role
            
        Returns:
            List of messages
        """
        session = self.get_session(session_id)
        if not session:
            return []
            
        messages = session.messages
        
        if role:
            messages = [m for m in messages if m.role == role]
            
        if limit:
            messages = messages[-limit:]
            
        return messages
        
    def get_context(
        self,
        session_id: str,
        max_tokens: int = 4000
    ) -> str:
        """
        Get conversation context for LLM.
        
        Args:
            session_id: Session ID
            max_tokens: Maximum context size in tokens (approximate)
            
        Returns:
            Formatted context string
        """
        session = self.get_session(session_id)
        if not session:
            return ""
            
        context_parts = []
        token_count = 0
        
        for message in reversed(session.messages):
            message_str = f"{message.role}: {message.content}"
            message_tokens = len(message_str.split()) * 1.3
            
            if token_count + message_tokens > max_tokens:
                break
                
            context_parts.insert(0, message_str)
            token_count += message_tokens
            
        return "\n".join(context_parts)
        
    def set_variable(
        self,
        session_id: str,
        key: str,
        value: Any
    ) -> bool:
        """
        Set a session variable.
        
        Args:
            session_id: Session ID
            key: Variable key
            value: Variable value
            
        Returns:
            True if variable was set
        """
        session = self.get_session(session_id)
        if session:
            session.variables[key] = value
            session.updated_at = datetime.utcnow()
            return True
        return False
        
    def get_variable(
        self,
        session_id: str,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Get a session variable.
        
        Args:
            session_id: Session ID
            key: Variable key
            default: Default value if not found
            
        Returns:
            Variable value or default
        """
        session = self.get_session(session_id)
        if session:
            return session.variables.get(key, default)
        return default
        
    def export_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Export session data for persistence.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data as dictionary
        """
        session = self.get_session(session_id)
        if not session:
            return None
            
        return {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "task_id": session.task_id,
            "parent_session_id": session.parent_session_id,
            "metadata": session.metadata,
            "variables": session.variables,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": m.metadata,
                    "message_id": m.message_id
                }
                for m in session.messages
            ]
        }
        
    def import_session(self, session_data: Dict[str, Any]) -> SessionContext:
        """
        Import session data from persistence.
        
        Args:
            session_data: Session data dictionary
            
        Returns:
            Imported session context
        """
        session = SessionContext(
            session_id=session_data["session_id"],
            created_at=datetime.fromisoformat(session_data["created_at"]),
            updated_at=datetime.fromisoformat(session_data["updated_at"]),
            task_id=session_data.get("task_id"),
            parent_session_id=session_data.get("parent_session_id"),
            metadata=session_data.get("metadata", {}),
            variables=session_data.get("variables", {})
        )
        
        for msg_data in session_data.get("messages", []):
            message = Message(
                role=msg_data["role"],
                content=msg_data["content"],
                timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                metadata=msg_data.get("metadata", {}),
                message_id=msg_data.get("message_id", str(uuid.uuid4()))
            )
            session.messages.append(message)
            
        self.sessions[session.session_id] = session
        self.logger.info(f"📥 Imported session: {session.session_id}")
        
        return session


class ConversationBuffer:
    """Buffer for managing conversation history with sliding window."""
    
    def __init__(self, max_size: int = 10):
        self.buffer: deque = deque(maxlen=max_size)
        self.max_size = max_size
        
    def add(self, role: str, content: str):
        """Add a message to the buffer."""
        self.buffer.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    def get_context(self) -> List[Dict[str, str]]:
        """Get conversation context for LLM."""
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.buffer
        ]
        
    def clear(self):
        """Clear the buffer."""
        self.buffer.clear()
        
    def to_string(self) -> str:
        """Convert buffer to string format."""
        return "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in self.buffer
        ])