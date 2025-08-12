# Base Classes for A2A Agents

This module provides two main base classes for building A2A-compliant agents:

## BaseLLMAgentExecutor

For LLM-powered agents with tools and streaming capabilities.

### Features
- Automatic A2A protocol compliance
- Multi-provider LLM support (Google Gemini, OpenAI GPT, Anthropic Claude)
- Session and memory management via Google ADK
- Streaming response support
- Automatic error handling and task state management

### Usage Example

```python
from base import BaseLLMAgentExecutor
from google.adk.tools import FunctionTool

class MyAssistant(BaseLLMAgentExecutor):
    def get_agent_name(self) -> str:
        return "My AI Assistant"
    
    def get_agent_description(self) -> str:
        return "A helpful AI assistant with search capabilities"
    
    def get_system_instruction(self) -> str:
        return "You are a helpful AI assistant. Be concise and friendly."
    
    def get_tools(self) -> List[FunctionTool]:
        return [
            FunctionTool(self.search_function)  # Just pass the function!
        ]
    
    def search_function(self, query: str) -> str:
        """Search for information."""  # Description goes in docstring
        return f"Search results for: {query}"

if __name__ == "__main__":
    agent = MyAssistant()
    agent.run()  # Starts on http://localhost:8000
```

### Environment Variables

The base class automatically detects LLM providers based on API keys:

```bash
# At least one required for LLM features
GOOGLE_API_KEY=your_key      # For Gemini models
OPENAI_API_KEY=your_key      # For GPT models  
ANTHROPIC_API_KEY=your_key   # For Claude models

# Optional model selection
GEMINI_MODEL=gemini-2.0-flash-001
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_MODEL=claude-3-5-haiku-20241022

# Agent configuration
AGENT_HEARTBEAT_INTERVAL=10.0
AGENT_CHUNK_TIMEOUT=120.0
```

## BaseAgentExecutor

For simple non-LLM agents with minimal boilerplate.

### Features
- Full A2A protocol compliance
- Minimal code required (< 20 lines)
- Perfect for deterministic processing
- No LLM dependencies
- Automatic task state management

### Usage Example

```python
from base import BaseAgentExecutor

class EchoAgent(BaseAgentExecutor):
    def get_agent_name(self) -> str:
        return "Echo Agent"
    
    def get_agent_description(self) -> str:
        return "Echoes back any message sent to it"
    
    async def process_message(self, message: str) -> str:
        return f"Echo: {message}"

if __name__ == "__main__":
    agent = EchoAgent()
    agent.run()  # Starts on http://localhost:8000
```

## Key Methods to Implement

### For BaseLLMAgentExecutor

| Method | Required | Description |
|--------|----------|-------------|
| `get_agent_name()` | Yes | Returns the agent's display name |
| `get_agent_description()` | Yes | Returns the agent's description |
| `get_system_instruction()` | Yes | Returns the LLM system prompt |
| `get_tools()` | Yes | Returns list of FunctionTool objects (can be empty) |

### For BaseAgentExecutor

| Method | Required | Description |
|--------|----------|-------------|
| `get_agent_name()` | Yes | Returns the agent's display name |
| `get_agent_description()` | Yes | Returns the agent's description |
| `process_message(message)` | Yes | Processes input and returns response |

## Automatic Features

Both base classes automatically handle:

1. **A2A Protocol Compliance**
   - AgentCard generation
   - Required methods (message/send, tasks/get, tasks/cancel)
   - Task state management
   - Error mapping to A2A error codes

2. **Platform Integration**
   - HealthUniverse URL detection (`HU_APP_URL`)
   - Health check endpoint (`/health`)
   - Well-known endpoint for agent card

3. **Task Lifecycle**
   - Automatic state transitions
   - Heartbeat for long-running tasks
   - Proper error handling
   - Context management

## Running Agents

### Local Development

```python
agent = MyAgent()
agent.run(host="0.0.0.0", port=8000)
```

### HealthUniverse Deployment

When deployed to HealthUniverse, the platform automatically:
- Sets `HU_APP_URL` environment variable
- Assigns a unique agent URL
- Manages containerization
- Handles scaling

## Testing

Test your agent locally:

```bash
# Start agent
python my_agent.py

# Test with curl
curl -X POST http://localhost:8000/message/send \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "message/send", "params": {"message": {"role": "user", "parts": [{"kind": "text", "text": "Hello"}]}}, "id": 1}'

# Check agent card
curl http://localhost:8000/.well-known/agentcard.json
```

## Error Handling

The base classes automatically handle errors and map them to A2A error codes:

- Python exceptions → JSON-RPC error codes
- Automatic retry for transient failures
- Timeout protection
- Graceful degradation

## Advanced Features

### Custom Processing (BaseLLMAgentExecutor)

Override `process_message()` for non-LLM fallback:

```python
async def process_message(self, message: str) -> str:
    # Called when LLM is not available
    return "Fallback response"
```

### Session Management

Sessions are automatically managed per task/context:
- Conversation history maintained
- Memory across interactions
- Artifact storage

## Troubleshooting

### No LLM Response
- Check API keys are set correctly
- Verify model name is valid
- Check rate limits

### Import Errors
- Ensure all requirements are installed
- Check Python version (3.9+)
- Verify a2a-sdk version

### Task State Issues
- Base class handles all transitions
- Check logs for state changes
- Verify error handling