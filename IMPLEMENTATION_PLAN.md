# A2A Template Repository Implementation Plan

## Executive Summary

This issue outlines the plan to create a production-ready template repository for building A2A-compliant agents on the HealthUniverse platform. The goal is to make it nearly impossible for developers to create non-compliant agents while keeping the implementation as simple as possible.

## Problem Statement

Currently, developers need to:
- Understand the A2A protocol specification details
- Write significant boilerplate code for each agent
- Handle protocol compliance manually
- Debug protocol-related errors in production
- Manage platform-specific requirements (HU_APP_URL, deployment patterns)

## Solution Overview

Create an enhanced template repository with:
- **Base classes that handle ALL A2A compliance automatically**
- **< 50 lines of code required for new agents**
- **Zero configuration needed post-deployment**
- **Support for both LLM and non-LLM agents**
- **Built-in validation and error handling**

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)

#### 1.1 Enhanced Base Classes

**BaseLLMAgentExecutor** - For LLM-powered agents
```python
class MyAgent(BaseLLMAgentExecutor):
    def get_agent_name(self) -> str:
        return "My Agent"
    
    def get_system_instruction(self) -> str:
        return "You are a helpful agent that..."
    
    def get_tools(self) -> List[FunctionTool]:
        return [tool1, tool2]  # Automatically validated
```

Features:
- Auto-detect LLM provider (Google/OpenAI/Anthropic)
- Handle all A2A protocol requirements
- Manage task state machine with proper transitions
- Built-in streaming and session management
- Automatic error mapping to A2A error codes

**BaseAgentExecutor** - For simple non-LLM agents
```python
class SimpleAgent(BaseAgentExecutor):
    def get_agent_name(self) -> str:
        return "Simple Agent"
    
    async def process_message(self, message: str) -> str:
        return f"Processed: {message}"
```

Features:
- Minimal boilerplate for deterministic agents
- Full A2A compliance without LLM overhead
- Perfect for data processing, routing, validation

#### 1.2 Automatic A2A Compliance

The base classes will automatically handle:
- Set `protocolVersion` to "0.3.0"
- Set `preferredTransport` to "JSONRPC"
- Populate `url` from `HU_APP_URL` environment variable
- Validate all required AgentCard fields on startup
- Implement complete TaskState machine:
  - `submitted`, `working`, `input-required`, `completed`
  - `canceled`, `failed`, `rejected`, `auth-required`, `unknown`
- Add timestamps to all state transitions
- Handle task context (contextId) across interactions
- Implement required methods (`message/send`, `tasks/get`, `tasks/cancel`)

### Phase 2: Developer Tools (Week 2)

#### 2.1 Project Structure
```
a2a-template/
├── base/
│   ├── base_agent.py          # Enhanced BaseLLMAgentExecutor
│   ├── simple_agent.py         # BaseAgentExecutor for non-LLM
│   ├── compliance.py           # A2A compliance validation
│   └── errors.py               # Error handling utilities
├── utils/
│   ├── a2a_client.py          # Inter-agent communication
│   ├── task_manager.py        # Task lifecycle management
│   └── platform.py            # HealthUniverse utilities
├── examples/
│   ├── simple_agent.py         # 20-line minimal example
│   ├── llm_agent.py           # 30-line LLM example
│   ├── tool_agent.py          # 40-line tool-using agent
│   └── orchestrator_agent.py  # 50-line multi-agent coordinator
├── tools/
│   └── example_tools.py       # Template tool implementations
├── config/
│   └── agents.json            # Agent registry template
├── tests/
│   ├── test_compliance.py     # A2A compliance tests
│   └── test_agents.py         # Agent functionality tests
├── docs/
│   ├── README.md              # Architecture overview
│   ├── QUICKSTART.md          # Getting started guide
│   ├── DEPLOYMENT.md          # HealthUniverse deployment
│   └── MIGRATION.md           # Migration from existing agents
├── requirements.txt           # Core dependencies
├── .env.example              # Environment template
└── main.py                   # Deployment entry point
```

#### 2.2 Utility Modules

**A2A Client** (`utils/a2a_client.py`)
- Simplified inter-agent communication
- Automatic retry and timeout handling
- Agent discovery from registry

**Task Manager** (`utils/task_manager.py`)
- Handle task lifecycle automatically
- Heartbeat for long-running tasks
- Graceful cancellation support

**Platform Utils** (`utils/platform.py`)
- HU_APP_URL handling
- Agent ID extraction
- Health check endpoints
- Environment validation

**Compliance Validator** (`base/compliance.py`)
```python
validator = ComplianceValidator(agent)
report = validator.validate()
# Returns detailed compliance report with pass/fail and recommendations
```

### Phase 3: Example Implementations (Week 2)

#### 3.1 Simple Text Processor (20 lines)
```python
from base import BaseAgentExecutor

class TextProcessor(BaseAgentExecutor):
    def get_agent_name(self) -> str:
        return "Text Processor"
    
    async def process_message(self, message: str) -> str:
        # Simple text transformation
        return message.upper()

if __name__ == "__main__":
    agent = TextProcessor()
    agent.run()
```

#### 3.2 LLM Assistant (30 lines)
```python
from base import BaseLLMAgentExecutor
from tools import search_tool, calculate_tool

class Assistant(BaseLLMAgentExecutor):
    def get_agent_name(self) -> str:
        return "AI Assistant"
    
    def get_system_instruction(self) -> str:
        return "You are a helpful assistant that can search and calculate."
    
    def get_tools(self):
        return [search_tool, calculate_tool]

if __name__ == "__main__":
    agent = Assistant()
    agent.run()
```

#### 3.3 Multi-Agent Orchestrator (50 lines)
```python
from base import BaseLLMAgentExecutor
from utils import A2AAgentClient

class Orchestrator(BaseLLMAgentExecutor):
    def __init__(self):
        super().__init__()
        self.client = A2AAgentClient()
    
    def get_agent_name(self) -> str:
        return "Orchestrator"
    
    def get_system_instruction(self) -> str:
        return """Coordinate multiple agents to complete complex tasks.
        Available agents: analyzer, processor, validator"""
    
    def get_tools(self):
        return [
            self.create_agent_tool("analyzer"),
            self.create_agent_tool("processor"),
            self.create_agent_tool("validator")
        ]

if __name__ == "__main__":
    agent = Orchestrator()
    agent.run()
```

### Phase 4: Documentation & Testing (Week 3)

#### 4.1 Documentation

**README.md** - Architecture and overview
- System design
- A2A compliance features
- Platform integration
- Quick examples

**QUICKSTART.md** - Getting started in 5 minutes
1. Clone repository
2. Copy `.env.example` to `.env`
3. Add API keys
4. Run example agent
5. Deploy to HealthUniverse

**DEPLOYMENT.md** - HealthUniverse deployment guide
- Repository structure requirements
- Environment variables setup
- Deployment UI walkthrough
- Troubleshooting common issues

**MIGRATION.md** - Migrate existing agents
- Step-by-step migration guide
- Before/after code examples
- Breaking changes
- Compatibility notes

#### 4.2 Testing & Validation

**Compliance Testing**
```bash
python -m tests.test_compliance MyAgent
# Output: Detailed A2A compliance report
```

**Local Testing**
```bash
python main.py --test
# Runs agent in test mode with mock requests
```

**Integration Testing**
- Test inter-agent communication
- Validate task state transitions
- Check error handling
- Verify platform integration

## Resources Available

### From `adk-demo-pipeline-main.zip`:
- Working `BaseLLMAgentExecutor` implementation
- Multiple agent examples (chunk, grep, keyword, summarize, orchestrator)
- A2A client implementation
- Tool patterns and integrations
- Google ADK integration

### From `a2a-agent-template-main.zip`:
- Simple, clean template structure
- Minimal agent implementation
- Basic A2A setup

## Success Criteria

✅ **Compliance**: All agents automatically pass A2A specification validation  
✅ **Simplicity**: New agent creation requires < 50 lines of code  
✅ **Reliability**: Zero protocol-related errors in production  
✅ **Compatibility**: Existing agents can migrate with minimal changes  
✅ **Platform Ready**: Works immediately on HealthUniverse  
✅ **Zero Config**: No manual setup required post-deployment  

## Key Improvements Over Current Implementation

1. **Automatic Protocol Compliance**
   - Current: Developers must understand A2A spec
   - New: Base class handles everything automatically

2. **Error Handling**
   - Current: Inconsistent error handling across agents
   - New: Automatic error mapping to A2A error codes

3. **Platform Integration**
   - Current: Manual URL and environment setup
   - New: Automatic detection and configuration

4. **Developer Experience**
   - Current: 200+ lines for basic agent
   - New: < 50 lines for full-featured agent

5. **Multi-Provider Support**
   - Current: Primarily Google-focused
   - New: Auto-detect Google/OpenAI/Anthropic

## Implementation Timeline

- **Week 1**: Core infrastructure (base classes, compliance)
- **Week 2**: Developer tools and examples
- **Week 3**: Documentation and testing
- **Week 4**: Community feedback and iteration

## Next Steps

1. Review and approve implementation plan
2. Set up development environment
3. Begin Phase 1 implementation
4. Create initial example agents
5. Test on HealthUniverse platform
6. Gather feedback from early adopters
7. Iterate based on real-world usage

## Questions for Discussion

1. Should we support both LLM and non-LLM agents in the same base class, or keep them separate?
2. What additional agent patterns should we support out of the box?
3. How can we make debugging and error messages more helpful?
4. Should we include pre-built tools for common operations?
5. What level of customization should be exposed vs. handled automatically?

## References

- [A2A Protocol Specification v0.3.0](./Specification%20-%20Agent2Agent%20(A2A)%20Protocol.md)
- [HealthUniverse Platform Documentation](https://www.healthuniverse.com/docs)
- [Google ADK Documentation](https://cloud.google.com/adk/docs)

---

This template repository will dramatically simplify A2A agent development while ensuring 100% protocol compliance and seamless HealthUniverse platform integration.