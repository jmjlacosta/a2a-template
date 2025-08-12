# A2A Agent Examples

This directory contains example agent implementations demonstrating different patterns and complexities, all using the A2A template base classes.

## 🎯 Examples Overview

| Agent | Complexity | Lines | LLM Required | Description |
|-------|------------|-------|--------------|-------------|
| [Simple Echo](#1-simple-echo-agent) | ⭐ | ~20 | No | Echoes messages back |
| [Text Processor](#2-text-processor-agent) | ⭐⭐ | ~50 | No | Text transformations |
| [LLM Assistant](#3-llm-assistant-agent) | ⭐⭐ | ~60 | Yes | AI assistant with tools |
| [Document Analyzer](#4-document-analyzer-agent) | ⭐⭐⭐ | ~150 | Yes | Document processing |
| [Orchestrator](#5-multi-agent-orchestrator) | ⭐⭐⭐⭐ | ~200 | Yes | Multi-agent coordination |
| [Regulatory Compliance](#6-regulatory-compliance-validator) | ⭐⭐⭐ | ~800 | No | HIPAA/CFR compliance checker |
| [AI Compliance Validator](#7-ai-regulatory-compliance) | ⭐⭐⭐⭐ | ~900 | Yes | AI-enhanced compliance analysis |

## 1. Simple Echo Agent

**File:** `simple_echo_agent.py`

The simplest possible A2A-compliant agent in under 20 lines of code.

### Features:
- Minimal implementation using `BaseAgentExecutor`
- No LLM required
- Automatic A2A protocol compliance
- Zero configuration

### Usage:
```bash
python simple_echo_agent.py
```

### Example Interaction:
```
Input: "Hello, agent!"
Output: "Echo: Hello, agent!"
```

### Key Learning:
- How simple it is to create an A2A-compliant agent
- BaseAgentExecutor handles all protocol details
- Perfect starting point for custom agents

## 2. Text Processor Agent

**File:** `text_processor_agent.py`

Demonstrates deterministic text processing without LLM.

### Features:
- Multiple text operations (uppercase, lowercase, word count, etc.)
- Command-based message parsing
- No LLM or API keys required
- Useful for text transformation pipelines

### Usage:
```bash
python text_processor_agent.py
```

### Available Commands:
- `uppercase: <text>` - Convert to uppercase
- `lowercase: <text>` - Convert to lowercase
- `wordcount: <text>` - Count words
- `reverse: <text>` - Reverse text
- `remove_spaces: <text>` - Remove all spaces
- `extract_numbers: <text>` - Extract numbers from text

### Example Interactions:
```
Input: "uppercase: hello world"
Output: "HELLO WORLD"

Input: "wordcount: this is a test"
Output: "Word count: 4"

Input: "extract_numbers: The price is $42.50 for 3 items"
Output: "Numbers found: 42, 50, 3"
```

### Key Learning:
- Building agents with business logic
- Command parsing patterns
- Deterministic operations without LLM

## 3. LLM Assistant Agent

**File:** `llm_assistant_agent.py`

AI assistant demonstrating `BaseLLMAgentExecutor` with custom tools.

### Features:
- LLM-powered conversational agent
- Custom tools (time, calculator, weather)
- Automatic provider detection (Google/OpenAI/Anthropic)
- System instructions for behavior control

### Setup:
```bash
# Set one of these API keys
export GOOGLE_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"

python llm_assistant_agent.py
```

### Available Tools:
- `get_current_time()` - Returns current date and time
- `calculate(expression)` - Performs math calculations
- `get_weather(city)` - Returns weather info (mock data)

### Example Interactions:
```
Input: "What time is it?"
Output: "The current time is 2024-03-15 14:30:45"

Input: "Calculate 15% tip on $85.50"
Output: "A 15% tip on $85.50 would be $12.83"

Input: "What's the weather in Paris?"
Output: "Weather in Paris: Partly cloudy, 22°C, humidity 65%"
```

### Key Learning:
- Adding tools to LLM agents
- System instruction configuration
- Multi-provider LLM support

## 4. Document Analyzer Agent

**File:** `document_analyzer_agent.py`

Advanced document processing with chunking and analysis.

### Features:
- Semantic document chunking
- Keyword extraction
- Structure analysis
- Entity extraction
- Combines LLM with deterministic processing

### Setup:
```bash
export GOOGLE_API_KEY="your-key"  # or other provider
python document_analyzer_agent.py
```

### Available Tools:
- `extract_chunks(text, chunk_size)` - Split into semantic chunks
- `find_keywords(text, max_keywords)` - Extract key terms
- `analyze_structure(text)` - Analyze document structure
- `extract_entities(text)` - Find dates, numbers, emails, etc.

### Example Interactions:
```
Input: "Analyze this document: [long text]"
Output: Structured analysis with chunks, keywords, and entities

Input: "Extract keywords from: [article text]"
Output: Top keywords with frequencies

Input: "Find the structure of: [document]"
Output: Headers, sections, lists, statistics
```

### Key Learning:
- Complex tool implementations
- Combining multiple analysis techniques
- Processing large documents efficiently

## 5. Multi-Agent Orchestrator

**File:** `orchestrator_agent.py`

Coordinates multiple specialized agents to solve complex tasks.

### Features:
- Inter-agent communication
- Dynamic tool creation for each agent
- Parallel and sequential execution
- Result combination and synthesis
- Agent discovery from registry

### Setup:

#### Step 1: Configure Agent Registry
Create or update `config/agents.json`:
```json
{
  "agents": {
    "echo_agent": {
      "url": "http://localhost:8000",
      "description": "Echoes messages"
    },
    "text_processor": {
      "url": "http://localhost:8001",
      "description": "Processes text"
    },
    "assistant": {
      "url": "http://localhost:8002",
      "description": "AI assistant"
    }
  }
}
```

#### Step 2: Start Individual Agents
```bash
# Terminal 1
python simple_echo_agent.py

# Terminal 2
python text_processor_agent.py

# Terminal 3
python llm_assistant_agent.py
```

#### Step 3: Start Orchestrator
```bash
export GOOGLE_API_KEY="your-key"
python orchestrator_agent.py
```

### Orchestration Patterns:

#### Parallel Execution:
```
Input: "Run these in parallel: echo 'test', uppercase 'hello', get current time"
Output: Results from all three agents executed simultaneously
```

#### Sequential Pipeline:
```
Input: "Process this pipeline: get time, then uppercase it, then echo it"
Output: Time → UPPERCASE TIME → Echo: UPPERCASE TIME
```

#### Smart Routing:
```
Input: "Analyze this document and extract keywords"
Output: Routes to document analyzer for the task
```

### Key Learning:
- Multi-agent coordination patterns
- Dynamic tool generation
- Parallel vs sequential execution
- Error handling in distributed systems

## 🚀 Running the Examples

### Local Development

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set API keys (for LLM agents):**
```bash
export GOOGLE_API_KEY="your-key"
# OR
export OPENAI_API_KEY="your-key"
# OR
export ANTHROPIC_API_KEY="your-key"
```

3. **Run an agent:**
```bash
python examples/simple_echo_agent.py
```

4. **Test the agent:**
```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Hello!"}]
      }
    },
    "id": 1
  }'
```

### HealthUniverse Deployment

Each example can be deployed to HealthUniverse:

1. **Copy example to main directory:**
```bash
cp examples/simple_echo_agent.py main.py
```

2. **Commit and push:**
```bash
git add main.py
git commit -m "Deploy echo agent"
git push
```

3. **Deploy via HealthUniverse dashboard**

## 📚 Learning Path

### Beginner:
1. Start with **Simple Echo Agent** - understand basic structure
2. Try **Text Processor** - add business logic
3. Modify commands in Text Processor

### Intermediate:
1. Run **LLM Assistant** - work with AI
2. Add new tools to the assistant
3. Customize system instructions

### Advanced:
1. Study **Document Analyzer** - complex processing
2. Implement new analysis functions
3. Deploy **Orchestrator** - multi-agent systems
4. Create agent pipelines

## 🎨 Creating Your Own Agent

Use these examples as templates:

### For Simple Logic:
Start with `simple_echo_agent.py` or `text_processor_agent.py`

### For AI Agents:
Start with `llm_assistant_agent.py`

### For Complex Processing:
Start with `document_analyzer_agent.py`

### For Multi-Agent Systems:
Start with `orchestrator_agent.py`

## 💡 Tips

1. **Keep agents focused** - Each agent should do one thing well
2. **Use appropriate base class** - BaseAgentExecutor for logic, BaseLLMAgentExecutor for AI
3. **Test locally first** - Ensure agents work before deploying
4. **Document your tools** - Clear docstrings help LLMs use tools correctly
5. **Handle errors gracefully** - Return helpful error messages

## 🐛 Troubleshooting

### "No API key found"
- Set GOOGLE_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY

### "Agent not found" (Orchestrator)
- Check `config/agents.json` has correct URLs
- Ensure target agents are running

### "Connection refused"
- Check agent is running on correct port
- Verify firewall settings

### "Tool not found"
- Ensure tool functions have proper docstrings
- Check FunctionTool initialization

## 📖 Further Reading

- [A2A Protocol Specification](../README.md)
- [Base Classes Documentation](../base/README.md)
- [Utility Modules](../utils/)
- [HealthUniverse Deployment Guide](../HEALTHUNIVERSE_DEPLOYMENT.md)

---

Happy agent building! 🤖✨
## 6. Regulatory Compliance Validator

**File:** `regulatory_compliance_agent.py`

Pattern-based regulatory compliance validator for healthcare protocols.

### Features:
- Validates against HIPAA, 21 CFR Part 11, IRB, and ONC HTI-1
- Pattern-based detection with context extraction
- Risk scoring (0-100 scale)
- Detailed findings with regulatory references
- No LLM required - works offline

### Compliance Frameworks:
- **HIPAA**: PHI protection, security, audit controls, authorization
- **21 CFR Part 11**: Electronic records/signatures, validation, audit trails
- **IRB**: Informed consent, risk assessment, vulnerable populations
- **ONC HTI-1**: Data transparency, interoperability, patient access

### Usage:
```bash
python regulatory_compliance_agent.py
```

### Example Input:
```
"We collect patient names and medical records for our study.
Data is stored in our database with password protection."
```

### Example Output:
```
Risk Score: 65/100 🔴
Issues Found:
  🔴 HIPAA: PHI not properly de-identified
  🟡 HIPAA: Encryption not specified
  ⚪ 21 CFR Part 11: Audit trail not mentioned
```

## 7. AI Regulatory Compliance Validator

**File:** `regulatory_compliance_ai_agent.py`

AI-enhanced compliance validator using LLM for intelligent context analysis.

### Features:
- All features of basic validator PLUS:
- LLM-powered context analysis to reduce false positives
- Confidence scoring for each finding (0-100%)
- Understands temporal context (past vs current vs future)
- Differentiates between mentions and actual practices
- Provides detailed AI explanations

### Key Improvements:
- **Fewer False Positives**: AI understands when compliance measures are actually in place
- **Context Awareness**: Distinguishes "we will implement" from "we have implemented"
- **Confidence Scoring**: Prioritize high-confidence violations
- **Intelligent Analysis**: Explains WHY something is or isn't compliant

### Usage:
```bash
# Requires LLM API key
export OPENAI_API_KEY="your-key"  # or GOOGLE_API_KEY, ANTHROPIC_API_KEY
python regulatory_compliance_ai_agent.py
```

### Example Comparison:

**Text**: "We implement AES-256 encryption for all patient data"

- **Pattern-only**: ✅ Detects mention of encryption
- **AI-Enhanced**: ✅ Confirms this indicates COMPLIANT encryption implementation

**Text**: "Encryption will be considered for future implementation"

- **Pattern-only**: ✅ Detects mention of encryption (false positive)
- **AI-Enhanced**: 🔴 Recognizes encryption is NOT yet implemented (correct)

### Testing:
```bash
# Run comparison tests
python test_regulatory_ai.py

# Interactive Jupyter demo
jupyter notebook regulatory_compliance_demo.ipynb
```

### Integration Example:
Both compliance validators can be integrated into larger workflows:

```python
# Use in orchestrator for multi-step validation
orchestrator = OrchestratorAgent()
orchestrator.register_agent("compliance", "http://localhost:8000")

# Chain with other agents
protocol_generator → compliance_validator → approval_workflow
```

---

## 🚀 Running the Examples

### Individual Agents:
```bash
# Run any agent standalone
python examples/agent_name.py
```

### Testing:
```bash
# Test individual agent
python test_simple_agent.py
python test_regulatory_compliance.py
python test_regulatory_ai.py
```

### Deployment:
All agents are fully A2A compliant and can be deployed to:
- Local development (localhost)
- HealthUniverse platform
- Any A2A-compatible orchestrator

## 📚 Learning Path

1. Start with **Simple Echo** to understand basics
2. Try **Text Processor** for deterministic operations
3. Explore **LLM Assistant** for AI capabilities
4. Study **Document Analyzer** for async operations
5. Learn **Orchestrator** for multi-agent systems
6. Implement **Regulatory Compliance** for domain-specific validation
7. Enhance with **AI Compliance** for intelligent analysis

Each example builds on previous concepts while introducing new patterns\!
EOF < /dev/null
