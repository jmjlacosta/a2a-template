# LLM Setup for A2A Agent Examples

## Quick Start with OpenAI

Most examples that use LLMs have been updated to work directly with OpenAI API:

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-openai-api-key"

# Run an LLM-powered agent
python examples/llm_assistant_agent.py
```

## Examples with LLM Support

### Simple Examples (No LLM Required)
- `simple_echo_agent.py` - Basic echo functionality
- `text_processor_agent.py` - Text transformations
- `regulatory_compliance_agent.py` - Pattern-based compliance checking
- `test_simple_agent.py` - Test echo agent

### LLM-Powered Examples
- `llm_assistant_agent.py` - AI assistant with tools (uses OpenAI directly)
- `document_analyzer_agent.py` - Document analysis with AI
- `orchestrator_agent.py` - Multi-agent orchestration
- `regulatory_compliance_ai_agent.py` - AI-enhanced compliance validation
- `test_llm_agent.py` - Test LLM agent

## Using OpenAI

The `llm_assistant_agent.py` example shows how to use OpenAI API directly:

```python
from openai import OpenAI

# In your process_message method:
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": message}
    ]
)
return response.choices[0].message.content
```

## Using Google ADK (Alternative)

Some examples still reference Google ADK. To use these with Google's Gemini:

```bash
export GOOGLE_API_KEY="your-google-api-key"
```

Or to use with OpenAI through ADK:

```python
from google.adk.agents.llm_agent import LlmAgent

agent = LlmAgent(
    name="Assistant",
    model="openai/gpt-3.5-turbo",  # OpenAI model through ADK
    instruction="You are a helpful assistant"
)
```

## Installation

```bash
# For OpenAI support
pip install openai

# For Google ADK support (optional)
pip install google-adk
```

## Notes

- The simplified examples use OpenAI API directly for clarity
- Google ADK supports both OpenAI and Google models
- You only need one API key (either OpenAI or Google) to run the LLM examples