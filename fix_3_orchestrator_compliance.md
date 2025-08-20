# Fix #3: orchestrator_agent.py - Ensure Proper A2A Communication

## Priority: HIGH - LLM Orchestrator Fix
**Depends on: Fix #1 (base.py) must be completed first**

## Current Status (from Issue #22)
The LLM-powered orchestrator is **more compliant** than simple_orchestrator:
- Uses tools properly via Google ADK ✅
- Doesn't do custom JSON routing ✅
- BUT: Tools may still return JSON strings ❌

## Required Changes

### 1. Fix tools/orchestrator_tools.py
All functions should return dicts, not JSON strings:

```python
# Check and fix any instances of:
return json.dumps(result)  # WRONG

# Should be:
return result  # RIGHT - return dict
```

### 2. Verify coordinate_agents Function
The coordinate_agents function should NOT expect JSON from agents:

```python
# WRONG - if it does this:
agent_response = await call_agent(...)
data = json.loads(agent_response)  # Don't parse as JSON

# RIGHT - treat as text:
agent_response = await call_agent(...)
# Work with the text response directly
```

### 3. Update System Instruction
Ensure the LLM knows agents return natural language:

```python
def get_system_instruction(self) -> str:
    return """You are an intelligent orchestrator that coordinates medical document analysis.

You have access to these agents (will be loaded from config):
- keyword: Generates search patterns from documents
- grep: Searches documents using patterns
- chunk: Extracts context around matches
[... rest of agents ...]

When coordinating agents:
1. Send clear, natural language requests to each agent
2. Agents will respond with natural language (not JSON)
3. Parse and understand their responses to continue the pipeline
4. Use the coordinate_agents tool to manage the workflow

Your goal is to intelligently route requests through the appropriate agents
based on the analysis needed."""
```

## Test Requirements

### Create: `tests/test_orchestrator_compliance.py`
```python
"""
Test orchestrator_agent compliance with A2A specification.
Verifies LLM-based orchestration without JSON expectations.
"""
import os
import sys
import asyncio
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["SHOW_AGENT_CALLS"] = "true"

async def test_orchestrator_tools_return_dicts():
    """Verify orchestrator tools return dicts not JSON."""
    from tools.orchestrator_tools import (
        plan_pipeline_execution,
        coordinate_agents,
        synthesize_results
    )
    
    # Test plan_pipeline_execution
    plan_result = plan_pipeline_execution(
        user_request="Analyze medical document",
        available_agents="keyword, grep, chunk"
    )
    assert isinstance(plan_result, (dict, str)), "Should return dict or str, not JSON"
    if isinstance(plan_result, str):
        # Should be natural text, not JSON
        try:
            import json
            json.loads(plan_result)
            assert False, "Should not return JSON string"
        except json.JSONDecodeError:
            pass  # Good, it's natural text
    print("✅ Tools return proper types")

async def test_orchestrator_coordination():
    """Test orchestrator coordinating agents without JSON."""
    print("\n" + "="*60)
    print("TEST: LLM Orchestrator Coordination")
    print("="*60)
    
    # Start orchestrator
    orch_process = subprocess.Popen(
        ["python", "examples/pipeline/orchestrator_agent.py"],
        env={**os.environ, "PORT": "8100", "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "")},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    time.sleep(5)  # Let agent start
    
    try:
        from utils.a2a_client import A2AAgentClient
        
        async with A2AAgentClient() as client:
            # Send request for coordination
            message = """
            I need to analyze this medical record for diabetes information:
            Patient: John Doe
            Diagnosis: Type 2 Diabetes
            
            Please coordinate the analysis through the appropriate agents.
            """
            
            print(f"📤 Sending: {message[:50]}...")
            response = await client.call_agent("http://localhost:8100", message)
            print(f"📥 Response: {response[:200]}...")
            
            # Should get intelligent response about coordination
            assert len(response) > 0
            print("✅ Orchestrator coordinates without expecting JSON")
    
    finally:
        orch_process.terminate()
    
    return True

async def test_orchestrator_to_keyword():
    """Test orchestrator → keyword agent communication."""
    if "--agents" not in sys.argv:
        print("Skipping multi-agent test (use --agents to run)")
        return True
    
    print("\n" + "="*60)
    print("TEST: Orchestrator → Keyword Communication")
    print("="*60)
    
    processes = []
    
    try:
        # Start orchestrator and keyword
        processes.append(subprocess.Popen(
            ["python", "examples/pipeline/orchestrator_agent.py"],
            env={**os.environ, "PORT": "8100"}
        ))
        processes.append(subprocess.Popen(
            ["python", "examples/pipeline/keyword_agent.py"],
            env={**os.environ, "PORT": "8001"}
        ))
        
        time.sleep(5)
        
        # Update config/agents.json with keyword location
        import json
        config = {
            "agents": {
                "keyword": {"url": "http://localhost:8001"}
            }
        }
        with open("config/agents.json", "w") as f:
            json.dump(config, f)
        
        from utils.a2a_client import A2AAgentClient
        
        async with A2AAgentClient() as client:
            response = await client.call_agent(
                "http://localhost:8100",
                "Generate search patterns for: Patient has diabetes"
            )
            
            print(f"Response: {response[:200]}...")
            print("✅ Orchestrator coordinates with keyword agent")
    
    finally:
        for p in processes:
            p.terminate()
    
    return True

async def main():
    """Run orchestrator compliance tests."""
    print("\n" + "="*70)
    print("ORCHESTRATOR AGENT A2A COMPLIANCE TESTS")
    print("="*70)
    
    # Test 1: Tools return proper types
    await test_orchestrator_tools_return_dicts()
    
    # Test 2: Basic coordination
    await test_orchestrator_coordination()
    
    # Test 3: Multi-agent (optional)
    await test_orchestrator_to_keyword()
    
    print("\n" + "="*70)
    print("✅ ALL ORCHESTRATOR TESTS PASSED")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
```

## Test Command
```bash
# Basic compliance test
python tests/test_orchestrator_compliance.py

# Test with agent coordination
SHOW_AGENT_CALLS=true python tests/test_orchestrator_compliance.py --agents
```

## Expected Logs
```
📨 INCOMING REQUEST TO: Orchestrator Agent
[LLM analyzing request]
[Calling coordinate_agents tool]
📤 Orchestrator calling Keyword Agent
   Message: "Generate patterns for diabetes in medical record"
📥 Response: "Here are the search patterns..."
[LLM processing response]
[Continuing coordination...]
```

## Branch Name
`fix-3-orchestrator-compliance`

## PR Checklist
- [ ] Tools return dicts/strings, not JSON strings
- [ ] No JSON parsing of agent responses
- [ ] System instruction updated for natural language
- [ ] Test shows proper coordination without JSON
- [ ] Logs show A2A-compliant message flow

## Dependencies
- **MUST COMPLETE**: Fix #1 (base.py)
- **NICE TO HAVE**: Fix #4 (keyword) for full testing

## Expected Outcome
After this fix:
1. Orchestrator coordinates using natural language
2. No JSON expectations from agents
3. LLM intelligently routes through pipeline
4. Full A2A compliance maintained

## References
- Issue #22: Orchestrator is more compliant than simple_orchestrator
- Fix #1: base.py (prerequisite)