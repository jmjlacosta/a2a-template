# Document the JSON/Text Input/Output Architecture for Agent Communication

## Problem Statement
We've implemented a sophisticated message routing system in `base.py` that intelligently handles different message formats (JSON vs text) and execution paths (direct tools vs LLM). This architecture enables reliable agent-to-agent communication while maintaining human-friendly interfaces. However, this work is not documented and risks being lost or misunderstood.

## Background
During the development of the medical document analysis pipeline, we discovered that agents needed different handling for:
- **Agent-to-agent communication**: Should use structured JSON for predictability
- **Human-to-agent communication**: Should use natural language with LLM processing
- **Mixed scenarios**: Agents with tools need to handle both cases appropriately

## Current Implementation
The `base.py` execute method now implements intelligent routing:

```python
# Check if this is a JSON request (agent-to-agent communication)
is_json_request = False
try:
    json.loads(message)
    is_json_request = True
except (json.JSONDecodeError, TypeError):
    pass

# Route based on message type and tools availability
if tools and is_json_request:
    # JSON + tools = direct tool execution (bypasses LLM)
    response = await self._execute_tools_directly(message, updater)
elif tools:
    # Text + tools = LLM with tools (Google ADK)
    await self._execute_with_tools(message, updater, task.id)
else:
    # No tools = process_message + LLM
    response = await self._execute_with_llm_no_tools(message, updater)
```

## Tasks

### 1. Create JSON_TEXT_ARCHITECTURE.md
Document should include:
- Overview of the three execution paths
- Decision tree diagram showing routing logic
- When each path is used and why

### 2. Document the Three Execution Paths

#### Path 1: JSON + Tools → Direct Tool Execution
- **When used**: Agent receives JSON message AND has tools defined
- **Purpose**: Efficient agent-to-agent communication without LLM overhead
- **Example agents**: grep_agent, chunk_agent when called by orchestrators
- **Returns**: JSON response from tool

#### Path 2: Text + Tools → LLM with Tools
- **When used**: Agent receives text message AND has tools defined
- **Purpose**: Human interaction with intelligent tool selection
- **Example**: User asks grep agent to "find all mentions of diabetes"
- **Returns**: Human-readable text via LLM

#### Path 3: No Tools → Process Message + LLM
- **When used**: Agent has no tools defined
- **Purpose**: Pure LLM-based processing
- **Example**: Simple response generation agents
- **Returns**: LLM-generated text

### 3. Document Agent Implementation Guidelines

#### For Agents with Tools:
```python
async def process_message(self, message: str) -> str:
    try:
        # Try to parse as JSON
        data = json.loads(message)
        
        # Check if this is a request we can handle directly
        if "expected_field" in data:
            # Call tool directly
            from tools.my_tools import my_tool_function
            result = my_tool_function(...)
            return result  # Return JSON string
        else:
            # Not our JSON format, return for LLM processing
            return message
            
    except json.JSONDecodeError:
        # Not JSON, return for LLM processing
        return message
```

### 4. Include Working Examples

#### Example 1: Grep Agent
- Shows how it detects JSON with patterns and document_content
- Calls search_medical_patterns tool directly
- Returns JSON results

#### Example 2: Chunk Agent  
- Handles both single and multiple match requests
- Processes matches array from orchestrators
- Returns structured chunk data

#### Example 3: Simple Orchestrator
- Sends JSON to agents
- Parses JSON responses
- Falls back to text parsing when needed

### 5. Testing Guidelines
- How to test agent with JSON input
- How to test agent with text input
- How to verify correct routing

### 6. Migration Guide
For updating existing agents to support this architecture:
1. Implement process_message to detect JSON
2. Call tools directly for recognized JSON formats
3. Return message unchanged for LLM processing otherwise
4. Remove duplicate process_message methods

## Benefits of This Architecture
1. **Performance**: Agent-to-agent calls bypass LLM for 10x faster response
2. **Reliability**: Structured JSON ensures predictable parsing
3. **Flexibility**: Same agent handles both human and agent callers
4. **A2A Compliance**: Uses TextPart for all responses per spec
5. **Cost Efficiency**: Reduces LLM token usage for agent pipelines

## Acceptance Criteria
- [ ] JSON_TEXT_ARCHITECTURE.md created with all sections
- [ ] All three execution paths documented with examples
- [ ] Guidelines for implementing new agents included
- [ ] Testing procedures documented
- [ ] Migration guide for existing agents provided

## Priority
**HIGH** - This architecture is fundamental to the pipeline's operation and must be preserved

## Labels
- documentation
- architecture
- agent-communication
- critical