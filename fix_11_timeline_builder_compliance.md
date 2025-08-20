# Fix #11: timeline_builder_agent.py - Verify Compliance and Fix Tools

## Priority: MEDIUM - Pipeline Agent with Checker Loop
**Depends on: Fix #1-10 should be completed first**

## Current Status (from Issue #22)
timeline_builder_agent.py is **COMPLIANT** ✅

## Required Changes

### 1. Verify process_message Compliance
### 2. Fix tools/timeline_builder_tools.py (if needed)
### 3. Ensure proper interaction with checker_agent

## Test Script: `tests/test_timeline_builder_compliance.py`
```python
"""Test timeline_builder compliance."""
import os, sys, json, asyncio, subprocess, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["SHOW_AGENT_CALLS"] = "true"

async def test_no_json():
    from examples.pipeline.timeline_builder_agent import TimelineBuilderAgent
    agent = TimelineBuilderAgent()
    result = await agent.process_message("Build timeline")
    assert isinstance(result, str) and len(result) < 100
    json_msg = json.dumps({"events": []})
    result = await agent.process_message(json_msg)
    assert isinstance(result, str) and len(result) < 100
    print("✅ No JSON detection")

async def test_tools():
    from tools.timeline_builder_tools import build_medical_timeline
    result = build_medical_timeline(events_data='{"events": []}')
    if isinstance(result, str):
        try:
            json.loads(result)
            assert False, "Returns JSON string"
        except: pass
    print("✅ Tools OK")

async def test_communication():
    proc = subprocess.Popen(
        ["python", "examples/pipeline/timeline_builder_agent.py"],
        env={**os.environ, "PORT": "8008"}
    )
    time.sleep(3)
    try:
        from utils.a2a_client import A2AAgentClient
        async with A2AAgentClient() as client:
            response = await client.call_agent(
                "http://localhost:8008",
                "Build timeline from: Jan 2024 diagnosis, Feb 2024 treatment"
            )
            assert len(response) > 0
            print("✅ Communication OK")
    finally:
        proc.terminate()

async def main():
    print("TIMELINE BUILDER COMPLIANCE TESTS")
    await test_no_json()
    await test_tools()
    await test_communication()
    print("✅ ALL PASSED")

if __name__ == "__main__":
    asyncio.run(main())
```

## Test Command
```bash
python tests/test_timeline_builder_compliance.py
```

## Branch Name
`fix-11-timeline-builder-compliance`

## Note
This agent interacts with checker_agent in a loop - ensure both are fixed together.

## References
Issue #22: Marked as compliant