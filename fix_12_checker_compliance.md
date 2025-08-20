# Fix #12: checker_agent.py - Verify Compliance and Fix Tools

## Priority: MEDIUM - Works with Timeline Builder
**Depends on: Fix #1-11 should be completed first**

## Current Status (from Issue #22)
checker_agent.py is **COMPLIANT** ✅

## Required Changes

### 1. Verify process_message Compliance
### 2. Fix tools/checker_tools.py (if needed)
### 3. Ensure proper loop with timeline_builder

## Test Script: `tests/test_checker_compliance.py`
```python
"""Test checker compliance."""
import os, sys, json, asyncio, subprocess, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["SHOW_AGENT_CALLS"] = "true"

async def test_no_json():
    from examples.pipeline.checker_agent import CheckerAgent
    agent = CheckerAgent()
    result = await agent.process_message("Check timeline accuracy")
    assert isinstance(result, str) and len(result) < 100
    json_msg = json.dumps({"timeline": []})
    result = await agent.process_message(json_msg)
    assert isinstance(result, str) and len(result) < 100
    print("✅ No JSON detection")

async def test_tools():
    from tools.checker_tools import verify_timeline_accuracy
    result = verify_timeline_accuracy(timeline_data='{"events": []}')
    if isinstance(result, str):
        try:
            json.loads(result)
            assert False, "Returns JSON string"
        except: pass
    print("✅ Tools OK")

async def test_communication():
    proc = subprocess.Popen(
        ["python", "examples/pipeline/checker_agent.py"],
        env={**os.environ, "PORT": "8009"}
    )
    time.sleep(3)
    try:
        from utils.a2a_client import A2AAgentClient
        async with A2AAgentClient() as client:
            response = await client.call_agent(
                "http://localhost:8009",
                "Verify timeline: Jan diagnosis -> Feb treatment"
            )
            assert len(response) > 0
            print("✅ Communication OK")
    finally:
        proc.terminate()

async def main():
    print("CHECKER AGENT COMPLIANCE TESTS")
    await test_no_json()
    await test_tools()
    await test_communication()
    print("✅ ALL PASSED")

if __name__ == "__main__":
    asyncio.run(main())
```

## Test Command
```bash
python tests/test_checker_compliance.py
```

## Branch Name
`fix-12-checker-compliance`

## Note
Works in loop with timeline_builder - fix together.

## References
Issue #22: Marked as compliant