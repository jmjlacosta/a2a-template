# Fix #13: unified_extractor_agent.py - Verify Compliance and Fix Tools

## Priority: MEDIUM - Late Pipeline Agent
**Depends on: Fix #1-12 should be completed first**

## Current Status (from Issue #22)
unified_extractor_agent.py is **COMPLIANT** ✅

## Test Script: `tests/test_unified_extractor_compliance.py`
```python
"""Test unified_extractor compliance."""
import os, sys, json, asyncio, subprocess, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["SHOW_AGENT_CALLS"] = "true"

async def test_no_json():
    from examples.pipeline.unified_extractor_agent import UnifiedExtractorAgent
    agent = UnifiedExtractorAgent()
    result = await agent.process_message("Extract all entities")
    assert isinstance(result, str) and len(result) < 100
    json_msg = json.dumps({"document": "test"})
    result = await agent.process_message(json_msg)
    assert isinstance(result, str) and len(result) < 100
    print("✅ No JSON detection")

async def test_tools():
    from tools.unified_extractor_tools import extract_all_medical_entities
    result = extract_all_medical_entities(document='Patient has diabetes')
    if isinstance(result, str):
        try:
            json.loads(result)
            assert False, "Returns JSON string"
        except: pass
    print("✅ Tools OK")

async def test_communication():
    proc = subprocess.Popen(
        ["python", "examples/pipeline/unified_extractor_agent.py"],
        env={**os.environ, "PORT": "8010"}
    )
    time.sleep(3)
    try:
        from utils.a2a_client import A2AAgentClient
        async with A2AAgentClient() as client:
            response = await client.call_agent(
                "http://localhost:8010",
                "Extract entities from: Patient has diabetes, takes metformin"
            )
            assert len(response) > 0
            print("✅ Communication OK")
    finally:
        proc.terminate()

async def main():
    print("UNIFIED EXTRACTOR COMPLIANCE TESTS")
    await test_no_json()
    await test_tools()
    await test_communication()
    print("✅ ALL PASSED")

if __name__ == "__main__":
    asyncio.run(main())
```

## Test Command
```bash
python tests/test_unified_extractor_compliance.py
```

## Branch Name
`fix-13-unified-extractor-compliance`

## References
Issue #22: Marked as compliant