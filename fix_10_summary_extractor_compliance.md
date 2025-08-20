# Fix #10: summary_extractor_agent.py - Verify Compliance and Fix Tools

## Priority: MEDIUM - Pipeline Agent
**Depends on: Fix #1-9 should be completed first**

## Current Status (from Issue #22)
summary_extractor_agent.py is **COMPLIANT** ✅

## Required Changes

### 1. Verify process_message Compliance
```python
async def process_message(self, message: str) -> str:
    return "Processing..."
```

### 2. Fix tools/summary_extractor_tools.py (if needed)
Check ALL functions return dicts, not JSON strings.

## Test Script: `tests/test_summary_extractor_compliance.py`
```python
"""Test summary_extractor compliance."""
import os, sys, json, asyncio, subprocess, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["SHOW_AGENT_CALLS"] = "true"

async def test_no_json():
    from examples.pipeline.summary_extractor_agent import SummaryExtractorAgent
    agent = SummaryExtractorAgent()
    result = await agent.process_message("Extract summary")
    assert isinstance(result, str) and len(result) < 100
    json_msg = json.dumps({"data": "test"})
    result = await agent.process_message(json_msg)
    assert isinstance(result, str) and len(result) < 100
    print("✅ No JSON detection")

async def test_tools():
    from tools.summary_extractor_tools import extract_clinical_summary
    result = extract_clinical_summary(reconciled_data='{"data": "test"}')
    if isinstance(result, str):
        try:
            json.loads(result)
            assert False, "Returns JSON string"
        except: pass
    print("✅ Tools OK")

async def test_communication():
    proc = subprocess.Popen(
        ["python", "examples/pipeline/summary_extractor_agent.py"],
        env={**os.environ, "PORT": "8007"}
    )
    time.sleep(3)
    try:
        from utils.a2a_client import A2AAgentClient
        async with A2AAgentClient() as client:
            response = await client.call_agent(
                "http://localhost:8007",
                "Extract clinical summary from reconciled data"
            )
            assert len(response) > 0
            print("✅ Communication OK")
    finally:
        proc.terminate()

async def main():
    print("SUMMARY EXTRACTOR COMPLIANCE TESTS")
    await test_no_json()
    await test_tools()
    await test_communication()
    print("✅ ALL PASSED")

if __name__ == "__main__":
    asyncio.run(main())
```

## Test Command
```bash
python tests/test_summary_extractor_compliance.py
```

## Branch Name
`fix-10-summary-extractor-compliance`

## PR Checklist
- [ ] process_message compliant
- [ ] Tools return dicts
- [ ] Test passes

## References
Issue #22: Marked as compliant