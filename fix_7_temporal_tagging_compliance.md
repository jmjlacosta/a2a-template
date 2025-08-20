# Fix #7: temporal_tagging_agent.py - Verify Compliance and Fix Tools

## Priority: MEDIUM - Pipeline Agent
**Depends on: Fix #1-6 should be completed first for proper pipeline testing**

## Current Status (from Issue #22)
temporal_tagging_agent.py is **COMPLIANT** ✅:
- Returns "Processing temporal information..." in process_message
- Doesn't detect JSON
- Lets base class handle tool execution

**BUT**: Need to verify tools return proper types

## Required Changes

### 1. Verify process_message Compliance
Current implementation should be:
```python
async def process_message(self, message: str) -> str:
    # Should just return simple string
    return "Processing temporal information..."  # Or similar
```

### 2. Fix tools/temporal_tools.py (if needed)
Check ALL functions return dicts or appropriate types, not JSON strings:

```python
# WRONG if found:
def extract_temporal_information(...) -> str:
    temporal_data = {...}
    return json.dumps(temporal_data)

# RIGHT:
def extract_temporal_information(...) -> dict:
    temporal_data = {...}
    return temporal_data
```

### 3. Verify System Instruction
Should properly guide the LLM for temporal extraction.

## Test Requirements

### Create: `tests/test_temporal_tagging_compliance.py`
```python
"""
Test temporal_tagging_agent compliance with A2A specification.
Verifies orchestrator → [keyword → grep → chunk] → temporal communication.
"""
import os
import sys
import json
import asyncio
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["SHOW_AGENT_CALLS"] = "true"

async def test_temporal_no_json_detection():
    """Verify temporal doesn't detect JSON in process_message."""
    from examples.pipeline.temporal_tagging_agent import TemporalTaggingAgent
    
    agent = TemporalTaggingAgent()
    
    # Test with regular message
    message = "Extract temporal information from these chunks"
    result = await agent.process_message(message)
    assert isinstance(result, str)
    assert len(result) < 100  # Should be brief
    print(f"✅ process_message returns: '{result}'")
    
    # Test with JSON - should NOT be detected
    json_message = json.dumps({
        "chunks": ["Patient visited on 2024-01-15"],
        "document": "medical record"
    })
    result = await agent.process_message(json_message)
    assert isinstance(result, str)
    assert len(result) < 100
    print("✅ JSON not detected or processed")

async def test_temporal_tools():
    """Verify tools return proper types."""
    from tools.temporal_tools import extract_temporal_information
    
    # Test the main tool
    result = extract_temporal_information(
        text="Patient visited on January 15, 2024 for diabetes checkup"
    )
    
    # Should return dict or list, not JSON string
    assert not isinstance(result, str) or len(result) > 200, \
        f"Tool should return dict/list or detailed text, got: {result[:100]}"
    
    if isinstance(result, str):
        # If string, should NOT be JSON
        try:
            json.loads(result)
            assert False, "Tool returned JSON string - should return dict or natural text"
        except json.JSONDecodeError:
            pass  # Good - it's natural text
    
    print("✅ Tools return proper types")

async def test_orchestrator_to_temporal():
    """Test orchestrator → temporal communication."""
    print("\n" + "="*60)
    print("TEST: Orchestrator → Temporal Tagging")
    print("="*60)
    
    # Start temporal agent
    temporal_process = subprocess.Popen(
        ["python", "examples/pipeline/temporal_tagging_agent.py"],
        env={**os.environ, "PORT": "8004"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    time.sleep(3)
    
    try:
        from utils.a2a_client import A2AAgentClient
        
        async with A2AAgentClient() as client:
            message = """
            Extract temporal information from these medical chunks:
            
            1. "Patient visited on January 15, 2024 for initial consultation"
            2. "Follow-up scheduled for February 1, 2024"
            3. "Diagnosed with diabetes in 2023"
            """
            
            print(f"📤 Sending: {message[:50]}...")
            response = await client.call_agent("http://localhost:8004", message)
            print(f"📥 Response: {response[:200]}...")
            
            # Should extract dates
            assert "2024" in response or "january" in response.lower() or "temporal" in response.lower()
            print("✅ Temporal agent responds properly")
    
    finally:
        temporal_process.terminate()

async def test_pipeline_to_temporal():
    """Test pipeline through temporal tagging."""
    if "--pipeline" not in sys.argv:
        print("Skipping pipeline test (use --pipeline to run)")
        return True
    
    print("\n" + "="*60)
    print("TEST: Pipeline through Temporal Tagging")
    print("="*60)
    
    processes = []
    
    try:
        # Start agents up to temporal
        agents = [
            ("simple_orchestrator", "8000"),
            ("keyword", "8001"),
            ("grep", "8002"),
            ("chunk", "8003"),
            ("temporal_tagging", "8004")
        ]
        
        for agent_name, port in agents:
            processes.append(subprocess.Popen(
                ["python", f"examples/pipeline/{agent_name}_agent.py"],
                env={**os.environ, "PORT": port}
            ))
        
        # Set up config
        config = {
            "agents": {
                "keyword": {"url": "http://localhost:8001"},
                "grep": {"url": "http://localhost:8002"},
                "chunk": {"url": "http://localhost:8003"},
                "temporal_tagging": {"url": "http://localhost:8004"}
            }
        }
        os.makedirs("config", exist_ok=True)
        with open("config/agents.json", "w") as f:
            json.dump(config, f)
        
        time.sleep(5)
        
        from utils.a2a_client import A2AAgentClient
        
        async with A2AAgentClient() as client:
            response = await client.call_agent(
                "http://localhost:8000",
                "Analyze: Patient visited on Jan 15, 2024 for diabetes checkup"
            )
            
            print(f"Pipeline response: {response[:300]}...")
            print("✅ Pipeline works through temporal tagging")
    
    finally:
        for p in processes:
            p.terminate()

async def main():
    """Run temporal tagging compliance tests."""
    print("\n" + "="*70)
    print("TEMPORAL TAGGING AGENT A2A COMPLIANCE TESTS")
    print("="*70)
    
    # Test 1: No JSON detection
    await test_temporal_no_json_detection()
    
    # Test 2: Tools return proper types
    await test_temporal_tools()
    
    # Test 3: Direct communication
    await test_orchestrator_to_temporal()
    
    # Test 4: Pipeline (optional)
    await test_pipeline_to_temporal()
    
    print("\n" + "="*70)
    print("✅ ALL TEMPORAL TAGGING TESTS PASSED")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
```

## Test Command
```bash
# Basic compliance test
python tests/test_temporal_tagging_compliance.py

# Test with pipeline (requires previous agents fixed)
SHOW_AGENT_CALLS=true python tests/test_temporal_tagging_compliance.py --pipeline
```

## Branch Name
`fix-7-temporal-tagging-compliance`

## PR Checklist
- [ ] process_message returns simple string
- [ ] No JSON detection in agent
- [ ] Tools return dicts/appropriate types, not JSON strings
- [ ] Test passes showing compliance
- [ ] Can receive chunks from previous pipeline stages
- [ ] Extracts temporal information properly

## Dependencies
- **MUST COMPLETE**: Fix #1-6 for full pipeline testing
- Can be tested independently for basic compliance

## Expected Outcome
After verification/fix:
1. Temporal tagging agent confirmed compliant
2. Tools return proper Python types
3. Extracts dates and temporal markers correctly
4. Pipeline works through this stage

## References
- Issue #22: Temporal tagging marked as compliant
- Previous fixes: #1-6