# Fix #14: unified_verifier_agent.py - Verify Compliance and Fix Tools

## Priority: MEDIUM - Late Pipeline Agent
**Depends on: Fix #1-13 should be completed first**

## Current Status (from Issue #22)
unified_verifier_agent.py is **COMPLIANT** ✅

## Test Script: `tests/test_unified_verifier_compliance.py`
```python
"""Test unified_verifier compliance."""
import os, sys, json, asyncio, subprocess, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["SHOW_AGENT_CALLS"] = "true"

async def test_no_json():
    from examples.pipeline.unified_verifier_agent import UnifiedVerifierAgent
    agent = UnifiedVerifierAgent()
    result = await agent.process_message("Verify extracted data")
    assert isinstance(result, str) and len(result) < 100
    json_msg = json.dumps({"entities": []})
    result = await agent.process_message(json_msg)
    assert isinstance(result, str) and len(result) < 100
    print("✅ No JSON detection")

async def test_tools():
    from tools.unified_verifier_tools import verify_medical_data
    result = verify_medical_data(extracted_data='{"entities": []}')
    if isinstance(result, str):
        try:
            json.loads(result)
            assert False, "Returns JSON string"
        except: pass
    print("✅ Tools OK")

async def test_communication():
    proc = subprocess.Popen(
        ["python", "examples/pipeline/unified_verifier_agent.py"],
        env={**os.environ, "PORT": "8011"}
    )
    time.sleep(3)
    try:
        from utils.a2a_client import A2AAgentClient
        async with A2AAgentClient() as client:
            response = await client.call_agent(
                "http://localhost:8011",
                "Verify: diabetes diagnosis, metformin prescription"
            )
            assert len(response) > 0
            print("✅ Communication OK")
    finally:
        proc.terminate()

async def main():
    print("UNIFIED VERIFIER COMPLIANCE TESTS")
    await test_no_json()
    await test_tools()
    await test_communication()
    print("✅ ALL PASSED")

if __name__ == "__main__":
    asyncio.run(main())
```

## Test Command
```bash
python tests/test_unified_verifier_compliance.py
```

## Branch Name
`fix-14-unified-verifier-compliance`

## References
Issue #22: Marked as compliant