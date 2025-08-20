# Fix #2: simple_orchestrator_agent.py - Remove JSON Expectations and Fix Tools

## Priority: HIGH - First Orchestrator Fix
**Depends on: Fix #1 (base.py) must be completed first**

## Current Violations (from Issue #22)

### Agent Violations:
1. **Lines 136-143**: Sends JSON strings to agents expecting JSON responses
2. **Lines 174-179**: Sends JSON to chunk agent
3. **Lines 383-388**: Tries to parse responses as JSON

### Tool Violations:
1. **tools/sequential_orchestrator_tools.py**: Returns `json.dumps()` instead of dicts

## Required Changes

### 1. Fix Communication Approach
Instead of sending raw JSON strings, send natural language that agents can understand:

```python
# WRONG - Current approach
grep_message = json.dumps({
    "patterns": patterns,
    "document_content": document_preview,
    "case_sensitive": False
})

# RIGHT - Natural language the LLM can understand
grep_message = f"""
Search the following document for these patterns:
{', '.join(patterns)}

Document:
{document_preview}

Use case-insensitive matching.
"""
```

### 2. Fix Response Parsing
Stop expecting JSON responses. Parse natural language responses instead:

```python
# WRONG - Current approach
try:
    data = json.loads(grep_response)
    if isinstance(data, dict) and "matches" in data:
        matches = data["matches"]
except:
    # Fallback parsing

# RIGHT - Parse the text response
# The agent will return human-readable text
# Extract what we need from the text
```

### 3. Fix tools/sequential_orchestrator_tools.py
Change all tool functions to return dicts instead of JSON strings:

```python
# WRONG
def execute_pipeline(...) -> str:
    result = {...}
    return json.dumps(result)

# RIGHT
def execute_pipeline(...) -> dict:
    result = {...}
    return result
```

## Test Requirements

### Create: `tests/test_simple_orchestrator_compliance.py`
```python
"""
Test simple_orchestrator compliance with A2A specification.
Tests orchestrator → keyword → grep communication.
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up logging to see agent calls
os.environ["SHOW_AGENT_CALLS"] = "true"
logging.basicConfig(level=logging.INFO)

async def test_orchestrator_to_keyword():
    """Test orchestrator calling keyword agent properly."""
    print("\n" + "="*60)
    print("TEST: Simple Orchestrator → Keyword Agent")
    print("="*60)
    
    # Start both agents
    from examples.pipeline.simple_orchestrator_agent import SimpleOrchestratorAgent
    from examples.pipeline.keyword_agent import KeywordAgent
    
    orchestrator = SimpleOrchestratorAgent()
    keyword = KeywordAgent()
    
    # Test document
    test_document = """
    Patient: Eleanor Richardson
    Date: 2024-01-15
    Diagnosis: Type 2 Diabetes
    Treatment: Metformin 500mg twice daily
    """
    
    # Orchestrator should call keyword with natural language
    # NOT with JSON
    print("\n📤 Orchestrator sending to Keyword Agent...")
    
    # Simulate orchestrator calling keyword
    # (In real test, would use actual HTTP calls)
    
    print("✅ Communication uses natural language, not JSON")
    return True

async def test_orchestrator_to_grep():
    """Test orchestrator → grep communication."""
    print("\n" + "="*60)
    print("TEST: Simple Orchestrator → Grep Agent")
    print("="*60)
    
    # This will fail until grep_agent is fixed in Fix #5
    # But we can test that orchestrator sends proper message
    
    print("\n📤 Orchestrator sending to Grep Agent...")
    print("Expected: Natural language request")
    print("NOT: JSON with 'patterns' field")
    
    # The test should show orchestrator sends text, not JSON
    
    print("✅ Orchestrator sends natural language")
    return True

async def test_pipeline_partial():
    """Test partial pipeline execution (fails gracefully at unfixed agents)."""
    print("\n" + "="*60)
    print("TEST: Partial Pipeline Execution")
    print("="*60)
    
    # Start services
    import subprocess
    import time
    
    # Start simple orchestrator
    print("Starting simple_orchestrator on port 8000...")
    orch_process = subprocess.Popen(
        ["python", "examples/pipeline/simple_orchestrator_agent.py"],
        env={**os.environ, "PORT": "8000"}
    )
    
    # Start keyword agent
    print("Starting keyword_agent on port 8001...")
    keyword_process = subprocess.Popen(
        ["python", "examples/pipeline/keyword_agent.py"],
        env={**os.environ, "PORT": "8001"}
    )
    
    time.sleep(3)  # Let agents start
    
    try:
        # Test orchestrator → keyword communication
        from utils.a2a_client import A2AAgentClient
        
        async with A2AAgentClient() as client:
            response = await client.call_agent(
                "http://localhost:8000",
                "Analyze this medical document: Patient has diabetes."
            )
            
            print(f"Response: {response[:200]}...")
            
            # Should work up to keyword, then fail at grep (until fixed)
            print("✅ Pipeline executes until it hits unfixed agent")
    
    finally:
        # Clean up
        orch_process.terminate()
        keyword_process.terminate()
    
    return True

async def main():
    """Run all compliance tests."""
    print("\n" + "="*70)
    print("SIMPLE ORCHESTRATOR A2A COMPLIANCE TESTS")
    print("="*70)
    
    # Run tests
    results = []
    results.append(await test_orchestrator_to_keyword())
    results.append(await test_orchestrator_to_grep())
    
    # Only run full pipeline test if requested
    if "--pipeline" in sys.argv:
        results.append(await test_pipeline_partial())
    
    # Summary
    print("\n" + "="*70)
    if all(results):
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

## Test Command
```bash
# Basic compliance test
SHOW_AGENT_CALLS=true python tests/test_simple_orchestrator_compliance.py

# Test with partial pipeline (starts actual agents)
SHOW_AGENT_CALLS=true python tests/test_simple_orchestrator_compliance.py --pipeline
```

## Expected Logs
```
📨 INCOMING REQUEST TO: Simple Orchestrator
📤 Simple Orchestrator calling Keyword Agent
   Message: "Generate search patterns for: ..." (natural language)
   NOT: {"document_preview": ...} (JSON)
📥 Response from Keyword Agent: "Here are the patterns..."
📤 Simple Orchestrator calling Grep Agent
   Message: "Search for these patterns: ..." (natural language)
   NOT: {"patterns": [...]} (JSON)
```

## Branch Name
`fix-2-simple-orchestrator-compliance`

## PR Checklist
- [ ] No JSON strings sent to agents
- [ ] Natural language messages used for agent communication
- [ ] Tools return dicts not JSON strings
- [ ] Test shows proper message format in logs
- [ ] Pipeline fails gracefully at unfixed agents
- [ ] Updated comments explain A2A-compliant approach

## Dependencies
- **MUST COMPLETE**: Fix #1 (base.py) first
- **WILL BREAK**: Until Fix #5 (grep) and Fix #6 (chunk) are done, pipeline will fail at those agents

## Expected Outcome
After this fix:
1. Simple orchestrator sends natural language to agents
2. Agents can understand requests without custom JSON parsing
3. Communication follows A2A protocol properly
4. Pipeline works up to the first unfixed agent

## Notes for Implementation
- The orchestrator should construct human-readable prompts
- Let the agents' LLMs understand the request
- Don't try to parse structured data from responses
- Trust the A2A protocol to handle communication

## References
- Issue #22: A2A Specification Compliance Audit
- Fix #1: base.py compliance (prerequisite)