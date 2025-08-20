# JSON Messaging Guide for A2A Agent Communication

## Overview

This guide documents the JSON-based messaging approach for agent-to-agent communication in the A2A pipeline, following the A2A v0.3.0 specification.

## Why JSON?

Based on the A2A specification (Section 6.5.3), using JSON provides:
- **Predictability**: Consistent message structure across all agents
- **Type Safety**: Clear contracts between agents  
- **Debugging**: Easier to trace and log structured data
- **A2A Compliance**: Follows specification recommendations for DataPart usage
- **Extensibility**: Easy to add new fields without breaking existing agents

## Message Structure

### Standard JSON Message Format

All agent messages should follow this structure:

```json
{
  "action": "action_name",       // Required: What the agent should do
  "data": {...},                  // Required: Primary data to process
  "instructions": "...",          // Optional: Specific instructions
  "metadata": {...},              // Optional: Additional context
  "timestamp": "uuid"             // Optional: For tracking
}
```

### Examples

#### Timeline Builder Request
```json
{
  "action": "build_timeline",
  "summary": "Patient summary text",
  "temporal_data": "Temporal extraction results",
  "encounters": "Grouped encounter data",
  "reconciled_data": "Reconciled clinical data",
  "instructions": "Build a chronological timeline of this cancer patient's journey"
}
```

#### Entity Extraction Request
```json
{
  "action": "extract_entities",
  "summary": "Clinical summary",
  "timeline": "Timeline data",
  "reconciled_data": "Reconciled data",
  "entity_types": ["medications", "procedures", "diagnoses"],
  "instructions": "Extract all medical entities from this clinical data"
}
```

## Implementation Details

### 1. Updated Base Class (`base.py`)

The base class now handles both TextPart and DataPart messages:
- Automatically detects JSON in messages
- Converts DataPart to JSON strings for processing
- Maintains backward compatibility with text messages

### 2. Simplified Agents

To avoid Google ADK parsing issues with complex type annotations:
- Created simplified versions without complex tools
- Agents process JSON directly via LLM
- Tool signatures use simple types (str, int) instead of `List[Dict[str, Any]]`

### 3. Agent Updates

#### Timeline Builder (`timeline_builder_simple.py`)
- Processes structured JSON input
- Builds chronological timelines without complex tools
- Returns JSON-structured timeline

#### Summary Extractor (`summary_extractor_simple.py`)
- Extracts structured summaries from JSON data
- Handles checker feedback for improvements
- Returns standardized JSON summary format

#### Unified Extractor (`unified_extractor_simple.py`)
- Processes JSON-structured entity extraction requests
- Returns organized medical entities

## Benefits

1. **Consistency**: All agents use the same message format
2. **Flexibility**: Easy to add new fields or modify structure
3. **Debugging**: Clear visibility into data flow between agents
4. **Error Handling**: Easier to validate and handle malformed messages
5. **Tool Compatibility**: Avoids complex type annotations that break Google ADK

## Migration Guide

### For Existing Agents

1. **Update message extraction**:
   ```python
   # Old way
   message = context.message.parts[0].text
   
   # New way (handles both text and JSON)
   message = self._extract_message(context)
   ```

2. **Parse JSON input**:
   ```python
   try:
       data = json.loads(message)
       # Process structured data
   except json.JSONDecodeError:
       # Fall back to text processing
   ```

3. **Simplify tool signatures**:
   ```python
   # Instead of
   def process(data: List[Dict[str, Any]]) -> Dict[str, Any]:
   
   # Use
   def process(data: str) -> str:
       parsed = json.loads(data)
   ```

## Best Practices

1. **Always validate JSON**: Check for required fields before processing
2. **Provide fallbacks**: Handle both JSON and text inputs gracefully
3. **Document expected format**: Include JSON schema in agent documentation
4. **Use descriptive actions**: Make the `action` field clear and specific
5. **Keep tools simple**: Avoid complex type annotations in tool functions

## Utilities

Use the provided utilities in `utils/json_messaging.py`:

```python
from utils.json_messaging import (
    create_json_message,      # Create A2A-compliant messages
    extract_json_from_message, # Extract JSON from A2A messages
    format_agent_request,      # Create standardized requests
    parse_agent_response,      # Parse agent responses
    create_pipeline_message    # Create pipeline-specific messages
)
```

## Troubleshooting

### Common Issues

1. **"'str' object has no attribute 'get'"**: Tool expects dict but receives string
   - Solution: Parse JSON or create simplified agent without tools

2. **"Failed to parse parameter"**: Google ADK can't parse complex types
   - Solution: Use simple types (str) and parse JSON manually

3. **"Request payload validation error"**: Malformed A2A message
   - Solution: Use proper Message/Part structure with DataPart for JSON

## Future Improvements

1. **Schema Validation**: Add JSON schema validation for each agent
2. **Type Definitions**: Create TypeScript-style type definitions
3. **Auto-conversion**: Automatic conversion between formats
4. **Error Recovery**: Better error messages and recovery strategies