"""
Utility functions for creating properly formatted A2A message parts.
Ensures compatibility with Google ADK Runner and proper Part discrimination.

CRITICAL: Markdown content (.md files) MUST be sent as TextPart, not FilePart.
"""

from typing import Any, List, Union, Dict, Optional
from a2a.types import TextPart, DataPart, FilePart, Part, Message
import json
import mimetypes


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
    import base64
    
    file_obj = {"name": name}
    if uri:
        file_obj["uri"] = uri
    elif bytes_data:
        # FilePart expects base64 encoded string for bytes
        file_obj["bytes"] = base64.b64encode(bytes_data).decode('utf-8')
    else:
        # Must have either uri or bytes
        file_obj["uri"] = ""  # Empty URI as fallback
    
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


def detect_content_type(content: Any, filename: Optional[str] = None) -> str:
    """
    Detect the appropriate content type for the given content.
    
    Args:
        content: The content to analyze
        filename: Optional filename for MIME type detection
        
    Returns:
        MIME type string
    """
    # Check filename extension first
    if filename:
        # CRITICAL: Markdown files must be treated as text
        if filename.endswith('.md'):
            return "text/markdown"
        elif filename.endswith(('.txt', '.log', '.csv', '.tsv')):
            return "text/plain"
        elif filename.endswith(('.json', '.jsonl')):
            return "application/json"
        elif filename.endswith(('.xml', '.html', '.htm')):
            return "text/html"
        elif filename.endswith(('.yaml', '.yml')):
            return "text/yaml"
        
        # Use mimetypes for other files
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            return mime_type
    
    # Content-based detection
    if isinstance(content, str):
        # Check if it looks like markdown
        markdown_markers = ['# ', '## ', '### ', '```', '**', '__', '- [ ]', '- [x]', '![', '[](']
        if any(marker in content for marker in markdown_markers):
            return "text/markdown"
        # Check if it's JSON
        try:
            json.loads(content)
            return "application/json"
        except (json.JSONDecodeError, TypeError):
            pass
        return "text/plain"
    elif isinstance(content, (dict, list)):
        return "application/json"
    elif isinstance(content, bytes):
        return "application/octet-stream"
    else:
        return "text/plain"


def is_text_content(content: Any, filename: Optional[str] = None) -> bool:
    """
    Determine if content should be sent as TextPart.
    
    CRITICAL: Markdown content MUST always be sent as TextPart.
    
    Args:
        content: The content to check
        filename: Optional filename for type detection
        
    Returns:
        True if content should be TextPart, False if FilePart
    """
    # CRITICAL: Markdown files are ALWAYS text
    if filename and filename.endswith('.md'):
        return True
    
    # Check content type
    content_type = detect_content_type(content, filename)
    
    # Text MIME types that should be TextPart
    text_types = [
        "text/",  # All text/* types
        "application/json",
        "application/xml",
        "application/yaml",
        "application/x-yaml",
        "application/javascript",
        "application/typescript"
    ]
    
    return any(content_type.startswith(t) for t in text_types)


def create_part_from_file(
    content: Union[str, bytes],
    filename: str,
    mime_type: Optional[str] = None
) -> Part:
    """
    Create the appropriate Part type for file content.
    
    CRITICAL: Markdown files (.md) MUST be sent as TextPart, not FilePart.
    
    Args:
        content: File content (string or bytes)
        filename: Name of the file
        mime_type: Optional explicit MIME type
        
    Returns:
        Appropriate Part object (TextPart for markdown and text, FilePart for binary)
    """
    # Detect MIME type if not provided
    if not mime_type:
        mime_type = detect_content_type(content, filename)
    
    # CRITICAL: Markdown handling
    if filename.endswith('.md'):
        # Markdown MUST be TextPart
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        return TextPart(
            kind="text",
            text=str(content),
            metadata={"contentType": mime_type or "text/markdown"}
        )
    
    # Check if it's text content
    if is_text_content(content, filename):
        if isinstance(content, bytes):
            try:
                content = content.decode('utf-8')
            except UnicodeDecodeError:
                # If decode fails, treat as binary
                return create_file_part(
                    name=filename,
                    bytes_data=content,
                    mime_type=mime_type or "application/octet-stream"
                )
        
        return TextPart(
            kind="text",
            text=str(content),
            metadata={"contentType": mime_type} if mime_type else None
        )
    
    # Binary content
    if not isinstance(content, bytes):
        content = str(content).encode('utf-8')
    
    return create_file_part(
        name=filename,
        bytes_data=content,
        mime_type=mime_type or "application/octet-stream"
    )