# Fix #9: reconciliation_agent.py - Verify Compliance and Fix Tools

## Priority: MEDIUM - Pipeline Agent
**Depends on: Fix #1-8 should be completed first**

## Current Status (from Issue #22)
reconciliation_agent.py is **COMPLIANT** ✅:
- Returns "Processing..." in process_message
- Doesn't detect JSON

**BUT**: Need to verify tools return proper types

## Required Changes

### 1. Verify process_message Compliance
```python
async def process_message(self, message: str) -> str:
    return "Processing..."
```

### 2. Fix tools/reconciliation_tools.py (if needed)
Check ALL functions return dicts, not JSON strings.

## Test Requirements

### Create: `tests/test_reconciliation_compliance.py`
```python
"""Test reconciliation_agent compliance."""
import os
import sys
import json
import asyncio
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["SHOW_AGENT_CALLS"] = "true"

async def test_reconciliation_no_json():
    from examples.pipeline.reconciliation_agent import ReconciliationAgent
    agent = ReconciliationAgent()
    
    # Test regular message
    result = await agent.process_message("Reconcile conflicting data")
    assert isinstance(result, str) and len(result) < 100
    print("✅ Returns simple string")
    
    # Test JSON not detected
    json_msg = json.dumps({"conflicts": ["data1", "data2"]})
    result = await agent.process_message(json_msg)
    assert isinstance(result, str) and len(result) < 100
    print("✅ JSON not detected")

async def test_reconciliation_tools():
    from tools.reconciliation_tools import reconcile_conflicts
    
    result = reconcile_conflicts(
        grouped_data='{"encounter1": {"data": "test"}}'
    )
    
    assert not isinstance(result, str) or len(result) > 200
    if isinstance(result, str):
        try:
            json.loads(result)
            assert False, "Returns JSON string"
        except json.JSONDecodeError:
            pass
    print("✅ Tools return proper types")

async def test_orchestrator_communication():
    print("\nTEST: Orchestrator → Reconciliation")
    
    proc = subprocess.Popen(
        ["python", "examples/pipeline/reconciliation_agent.py"],
        env={**os.environ, "PORT": "8006"}
    )
    time.sleep(3)
    
    try:
        from utils.a2a_client import A2AAgentClient
        async with A2AAgentClient() as client:
            response = await client.call_agent(
                "http://localhost:8006",
                "Reconcile: Patient has diabetes per doc1, pre-diabetes per doc2"
            )
            assert "reconcil" in response.lower()
            print("✅ Agent responds properly")
    finally:
        proc.terminate()

async def main():
    print("\nRECONCILIATION AGENT COMPLIANCE TESTS")
    print("="*50)
    await test_reconciliation_no_json()
    await test_reconciliation_tools()
    await test_orchestrator_communication()
    print("✅ ALL TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(main())
```

## Test Command
```bash
python tests/test_reconciliation_compliance.py
```

## Branch Name
`fix-9-reconciliation-compliance`

## PR Checklist
- [ ] process_message returns simple string
- [ ] No JSON detection
- [ ] Tools return dicts
- [ ] Test passes

## Dependencies
Fix #1-8 for pipeline testing

## References
Issue #22: Marked as compliant