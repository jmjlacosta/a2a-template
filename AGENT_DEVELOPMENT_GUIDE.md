# Agent Development Guide

A step-by-step guide for creating A2A-compliant agents using this template.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Creating Your First Agent](#creating-your-first-agent)
4. [Migration Guide](#migration-guide-converting-existing-code)
5. [Testing Your Agent](#testing-your-agent)
6. [Deployment](#deployment)

## Overview

This template provides a simplified base class (`A2AAgent`) that handles all the complex A2A protocol requirements, letting you focus on your agent's business logic. Agents can be:

- **Simple agents** - Just process messages and return responses
- **Tool-based agents** - Use LLM with function tools for complex operations
- **Orchestrator agents** - Coordinate multiple agents to complete tasks

## Prerequisites

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up LLM API Key
You need at least one LLM provider API key:
```bash
# Choose one:
export GOOGLE_API_KEY="your-gemini-api-key"      # Preferred
export OPENAI_API_KEY="your-openai-api-key"      # Alternative
export ANTHROPIC_API_KEY="your-claude-api-key"   # Alternative
```

## Creating Your First Agent

### Option 1: Simple Agent (No Tools)

For basic message processing without LLM tools:

```python
#!/usr/bin/env python3
"""
My Simple Agent - Description of what it does.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base import A2AAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


class MySimpleAgent(A2AAgent):
    """Your agent description."""
    
    def get_agent_name(self) -> str:
        return "My Simple Agent"
    
    def get_agent_description(self) -> str:
        return "Detailed description of what your agent does"
    
    async def process_message(self, message: str) -> str:
        """Process the message and return a response."""
        # Your logic here
        return f"Processed: {message}"


# Module-level app creation (required for deployment)
agent = MySimpleAgent()
agent_card = agent.create_agent_card()
task_store = InMemoryTaskStore()
request_handler = DefaultRequestHandler(
    agent_executor=agent,
    task_store=task_store
)

app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
).build()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting {agent.get_agent_name()}")
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### Option 2: Tool-Based Agent (With LLM and Functions)

For agents that need to use tools/functions with an LLM:

```python
#!/usr/bin/env python3
"""
My Tool Agent - Uses LLM with function tools.
"""

import os
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from base import A2AAgent
from google.adk.tools import FunctionTool
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore


# Define your tool functions
def search_database(query: str, limit: int = 10) -> str:
    """Search the database for information."""
    # Your implementation
    return f"Found {limit} results for: {query}"

def calculate_something(value1: float, value2: float) -> str:
    """Perform a calculation."""
    result = value1 + value2
    return f"Result: {result}"


class MyToolAgent(A2AAgent):
    """Agent that uses tools via LLM."""
    
    def get_agent_name(self) -> str:
        return "My Tool Agent"
    
    def get_agent_description(self) -> str:
        return "Agent that uses tools to process requests"
    
    def get_system_instruction(self) -> str:
        """Instructions for the LLM on how to use tools."""
        return """You are a helpful assistant with access to tools.
        
        Use the search_database tool to find information.
        Use the calculate_something tool for calculations.
        
        Always explain what you're doing."""
    
    def get_tools(self) -> List:
        """Provide tools for the LLM to use."""
        return [
            FunctionTool(func=search_database),
            FunctionTool(func=calculate_something)
        ]
    
    async def process_message(self, message: str) -> str:
        # This won't be called when tools are provided
        # The base handles everything via Google ADK
        return "Handled by tool execution"


# Module-level app creation
agent = MyToolAgent()
agent_card = agent.create_agent_card()
task_store = InMemoryTaskStore()
request_handler = DefaultRequestHandler(
    agent_executor=agent,
    task_store=task_store
)

app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
).build()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting {agent.get_agent_name()}")
    uvicorn.run(app, host="0.0.0.0", port=port)
```

## Migration Guide: Converting Existing Code

If you have existing code (like our ADK demo pipeline), here's how to migrate it:

### Step 1: Analyze Your Existing Code

Identify:
- **Functions/tools** your code uses
- **System prompts** or instructions
- **Input/output formats**
- **Dependencies**

### Step 2: Extract Tool Functions

If your code has functions that should be LLM tools:

1. **Create a tools file** (`tools/my_tools.py`):
```python
from google.adk.tools import FunctionTool

def my_function(param1: str, param2: int) -> str:
    """Function description for LLM."""
    # Your existing function code
    return result

# Wrap functions as tools
my_tool = FunctionTool(func=my_function)

# Export tools list
MY_TOOLS = [my_tool]
```

2. **Keep functions unchanged** - Just wrap them with `FunctionTool`

### Step 3: Create Agent Class

Create your agent in `examples/` or `examples/pipeline/`:

```python
#!/usr/bin/env python3
"""
Agent name and description.
"""

import os
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))  # Adjust path as needed

from base import A2AAgent
from tools.my_tools import MY_TOOLS  # Import your tools
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill


class MyMigratedAgent(A2AAgent):
    
    def get_agent_name(self) -> str:
        return "Name from original agent"
    
    def get_agent_description(self) -> str:
        return "Description from original agent"
    
    def get_agent_version(self) -> str:
        return "2.0.0"  # Version after migration
    
    def get_system_instruction(self) -> str:
        """Copy system prompt from original agent."""
        return """Original system instructions here..."""
    
    def get_tools(self) -> List:
        """Return imported tools."""
        return MY_TOOLS
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """Optional: Define skills for agent discovery."""
        return [
            AgentSkill(
                id="skill_id",
                name="Skill Name",
                description="What this skill does",
                tags=["tag1", "tag2"],
                examples=["Example usage 1", "Example usage 2"]
            )
        ]
    
    def supports_streaming(self) -> bool:
        """Enable streaming for real-time updates."""
        return True
    
    async def process_message(self, message: str) -> str:
        # Not called when tools are provided
        return "Handled by tool execution"


# Standard app creation pattern
agent = MyMigratedAgent()
agent_card = agent.create_agent_card()
task_store = InMemoryTaskStore()
request_handler = DefaultRequestHandler(
    agent_executor=agent,
    task_store=task_store
)

app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
).build()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### Step 4: Key Migration Points

| Original Pattern | New Pattern |
|-----------------|-------------|
| Complex base class with streaming | Simplified `A2AAgent` base |
| Manual LLM setup | Automatic via `get_tools()` |
| Session management code | Handled by Google ADK |
| Heartbeat/streaming logic | Built-in via TaskUpdater |
| Manual error handling | Automatic A2A compliance |

### Step 5: What Gets Simplified

✅ **Remove**:
- Session management code
- Streaming/heartbeat logic
- LLM initialization code
- Manual task management
- Complex error handling

✅ **Keep**:
- Tool functions (unchanged)
- System instructions
- Agent metadata
- Business logic

## Testing Your Agent

### Universal Test Suite

Test any agent with our universal tester:

```bash
# Test your agent
python test_any_agent.py examples.my_agent MyAgentClass

# Examples
python test_any_agent.py examples.pipeline.grep_agent GrepAgent
python test_any_agent.py examples.simple_echo_agent EchoAgent
```

The tester validates:
- Agent properties (name, description, version)
- Agent card generation
- Tool configuration
- Skills definition
- Message processing
- A2A protocol compliance

### Manual Testing

1. **Start your agent**:
```bash
python examples/my_agent.py
```

2. **Check agent card**:
```bash
curl http://localhost:8000/.well-known/agent-card.json
```

3. **Send a test message**:
```bash
curl -X POST http://localhost:8000/v1/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Test message"}'
```

## Deployment

### For HealthUniverse

1. **Ensure module-level `app` variable**:
```python
# This MUST be at module level for HealthUniverse
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
).build()
```

2. **Agent Discovery**:
- Agent card available at `/.well-known/agent-card.json`
- Also available at `/.well-known/agent.json` (HealthUniverse compatible)

3. **Environment Variables**:
```bash
# Required
GOOGLE_API_KEY=xxx  # or OPENAI_API_KEY or ANTHROPIC_API_KEY

# Optional
PORT=8000
HU_APP_URL=https://apps.healthuniverse.com/xxx-xxx-xxx
```

### For Inter-Agent Communication

Agents can call each other:

```python
# In your agent's process_message or system instruction:
response = await self.call_other_agent(
    "agent-name",  # From config/agents.json
    "Message to send"
)
```

Configure known agents in `config/agents.json`:
```json
{
  "agents": {
    "agent-name": {
      "url": "https://apps.healthuniverse.com/xxx-xxx-xxx",
      "name": "Agent Display Name",
      "description": "What this agent does"
    }
  }
}
```

## Best Practices

### 1. Tool Design
- Keep tool functions focused and single-purpose
- Include clear docstrings (LLM reads these)
- Handle errors gracefully
- Support optional parameters with defaults

### 2. System Instructions
- Be specific about tool usage
- Include examples in the prompt
- Explain expected input/output formats
- Guide the LLM's decision-making

### 3. File Organization
```
examples/
  pipeline/           # Complex multi-agent systems
    grep_agent.py
    chunk_agent.py
  simple_agent.py     # Standalone agents
  
tools/
  grep_tools.py       # Reusable tool functions
  common_tools.py
```

### 4. Error Handling
- The base handles A2A protocol errors
- Focus on your business logic errors
- Return helpful error messages
- Log appropriately

### 5. Testing
- Always run the universal tester
- Test with actual LLM calls
- Verify agent card generation
- Test tool execution paths

## Common Patterns

### Pattern 1: Search and Process
```python
def search_content(query: str, content: str) -> str:
    """Search content without file access."""
    # Process content directly
    return results
```

### Pattern 2: Validation
```python
def validate_input(data: str) -> str:
    """Validate and potentially fix input."""
    # Validation logic
    return validation_results
```

### Pattern 3: Analysis
```python
def analyze_data(data: str, criteria: List[str]) -> str:
    """Analyze data against criteria."""
    # Analysis logic
    return analysis_results
```

## Advanced Topics

### Inter-Agent Communication

Agents can call other agents using the `call_other_agent` method:

```python
async def process_message(self, message: str) -> str:
    # Call another agent
    response = await self.call_other_agent("agent_name", "message")
    return response
```

**Important**: Configure agent URLs in `config/agents.json`:
```json
{
  "agents": {
    "agent_name": {
      "url": "http://localhost:8002"
    }
  }
}
```

### Async Tool Functions

Google ADK's `FunctionTool` supports async functions natively:

```python
# Async functions work directly with FunctionTool
async def my_async_tool(param: str) -> str:
    """Async tool function."""
    result = await some_async_operation()
    return result

# No special handling needed
my_tool = FunctionTool(func=my_async_tool)
```

**Important**: Do NOT use `asyncio.run()` in tool functions - the agent's `execute()` method already runs in an async context.

### Handling Single-Line Documents

For agents processing documents (like medical records that may be single paragraphs):

1. **Detect single-line documents**:
```python
lines = document.split('\n')
is_single_line = len(lines) == 1
```

2. **Deduplicate processing**:
```python
# Don't process the same line multiple times
unique_lines = {}
for match in matches:
    line_num = match.get("line_number", 1)
    if line_num not in unique_lines:
        unique_lines[line_num] = match
```

3. **Smart chunking strategies**:
- For short single-line docs (<2000 chars): Process entire document once
- For long single-line docs: Extract segments around key matches
- Limit chunk extraction to avoid redundant processing

### Orchestrator Patterns

Two orchestration approaches:

1. **Dynamic Orchestrator**: Uses LLM with tools to decide agent calling sequence
   - More flexible, adapts to different queries
   - Higher latency due to LLM decision-making
   - Better for complex, varied requests

2. **Simple/Fixed Orchestrator**: Direct sequential pipeline execution
   - Faster execution (no LLM decisions)
   - Predictable behavior
   - Better for well-defined workflows

## Troubleshooting

### Issue: "No LLM API key found"
**Solution**: Set one of the environment variables:
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

### Issue: "asyncio.run() cannot be called from a running event loop"
**Solution**: Your tool functions are trying to create a new event loop. Use async functions directly without `asyncio.run()`.

### Issue: "Module not found"
**Solution**: Ensure proper path setup:
```python
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Issue: Tools not executing
**Solution**: 
- Verify `get_tools()` returns FunctionTool objects
- Check system instruction mentions the tools
- Ensure LLM API key is set

### Issue: Agent card not accessible
**Solution**:
- Check the module-level `app` variable exists
- Verify A2AStarletteApplication is built correctly
- Try both endpoints: `/agent-card.json` and `/agent.json`

## Next Steps

1. Start with a simple agent to understand the pattern
2. Add tools as needed for complex operations
3. Test thoroughly with the universal tester
4. Deploy and integrate with other agents
5. Build orchestrators to coordinate multiple agents

## Support

- Check existing examples in `examples/` directory
- Review the [A2A Specification](A2A_SPECIFICATION.md)
- See [Migration Guide Issue #18](https://github.com/jmjlacosta/a2a-template/issues/18) for complex migrations
- Test with `test_any_agent.py` for validation

---

Remember: The base handles all A2A complexity. Focus on your agent's unique functionality!