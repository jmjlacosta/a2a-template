# Fix #8: encounter_grouping_agent.py - Verify Compliance and Fix Tools

## Priority: MEDIUM - Pipeline Agent
**Depends on: Fix #1-7 should be completed first for proper pipeline testing**

## Current Status (from Issue #22)
encounter_grouping_agent.py is **COMPLIANT** ✅:
- Returns "Processing..." in process_message
- Doesn't detect JSON
- Lets base class handle tool execution

**BUT**: Need to verify tools return proper types

## Required Changes

### 1. Verify process_message Compliance
```python
async def process_message(self, message: str) -> str:
    # Should just return simple string
    return "Processing..."
```

### 2. Fix tools/encounter_grouping_tools.py (if needed)
Check ALL functions return dicts, not JSON strings.

### 3. Verify System Instruction
Should guide LLM to group medical events by encounters.

## Test Requirements

### Create: `tests/test_encounter_grouping_compliance.py`
```python
"""
Test encounter_grouping_agent compliance with A2A specification.
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

async def test_encounter_no_json_detection():
    """Verify encounter doesn't detect JSON."""
    from examples.pipeline.encounter_grouping_agent import EncounterGroupingAgent
    
    agent = EncounterGroupingAgent()
    
    # Test with regular message
    message = "Group these medical events by encounter"
    result = await agent.process_message(message)
    assert isinstance(result, str)
    assert len(result) < 100
    print(f"✅ process_message returns: '{result}'")
    
    # Test with JSON - should NOT be detected
    json_message = json.dumps({
        "events": ["Visit 1", "Visit 2"],
        "dates": ["2024-01-15", "2024-02-01"]
    })
    result = await agent.process_message(json_message)
    assert isinstance(result, str)
    assert len(result) < 100
    print("✅ JSON not detected")

async def test_encounter_tools():
    """Verify tools return proper types."""
    from tools.encounter_grouping_tools import group_by_encounters
    
    # Test the main tool
    result = group_by_encounters(
        temporal_data='[{"date": "2024-01-15", "event": "Initial visit"}]'
    )
    
    # Should return dict, not JSON string
    assert not isinstance(result, str) or len(result) > 200, \
        "Tool should return dict or detailed text"
    
    if isinstance(result, str):
        try:
            json.loads(result)
            assert False, "Tool returned JSON string"
        except json.JSONDecodeError:
            pass  # Good
    
    print("✅ Tools return proper types")

async def test_orchestrator_to_encounter():
    """Test communication with encounter grouping."""
    print("\n" + "="*60)
    print("TEST: Orchestrator → Encounter Grouping")
    print("="*60)
    
    encounter_process = subprocess.Popen(
        ["python", "examples/pipeline/encounter_grouping_agent.py"],
        env={**os.environ, "PORT": "8005"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    time.sleep(3)
    
    try:
        from utils.a2a_client import A2AAgentClient
        
        async with A2AAgentClient() as client:
            message = """
            Group these temporal events by clinical encounter:
            - Jan 15, 2024: Initial consultation
            - Jan 15, 2024: Blood work ordered
            - Feb 1, 2024: Follow-up visit
            - Feb 1, 2024: Medication adjustment
            """
            
            print(f"📤 Sending: {message[:50]}...")
            response = await client.call_agent("http://localhost:8005", message)
            print(f"📥 Response: {response[:200]}...")
            
            assert "encounter" in response.lower() or "group" in response.lower()
            print("✅ Encounter grouping responds properly")
    
    finally:
        encounter_process.terminate()

async def main():
    """Run encounter grouping compliance tests."""
    print("\n" + "="*70)
    print("ENCOUNTER GROUPING AGENT A2A COMPLIANCE TESTS")
    print("="*70)
    
    await test_encounter_no_json_detection()
    await test_encounter_tools()
    await test_orchestrator_to_encounter()
    
    print("\n" + "="*70)
    print("✅ ALL ENCOUNTER GROUPING TESTS PASSED")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
```

## Test Command
```bash
python tests/test_encounter_grouping_compliance.py
```

## Branch Name
`fix-8-encounter-grouping-compliance`

## PR Checklist
- [ ] process_message returns simple string
- [ ] No JSON detection
- [ ] Tools return dicts, not JSON strings
- [ ] Test passes
- [ ] Groups events by encounter properly

## Dependencies
- Fix #1-7 for full pipeline testing

## References
- Issue #22: Marked as compliant