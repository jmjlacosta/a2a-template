"""
Server-Sent Events (SSE) client for A2A streaming.
Parses SSE streams per W3C specification for A2A protocol compliance.
"""

import json
import logging
from typing import AsyncIterator, Dict, Any, Optional

logger = logging.getLogger(__name__)


class SSEClient:
    """
    Parse Server-Sent Events for A2A streaming.
    
    Implements W3C SSE specification for parsing event streams
    from A2A servers using message/stream method.
    """
    
    def __init__(self):
        """Initialize SSE client."""
        self.logger = logger
    
    async def parse_stream(self, response) -> AsyncIterator[Dict[str, Any]]:
        """
        Parse SSE stream from aiohttp response.
        
        Yields parsed JSON-RPC responses from data fields.
        
        Args:
            response: aiohttp ClientResponse with SSE stream
            
        Yields:
            Parsed JSON objects from SSE data fields
        """
        buffer = ""
        
        try:
            # Read chunks from response stream
            async for chunk in response.content.iter_any():
                # Decode chunk and add to buffer
                if isinstance(chunk, bytes):
                    chunk = chunk.decode('utf-8', errors='ignore')
                buffer += chunk
                
                # Process complete events (separated by double newline)
                while '\n\n' in buffer:
                    event_text, buffer = buffer.split('\n\n', 1)
                    
                    # Parse event and yield if valid
                    event_data = self._parse_event(event_text)
                    if event_data:
                        yield event_data
            
            # Process any remaining data in buffer
            if buffer.strip():
                event_data = self._parse_event(buffer)
                if event_data:
                    yield event_data
                    
        except Exception as e:
            self.logger.error(f"Error parsing SSE stream: {e}")
            raise
    
    def _parse_event(self, event_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single SSE event.
        
        Args:
            event_text: Raw SSE event text
            
        Returns:
            Parsed JSON data from event, or None if invalid
        """
        if not event_text.strip():
            return None
        
        event_type = None
        event_data = None
        event_id = None
        retry = None
        
        # Parse SSE fields line by line
        for line in event_text.split('\n'):
            if not line:
                continue
                
            if line.startswith('event:'):
                # Event type field
                event_type = line[6:].strip()
            elif line.startswith('data:'):
                # Data field - this is what we care about for A2A
                data_str = line[5:].strip()
                if data_str:
                    try:
                        # Parse JSON from data field
                        event_data = json.loads(data_str)
                    except json.JSONDecodeError as e:
                        self.logger.debug(f"Failed to parse JSON from SSE data: {e}")
                        # Some SSE streams may have non-JSON data
                        event_data = {"raw": data_str}
            elif line.startswith('id:'):
                # Event ID field
                event_id = line[3:].strip()
            elif line.startswith('retry:'):
                # Retry field (reconnection time in ms)
                retry_str = line[6:].strip()
                try:
                    retry = int(retry_str)
                except ValueError:
                    pass
            elif line.startswith(':'):
                # Comment line - ignore
                continue
        
        # Return parsed data if we got any
        if event_data:
            # Add metadata if present
            if event_type:
                event_data['_sse_event_type'] = event_type
            if event_id:
                event_data['_sse_event_id'] = event_id
            if retry is not None:
                event_data['_sse_retry'] = retry
            
            return event_data
        
        return None


class SSEParser:
    """
    Alternative SSE parser for line-by-line processing.
    Useful for manual stream parsing.
    """
    
    def __init__(self):
        """Initialize parser state."""
        self.buffer = ""
        self.events = []
    
    def feed(self, data: str) -> list:
        """
        Feed data to parser and get complete events.
        
        Args:
            data: New data to parse
            
        Returns:
            List of complete parsed events
        """
        self.buffer += data
        complete_events = []
        
        # Extract complete events from buffer
        while '\n\n' in self.buffer:
            event_text, self.buffer = self.buffer.split('\n\n', 1)
            event = self._parse_event(event_text)
            if event:
                complete_events.append(event)
        
        return complete_events
    
    def _parse_event(self, event_text: str) -> Optional[Dict[str, Any]]:
        """Parse single event (same as SSEClient._parse_event)."""
        client = SSEClient()
        return client._parse_event(event_text)