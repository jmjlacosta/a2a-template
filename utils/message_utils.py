"""
Utility functions for creating properly formatted A2A message parts.
Ensures compatibility with Google ADK Runner and proper Part discrimination.
"""

from typing import Any, List, Union, Dict
from a2a.types import TextPart, DataPart, FilePart, Part, Message
import json


def create_text_part(text: str) -> TextPart:
    """
    Create a TextPart with proper kind field.
    
    Args:
        text: The text content
        
    Returns:
        TextPart with kind="text"
    """
    return TextPart(kind="text", text=str(text))


def create_data_part(data: Any) -> DataPart:
    """
    Create a DataPart with proper kind field for structured data.
    
    Args:
        data: The structured data (dict, list, or any JSON-serializable object)
        
    Returns:
        DataPart with kind="data"
    """
    return DataPart(kind="data", data=data)


def create_file_part(name: str, uri: str = None, bytes_data: bytes = None, mime_type: str = None) -> FilePart:
    """
    Create a FilePart with proper kind field.
    
    Args:
        name: File name
        uri: Optional URI to the file
        bytes_data: Optional file bytes
        mime_type: Optional MIME type
        
    Returns:
        FilePart with kind="file"
    """
    file_obj = {"name": name}
    if uri:
        file_obj["uri"] = uri
    if bytes_data:
        file_obj["bytes"] = bytes_data
    if mime_type:
        file_obj["mimeType"] = mime_type
    
    return FilePart(kind="file", file=file_obj)


def create_message_parts(content: Any) -> List[Part]:
    """
    Create proper Part objects based on content type.
    Automatically determines whether to use TextPart or DataPart.
    
    Args:
        content: The content to convert to Parts
        
    Returns:
        List of Part objects with proper kind discrimination
    """
    if isinstance(content, str):
        return [create_text_part(content)]
    elif isinstance(content, (dict, list)):
        return [create_data_part(content)]
    elif isinstance(content, Part):
        # Already a proper Part, ensure it has kind field
        if not hasattr(content, 'kind'):
            # Try to infer kind from type
            if isinstance(content, TextPart):
                content.kind = "text"
            elif isinstance(content, DataPart):
                content.kind = "data"
            elif isinstance(content, FilePart):
                content.kind = "file"
        return [content]
    elif isinstance(content, (tuple, set)):
        # Convert to list for DataPart
        return [create_data_part(list(content))]
    else:
        # Fallback: convert to string
        return [create_text_part(str(content))]


def create_agent_message(content: Any, role: str = "agent") -> Message:
    """
    Create a properly formatted agent Message with Parts.
    
    Args:
        content: The message content (string, dict, list, etc.)
        role: Message role (default "agent")
        
    Returns:
        Message with properly formatted Parts
    """
    import uuid
    
    parts = create_message_parts(content)
    
    return Message(
        role=role,
        parts=parts,
        kind="message",
        messageId=str(uuid.uuid4())
    )


def extract_content_from_parts(parts: List[Part]) -> Any:
    """
    Extract content from message parts, handling all Part types.
    
    Args:
        parts: List of Part objects
        
    Returns:
        Extracted content (string for text, dict/list for data, etc.)
    """
    if not parts:
        return None
    
    extracted = []
    
    for part in parts:
        # Handle both dict-like and object-like parts
        kind = None
        if isinstance(part, dict):
            kind = part.get("kind")
        elif hasattr(part, "kind"):
            kind = part.kind
        
        if kind == "text":
            # Extract text content
            text = None
            if isinstance(part, dict):
                text = part.get("text")
            elif hasattr(part, "text"):
                text = part.text
            if text is not None:
                extracted.append(text)
                
        elif kind == "data":
            # Return data directly if it's the only part
            data = None
            if isinstance(part, dict):
                data = part.get("data")
            elif hasattr(part, "data"):
                data = part.data
            if data is not None:
                if len(parts) == 1:
                    return data  # Return structured data directly
                extracted.append(data)
                
        elif kind == "file":
            # Handle file parts
            file_obj = None
            if isinstance(part, dict):
                file_obj = part.get("file")
            elif hasattr(part, "file"):
                file_obj = part.file
            if file_obj:
                extracted.append(file_obj)
    
    # If we have multiple parts or all text, join as strings
    if len(extracted) == 1:
        return extracted[0]
    elif all(isinstance(x, str) for x in extracted):
        return "\n".join(extracted)
    else:
        return extracted


def format_for_llm(parts: List[Part]) -> str:
    """
    Format message parts for LLM consumption.
    Converts all part types to a string representation.
    
    Args:
        parts: List of Part objects
        
    Returns:
        String representation suitable for LLM processing
    """
    formatted = []
    
    for part in parts:
        kind = getattr(part, "kind", None)
        
        if kind == "text":
            text = getattr(part, "text", "")
            formatted.append(text)
            
        elif kind == "data":
            data = getattr(part, "data", {})
            # Format data as JSON for LLM understanding
            if isinstance(data, (dict, list)):
                formatted.append(json.dumps(data, indent=2))
            else:
                formatted.append(str(data))
                
        elif kind == "file":
            file_obj = getattr(part, "file", {})
            name = file_obj.get("name", "unnamed") if isinstance(file_obj, dict) else "unnamed"
            uri = file_obj.get("uri") if isinstance(file_obj, dict) else None
            if uri:
                formatted.append(f"[File: {name}] {uri}")
            else:
                formatted.append(f"[File: {name}]")
    
    return "\n".join(formatted)