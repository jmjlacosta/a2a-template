# Fix #1: base.py - Remove Custom JSON Routing Logic

## Priority: CRITICAL - Foundation Issue
**This MUST be fixed first before any other agent fixes**

## Current Violations (from Issue #22)

### Lines 150-189: Custom Message Format Detection
```python
# VIOLATION: Detects JSON and routes differently
is_json_request = False
try:
    json.loads(message)
    is_json_request = True
    self.logger.info("Detected JSON message - likely agent-to-agent communication")
except (json.JSONDecodeError, TypeError) as e:
    self.logger.debug(f"Not a JSON message: {e}")
    pass

# VIOLATION: Routes based on message type
if tools and len(tools) > 0 and is_json_request:
    response = await self._execute_tools_directly(message, updater)
elif tools and len(tools) > 0:
    await self._execute_with_tools(message, updater, task.id)
else:
    response = await self._execute_with_llm_no_tools(message, updater)
```

### Lines 212-243: Custom Tool Execution Method
```python
async def _execute_tools_directly(self, message: str, updater: TaskUpdater) -> str:
    """Execute tools directly without LLM for agent-to-agent communication."""
    # VIOLATION: This entire method bypasses A2A SDK
```

## Required Changes

### 1. Remove Custom Routing Logic
Delete lines 150-189 and replace with:
```python
# Let SDK handle execution based on agent configuration
tools = self.get_tools()
if tools:
    # Use Google ADK with tools - handles ALL messages the same way
    await self._execute_with_tools(message, updater, task.id)
else:
    # Use LLM without tools
    response = await self._execute_with_llm_no_tools(message, updater)
    await updater.add_artifact(
        [Part(root=TextPart(text=response))],
        name="response"
    )

await updater.complete()
```

### 2. Delete _execute_tools_directly Method
Remove the entire method (lines 212-243) - it violates A2A principles

### 3. Simplify execute Method
The execute method should:
1. Extract message from context
2. Create/get task
3. Create TaskUpdater
4. Route to ADK (with tools) or LLM (without tools)
5. Complete task

NO JSON detection, NO custom routing

## Test Requirements

### Create: `tests/test_base_compliance.py`
```python
"""
Test that base.py properly routes messages without JSON detection.
"""
import os
import sys
import json
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from base import A2AAgent
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message
from a2a.types import Message, Part, TextPart

class TestAgent(A2AAgent):
    """Simple test agent to verify base routing."""
    
    def get_agent_name(self) -> str:
        return "Test Agent"
    
    def get_agent_description(self) -> str:
        return "Agent for testing base.py compliance"
    
    async def process_message(self, message: str) -> str:
        # Should receive ALL messages, regardless of format
        return f"Processed: {message}"
    
    def get_tools(self):
        # No tools for this test
        return []

async def test_json_not_detected():
    """Verify JSON messages are NOT routed differently."""
    agent = TestAgent()
    
    # Test with JSON message
    json_message = json.dumps({"test": "data", "key": "value"})
    
    # Create context with JSON message
    context = RequestContext(
        message=Message(
            parts=[Part(root=TextPart(text=json_message))]
        )
    )
    
    event_queue = EventQueue()
    
    # Execute should NOT detect JSON and route differently
    await agent.execute(context, event_queue)
    
    # Check that process_message was called normally
    # (will need to add logging to verify)
    print("✅ JSON message processed without special routing")

async def test_text_message():
    """Verify text messages work normally."""
    agent = TestAgent()
    
    text_message = "This is a regular text message"
    
    context = RequestContext(
        message=Message(
            parts=[Part(root=TextPart(text=text_message))]
        )
    )
    
    event_queue = EventQueue()
    await agent.execute(context, event_queue)
    
    print("✅ Text message processed normally")

if __name__ == "__main__":
    print("Testing base.py A2A compliance...")
    print("-" * 50)
    
    asyncio.run(test_json_not_detected())
    asyncio.run(test_text_message())
    
    print("-" * 50)
    print("✅ All tests passed - base.py is compliant")
```

## Test Command
```bash
# Run compliance test
python tests/test_base_compliance.py

# With verbose logging to see routing decisions
SHOW_AGENT_CALLS=true python tests/test_base_compliance.py
```

## Branch Name
`fix-1-base-compliance`

## PR Checklist
- [ ] All JSON detection code removed
- [ ] _execute_tools_directly method deleted
- [ ] All messages routed the same way (no format detection)
- [ ] Test passes showing JSON and text handled identically
- [ ] No custom "optimizations" for agent-to-agent communication
- [ ] Comments updated to reflect proper A2A compliance

## Expected Outcome
After this fix:
1. ALL messages go through the same routing path
2. The ADK/LLM decides how to handle messages, not our code
3. Agent-to-agent communication works through proper A2A protocol
4. No "shortcuts" or "optimizations" that break compliance

## Impact on Other Agents
⚠️ **WARNING**: This change will temporarily break grep_agent and chunk_agent which expect the custom routing. They will be fixed in subsequent issues.

## Dependencies
None - this is the foundation fix

## References
- Issue #22: A2A Specification Compliance Audit
- A2A Specification Section 1.2: "Opaque Execution" principle
- A2A Specification Section 6.5: Part Union Type (no routing based on type)