"""
JSON-based messaging utilities for A2A agent communication.
Provides structured message formatting following A2A v0.3.0 specification.
"""

import json
import uuid
from typing import Dict, Any, List, Optional, Union
from a2a.types import Message, Part, TextPart, DataPart


def create_json_message(
    data: Union[Dict[str, Any], str],
    message_id: Optional[str] = None,
    task_id: Optional[str] = None,
    context_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Message:
    """
    Create an A2A-compliant message with JSON data.
    
    Uses DataPart for structured data as recommended by A2A spec section 6.5.3.
    
    Args:
        data: Either a dictionary (sent as DataPart) or string (sent as TextPart)
        message_id: Optional message ID (auto-generated if not provided)
        task_id: Optional task ID for continuing conversations
        context_id: Optional context ID for grouping related messages
        metadata: Optional metadata dictionary
        
    Returns:
        A2A Message object with proper structure
    """
    if message_id is None:
        message_id = str(uuid.uuid4())
    
    # Create appropriate part based on data type
    parts: List[Part] = []
    
    if isinstance(data, dict):
        # Use DataPart for structured data (A2A spec 6.5.3)
        parts.append(Part(root=DataPart(
            kind="data",
            data=data
        )))
    elif isinstance(data, str):
        # Check if string is JSON
        try:
            json_data = json.loads(data)
            # It's JSON, use DataPart
            parts.append(Part(root=DataPart(
                kind="data",
                data=json_data
            )))
        except json.JSONDecodeError:
            # It's plain text, use TextPart
            parts.append(Part(root=TextPart(
                kind="text",
                text=data
            )))
    else:
        # Convert to JSON string for other types
        parts.append(Part(root=DataPart(
            kind="data",
            data={"value": str(data)}
        )))
    
    # Create message following A2A spec section 6.4
    message = Message(
        messageId=message_id,
        role="user",
        parts=parts,
        kind="message"
    )
    
    # Add optional fields if provided
    if task_id:
        message.taskId = task_id
    if context_id:
        message.contextId = context_id
    if metadata:
        message.metadata = metadata
    
    return message


def extract_json_from_message(message: Message) -> Union[Dict[str, Any], str, None]:
    """
    Extract JSON data from an A2A message.
    
    Handles both DataPart (structured) and TextPart (may contain JSON string).
    
    Args:
        message: A2A Message object
        
    Returns:
        Extracted data (dict if JSON, string if text, None if no content)
    """
    if not message or not message.parts:
        return None
    
    # Process all parts and combine results
    extracted_data = []
    
    for part in message.parts:
        if hasattr(part, 'root'):
            part_root = part.root
        else:
            part_root = part
            
        # Check part type
        if hasattr(part_root, 'kind'):
            if part_root.kind == "data" and hasattr(part_root, 'data'):
                # DataPart with structured data
                extracted_data.append(part_root.data)
            elif part_root.kind == "text" and hasattr(part_root, 'text'):
                # TextPart - check if it contains JSON
                text = part_root.text
                try:
                    json_data = json.loads(text)
                    extracted_data.append(json_data)
                except json.JSONDecodeError:
                    # Plain text
                    extracted_data.append(text)
    
    # Return based on what we found
    if len(extracted_data) == 0:
        return None
    elif len(extracted_data) == 1:
        return extracted_data[0]
    else:
        # Multiple parts - combine appropriately
        if all(isinstance(d, dict) for d in extracted_data):
            # All dicts - merge them
            merged = {}
            for d in extracted_data:
                merged.update(d)
            return merged
        elif all(isinstance(d, str) for d in extracted_data):
            # All strings - concatenate
            return "\n".join(extracted_data)
        else:
            # Mixed types - return as list
            return extracted_data


def format_agent_request(
    action: str,
    data: Dict[str, Any],
    instructions: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized JSON request format for agent communication.
    
    This provides a consistent structure that all agents can understand.
    
    Args:
        action: The action being requested (e.g., "extract", "summarize", "verify")
        data: The data to process
        instructions: Optional specific instructions for the agent
        metadata: Optional metadata about the request
        
    Returns:
        Standardized request dictionary
    """
    request = {
        "action": action,
        "data": data,
        "timestamp": str(uuid.uuid4())  # For tracking
    }
    
    if instructions:
        request["instructions"] = instructions
    
    if metadata:
        request["metadata"] = metadata
    
    return request


def parse_agent_response(response: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parse an agent's response into a consistent format.
    
    Args:
        response: Agent's response (string or dict)
        
    Returns:
        Parsed response as dictionary
    """
    if isinstance(response, dict):
        return response
    
    if isinstance(response, str):
        # Try to parse as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Return as wrapped text
            return {
                "type": "text",
                "content": response
            }
    
    # Other types
    return {
        "type": "unknown",
        "content": str(response)
    }


def create_pipeline_message(
    step: str,
    input_data: Dict[str, Any],
    previous_results: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized message for pipeline processing.
    
    This format ensures consistency across all pipeline stages.
    
    Args:
        step: Current pipeline step name
        input_data: Primary input data for this step
        previous_results: Results from previous pipeline steps
        config: Configuration for this step
        
    Returns:
        Structured pipeline message
    """
    message = {
        "pipeline_step": step,
        "input": input_data,
        "request_id": str(uuid.uuid4())
    }
    
    if previous_results:
        message["context"] = previous_results
    
    if config:
        message["config"] = config
    
    return message