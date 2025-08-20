# Fix #5: grep_agent.py - Remove JSON Detection and Fix Tool Return Types

## Priority: CRITICAL - Major Violation
**Depends on: Fix #1 (base.py) and Fix #2 (simple_orchestrator) must be completed first**

## Current Violations (from Issue #22)

### Agent Violations (lines 95-138):
```python
async def process_message(self, message: str) -> str:
    try:
        # VIOLATION: Detects JSON
        data = json.loads(message)
        
        # VIOLATION: Routes based on JSON fields
        if "patterns" in data and ("document_content" in data or "file_content" in data):
            # VIOLATION: Directly calls tool
            from tools.grep_tools import search_medical_patterns
            result = search_medical_patterns(...)
            return result  # VIOLATION: Returns JSON string
        else:
            return message
            
    except json.JSONDecodeError:
        return message
```

### Tool Violations (tools/grep_tools.py):
- Line 90: `return json.dumps(results)`
- Line 103: `return json.dumps(results)`
- Line 184: `return json.dumps(results)`
- Line 308: `return json.dumps(results)`

## Required Changes

### 1. Fix grep_agent.py process_message
Replace entire process_message with:
```python
async def process_message(self, message: str) -> str:
    """
    Process incoming messages for LLM/ADK handling.
    NO JSON detection, NO custom routing.
    """
    # Simply return the message for LLM/ADK to process
    # The LLM will understand the request and call tools as needed
    return message
```

That's it! Delete ALL the JSON detection logic.

### 2. Fix tools/grep_tools.py
Change all functions to return dicts:

```python
# WRONG - Current
def search_medical_patterns(...) -> str:
    results = {
        "file_path": file_path,
        "patterns_searched": patterns,
        "total_matches": total_matches,
        "pattern_results": pattern_results,
        "errors": results.get("errors", [])
    }
    return json.dumps(results)  # BAD

# RIGHT - Fixed
def search_medical_patterns(...) -> dict:
    results = {
        "file_path": file_path,
        "patterns_searched": patterns,
        "total_matches": total_matches,
        "pattern_results": pattern_results,
        "errors": results.get("errors", [])
    }
    return results  # Return dict directly
```

Apply this change to ALL functions in grep_tools.py.

### 3. Update get_system_instruction
Make sure the LLM knows how to use the tools:
```python
def get_system_instruction(self) -> str:
    return """You are a medical document search specialist using grep-like pattern matching.

When asked to search a document:
1. Use search_medical_patterns tool with appropriate patterns
2. The tool needs patterns as a list and document content as text
3. Return the search results in a clear, readable format

You have access to these tools:
- search_medical_patterns: Search for patterns in medical documents
- validate_and_fix_patterns: Validate regex patterns
- search_with_error_recovery: Search with fallback options
- analyze_search_performance: Analyze search effectiveness

Always explain what patterns you're searching for and why."""
```

## Test Requirements

### Create: `tests/test_grep_compliance.py`
```python
"""
Test grep_agent compliance with A2A specification.
Verifies orchestrator → grep → orchestrator communication.
"""
import os
import sys
import json
import asyncio
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Enable verbose logging
os.environ["SHOW_AGENT_CALLS"] = "true"

async def test_grep_no_json_detection():
    """Verify grep doesn't detect JSON in process_message."""
    from examples.pipeline.grep_agent import GrepAgent
    
    agent = GrepAgent()
    
    # Test 1: JSON message should NOT trigger special handling
    json_message = json.dumps({
        "patterns": ["diabetes", "insulin"],
        "document_content": "Patient has diabetes"
    })
    
    result = await agent.process_message(json_message)
    
    # After fix, should return the message unchanged
    assert result == json_message, "JSON should not be detected or handled specially"
    print("✅ JSON message not detected")
    
    # Test 2: Regular text should also pass through
    text_message = "Search for diabetes in the document"
    result = await agent.process_message(text_message)
    assert result == text_message, "Text should pass through unchanged"
    print("✅ Text message passes through")

async def test_tool_returns_dict():
    """Verify tools return dicts not JSON strings."""
    from tools.grep_tools import search_medical_patterns
    
    # Call tool directly
    result = search_medical_patterns(
        file_path="test.txt",
        patterns_json='["diabetes", "insulin"]',
        case_sensitive="false",
        max_matches="10",
        context_lines="2",
        file_content="Patient has diabetes requiring insulin"
    )
    
    # After fix, should return dict not string
    assert isinstance(result, dict), f"Tool should return dict, got {type(result)}"
    print("✅ Tool returns dict not JSON string")

async def test_orchestrator_grep_communication():
    """Test actual communication between orchestrator and grep."""
    print("\n" + "="*60)
    print("TEST: Orchestrator → Grep → Orchestrator")
    print("="*60)
    
    # Start grep agent
    grep_process = subprocess.Popen(
        ["python", "examples/pipeline/grep_agent.py"],
        env={**os.environ, "PORT": "8002"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    time.sleep(3)  # Let agent start
    
    try:
        from utils.a2a_client import A2AAgentClient
        
        async with A2AAgentClient() as client:
            # Send natural language request (NOT JSON)
            message = """
            Search this medical document for mentions of diabetes and insulin:
            
            Patient: Eleanor Richardson
            Diagnosis: Type 2 Diabetes
            Treatment: Insulin therapy started
            """
            
            print(f"📤 Sending: {message[:50]}...")
            response = await client.call_agent("http://localhost:8002", message)
            print(f"📥 Response: {response[:200]}...")
            
            # Response should be natural language with search results
            assert "diabetes" in response.lower() or "found" in response.lower()
            print("✅ Grep agent responds properly to natural language")
    
    finally:
        grep_process.terminate()
        
    return True

async def test_pipeline_through_grep():
    """Test pipeline: orchestrator → keyword → grep."""
    if "--pipeline" not in sys.argv:
        print("Skipping pipeline test (use --pipeline to run)")
        return True
        
    print("\n" + "="*60)
    print("TEST: Pipeline through Grep")
    print("="*60)
    
    processes = []
    
    try:
        # Start agents
        processes.append(subprocess.Popen(
            ["python", "examples/pipeline/simple_orchestrator_agent.py"],
            env={**os.environ, "PORT": "8000"}
        ))
        processes.append(subprocess.Popen(
            ["python", "examples/pipeline/keyword_agent.py"],
            env={**os.environ, "PORT": "8001"}
        ))
        processes.append(subprocess.Popen(
            ["python", "examples/pipeline/grep_agent.py"],
            env={**os.environ, "PORT": "8002"}
        ))
        
        time.sleep(5)  # Let agents start
        
        from utils.a2a_client import A2AAgentClient
        
        async with A2AAgentClient() as client:
            response = await client.call_agent(
                "http://localhost:8000",
                "Search for diabetes in: Patient has diabetes requiring insulin"
            )
            
            print(f"Pipeline response: {response[:300]}...")
            print("✅ Pipeline works through grep agent")
    
    finally:
        for p in processes:
            p.terminate()
    
    return True

async def main():
    """Run all grep compliance tests."""
    print("\n" + "="*70)
    print("GREP AGENT A2A COMPLIANCE TESTS")
    print("="*70)
    
    # Test 1: No JSON detection
    await test_grep_no_json_detection()
    
    # Test 2: Tools return dicts
    await test_tool_returns_dict()
    
    # Test 3: Orchestrator communication
    await test_orchestrator_grep_communication()
    
    # Test 4: Pipeline (optional)
    await test_pipeline_through_grep()
    
    print("\n" + "="*70)
    print("✅ ALL GREP TESTS PASSED")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
```

## Test Command
```bash
# Basic compliance test
python tests/test_grep_compliance.py

# Test with full pipeline
SHOW_AGENT_CALLS=true python tests/test_grep_compliance.py --pipeline
```

## Expected Logs After Fix
```
📨 INCOMING REQUEST TO: Grep Agent
📝 MESSAGE: Search this medical document for mentions...
[No JSON detection logs]
[ADK/LLM decides to call search_medical_patterns tool]
Tool called with proper parameters
Tool returns dict (not JSON string)
Response formatted by LLM
📥 RESPONSE: Found 2 mentions of diabetes...
```

## Branch Name
`fix-5-grep-compliance`

## PR Checklist
- [ ] All JSON detection removed from process_message
- [ ] process_message just returns the message unchanged
- [ ] All tool functions return dicts not JSON strings
- [ ] No `json.dumps()` calls in tools
- [ ] Test shows no JSON detection occurring
- [ ] Orchestrator can communicate using natural language
- [ ] Logs show proper A2A message flow

## Dependencies
- **MUST COMPLETE FIRST**: 
  - Fix #1 (base.py) - Foundation
  - Fix #2 (simple_orchestrator) - To test communication

## Common Pitfalls to Avoid
1. Don't try to "help" by parsing the message
2. Don't check message format at all
3. Let the LLM/ADK handle everything
4. Tools should return Python objects, not strings

## Expected Outcome
After this fix:
1. Grep agent accepts any message format
2. LLM understands requests and calls tools appropriately  
3. Tools return proper Python dicts
4. Agent-to-agent communication works via A2A protocol
5. No custom JSON routing

## References
- Issue #22: A2A Specification Compliance Audit (grep violations)
- Fix #1: base.py (prerequisite)
- Fix #2: simple_orchestrator (for testing)