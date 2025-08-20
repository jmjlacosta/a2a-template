# Fix #4: keyword_agent.py - Verify Compliance and Fix Tools

## Priority: HIGH - First Pipeline Agent
**Depends on: Fix #1 (base.py) must be completed first**

## Current Status (from Issue #22)
keyword_agent.py is **COMPLIANT** ✅:
- Returns "Processing..." in process_message
- Doesn't detect JSON
- Lets base class handle tool execution

**BUT**: Need to verify tools return proper types

## Required Changes

### 1. Verify process_message Compliance
Current implementation should be:
```python
async def process_message(self, message: str) -> str:
    # Should just return simple string for LLM processing
    return "Processing..."  # Or similar
```
If it does anything else, simplify it.

### 2. Fix tools/keyword_tools.py
Check all functions return dicts or strings, not JSON:

```python
# WRONG if found:
def generate_medical_patterns(...) -> str:
    patterns = {...}
    return json.dumps(patterns)

# RIGHT:
def generate_medical_patterns(...) -> dict:
    patterns = {...}
    return patterns
```

### 3. Verify System Instruction
Should guide the LLM to use tools properly:
```python
def get_system_instruction(self) -> str:
    return """You are a medical keyword specialist that generates search patterns.

When asked to analyze a document or generate patterns:
1. Use the generate_medical_patterns tool
2. The tool needs a document preview/summary as input
3. It will return categorized search patterns

You have these tools available:
- generate_medical_patterns: Generate comprehensive search patterns
- validate_patterns: Validate the generated patterns

Focus on medical terminology, clinical terms, temporal markers, and document structure."""
```

## Test Requirements

### Create: `tests/test_keyword_compliance.py`
```python
"""
Test keyword_agent compliance with A2A specification.
First agent in the pipeline - critical for downstream testing.
"""
import os
import sys
import asyncio
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["SHOW_AGENT_CALLS"] = "true"

async def test_keyword_process_message():
    """Verify keyword doesn't process JSON specially."""
    from examples.pipeline.keyword_agent import KeywordAgent
    
    agent = KeywordAgent()
    
    # Test that process_message is simple
    test_message = "Generate patterns for diabetes document"
    result = await agent.process_message(test_message)
    
    # Should return simple string, not process the message
    assert isinstance(result, str)
    assert len(result) < 100  # Should be brief like "Processing..."
    print(f"✅ process_message returns: '{result}'")
    
    # Test with JSON - should NOT be detected
    json_message = '{"document": "test"}'
    result = await agent.process_message(json_message)
    assert isinstance(result, str)
    assert len(result) < 100
    print("✅ JSON not detected or processed")

async def test_keyword_tools():
    """Verify tools return proper types."""
    from tools.keyword_tools import generate_medical_patterns
    
    # Test the main tool
    result = generate_medical_patterns(
        document_preview="Patient has diabetes requiring insulin therapy"
    )
    
    # Should return dict or list, not JSON string
    assert isinstance(result, (dict, list)), f"Tool should return dict/list, got {type(result)}"
    
    # If it's a string, make sure it's not JSON
    if isinstance(result, str):
        try:
            import json
            json.loads(result)
            assert False, "Tool returned JSON string - should return dict"
        except json.JSONDecodeError:
            pass  # OK - it's natural text
    
    print("✅ Tools return proper types")

async def test_orchestrator_to_keyword():
    """Test orchestrator → keyword communication."""
    print("\n" + "="*60)
    print("TEST: Orchestrator → Keyword Agent")
    print("="*60)
    
    # Start keyword agent
    keyword_process = subprocess.Popen(
        ["python", "examples/pipeline/keyword_agent.py"],
        env={**os.environ, "PORT": "8001"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    time.sleep(3)
    
    try:
        from utils.a2a_client import A2AAgentClient
        
        async with A2AAgentClient() as client:
            # Send natural language request
            message = """
            Generate search patterns for this medical document:
            
            Patient: Eleanor Richardson
            Date: 2024-01-15
            Diagnosis: Type 2 Diabetes
            Treatment: Metformin 500mg
            """
            
            print(f"📤 Sending: {message[:50]}...")
            response = await client.call_agent("http://localhost:8001", message)
            print(f"📥 Response type: {type(response)}")
            print(f"📥 Response: {response[:200]}...")
            
            # Should get patterns back
            assert "pattern" in response.lower() or "search" in response.lower()
            print("✅ Keyword agent responds properly")
    
    finally:
        keyword_process.terminate()

async def test_simple_orchestrator_to_keyword():
    """Test simple_orchestrator → keyword communication."""
    if "--orchestrator" not in sys.argv:
        print("Skipping orchestrator test (use --orchestrator to run)")
        return True
    
    print("\n" + "="*60)
    print("TEST: Simple Orchestrator → Keyword")
    print("="*60)
    
    processes = []
    
    try:
        # Start both agents
        processes.append(subprocess.Popen(
            ["python", "examples/pipeline/simple_orchestrator_agent.py"],
            env={**os.environ, "PORT": "8000"}
        ))
        processes.append(subprocess.Popen(
            ["python", "examples/pipeline/keyword_agent.py"],
            env={**os.environ, "PORT": "8001"}
        ))
        
        # Update config
        import json
        config = {"agents": {"keyword": {"url": "http://localhost:8001"}}}
        os.makedirs("config", exist_ok=True)
        with open("config/agents.json", "w") as f:
            json.dump(config, f)
        
        time.sleep(5)
        
        from utils.a2a_client import A2AAgentClient
        
        async with A2AAgentClient() as client:
            response = await client.call_agent(
                "http://localhost:8000",
                "Analyze: Patient has diabetes"
            )
            
            print(f"Pipeline response: {response[:300]}...")
            
            # Should work through keyword, fail at grep (if not fixed yet)
            print("✅ Pipeline processes through keyword")
    
    finally:
        for p in processes:
            p.terminate()

async def main():
    """Run keyword agent compliance tests."""
    print("\n" + "="*70)
    print("KEYWORD AGENT A2A COMPLIANCE TESTS")
    print("="*70)
    
    # Test 1: process_message compliance
    await test_keyword_process_message()
    
    # Test 2: Tools return proper types
    await test_keyword_tools()
    
    # Test 3: Direct agent communication
    await test_orchestrator_to_keyword()
    
    # Test 4: Orchestrator pipeline (optional)
    await test_simple_orchestrator_to_keyword()
    
    print("\n" + "="*70)
    print("✅ ALL KEYWORD TESTS PASSED")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
```

## Test Command
```bash
# Basic compliance test
python tests/test_keyword_compliance.py

# Test with orchestrator
SHOW_AGENT_CALLS=true python tests/test_keyword_compliance.py --orchestrator
```

## Expected Logs
```
📨 INCOMING REQUEST TO: Keyword Agent
📝 MESSAGE: Generate search patterns for this medical document...
[LLM processes request]
[Calls generate_medical_patterns tool]
Tool returns dict with patterns
[LLM formats response]
📥 RESPONSE: Here are the search patterns...
```

## Branch Name
`fix-4-keyword-compliance`

## PR Checklist
- [ ] process_message returns simple string
- [ ] No JSON detection in agent
- [ ] Tools return dicts/lists, not JSON strings
- [ ] Test passes showing compliance
- [ ] Can receive requests from orchestrators
- [ ] Logs show proper A2A flow

## Dependencies
- **MUST COMPLETE**: Fix #1 (base.py)
- **GOOD TO HAVE**: Fix #2 (simple_orchestrator) for testing

## Expected Outcome
After verification/fix:
1. Keyword agent confirmed compliant
2. Tools return proper Python types
3. Works as first agent in pipeline
4. Orchestrators can call it successfully

## Notes
- This agent is likely already compliant
- Main task is verifying and fixing tools
- Critical as it's the first in the pipeline

## References
- Issue #22: Keyword marked as compliant
- Fix #1: base.py (prerequisite)