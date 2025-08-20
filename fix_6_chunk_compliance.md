# Fix #6: chunk_agent.py - Remove JSON Detection and Fix Tool Return Types

## Priority: CRITICAL - Major Violation
**Depends on: Fix #1 (base.py), Fix #2 (simple_orchestrator), Fix #5 (grep) should be completed first**

## Current Violations (from Issue #22)

### Agent Violations (lines 103-173):
```python
async def process_message(self, message: str) -> str:
    try:
        # VIOLATION: Detects JSON
        data = json.loads(message)
        
        # VIOLATION: Routes based on JSON fields
        if "match_info" in data or ("matches" in data and "document" in data):
            # VIOLATION: Directly calls tool
            from tools.chunk_tools import create_document_chunk
            
            # VIOLATION: Process and return JSON
            chunks = []
            for match in matches[:5]:
                result = create_document_chunk(...)
                chunks.append(json.loads(result))
            
            return json.dumps({"chunks": chunks})  # VIOLATION
```

### Tool Violations (tools/chunk_tools.py):
Multiple functions returning `json.dumps()` instead of dicts

## Required Changes

### 1. Fix chunk_agent.py process_message
Replace entire process_message with:
```python
async def process_message(self, message: str) -> str:
    """
    Process incoming messages for LLM/ADK handling.
    NO JSON detection, NO custom routing.
    """
    # Simply return the message for LLM/ADK to process
    return message
```

Delete ALL the JSON detection and processing logic.

### 2. Fix tools/chunk_tools.py
Change all functions to return dicts:

```python
# WRONG - Current
def create_document_chunk(...) -> str:
    chunk = {
        "chunk_id": chunk_id,
        "content": content,
        "metadata": metadata
    }
    return json.dumps(chunk)

# RIGHT - Fixed
def create_document_chunk(...) -> dict:
    chunk = {
        "chunk_id": chunk_id,
        "content": content,
        "metadata": metadata
    }
    return chunk  # Return dict directly
```

### 3. Update System Instruction
```python
def get_system_instruction(self) -> str:
    return """You are a document chunk extraction specialist.

When asked to extract chunks:
1. Use create_document_chunk tool to extract context around matches
2. The tool needs match information and document content
3. Extract meaningful context with appropriate boundaries

Available tools:
- create_document_chunk: Extract context around a match
- merge_overlapping_chunks: Combine overlapping chunks
- analyze_chunk_boundaries: Detect semantic boundaries
- optimize_chunk_size: Optimize chunk sizes
- create_semantic_chunks: Create semantically coherent chunks
- extract_structured_sections: Extract document sections

Focus on preserving medical context and semantic coherence."""
```

## Test Requirements

### Create: `tests/test_chunk_compliance.py`
```python
"""
Test chunk_agent compliance with A2A specification.
Verifies orchestrator → grep → chunk communication.
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

async def test_chunk_no_json_detection():
    """Verify chunk doesn't detect JSON in process_message."""
    from examples.pipeline.chunk_agent import ChunkAgent
    
    agent = ChunkAgent()
    
    # Test 1: JSON message should NOT trigger special handling
    json_message = json.dumps({
        "matches": [
            {"line_number": 5, "match_text": "diabetes"},
            {"line_number": 10, "match_text": "insulin"}
        ],
        "document": "Patient document content here..."
    })
    
    result = await agent.process_message(json_message)
    
    # After fix, should return the message unchanged
    assert result == json_message, "JSON should not be detected"
    print("✅ JSON message not detected")
    
    # Test 2: Regular text
    text_message = "Extract chunks around the diabetes matches"
    result = await agent.process_message(text_message)
    assert result == text_message
    print("✅ Text message passes through")

async def test_tool_returns_dict():
    """Verify tools return dicts not JSON strings."""
    from tools.chunk_tools import create_document_chunk
    
    # Create test match info
    match_info = {
        "file_path": "test.txt",
        "line_number": 5,
        "match_text": "diabetes",
        "file_content": "Line 1\nLine 2\nLine 3\nLine 4\nPatient has diabetes\nLine 6"
    }
    
    # Call tool
    result = create_document_chunk(
        file_path="test.txt",
        match_info_json=json.dumps(match_info),
        lines_before="2",
        lines_after="2",
        boundary_detection="true",
        file_content=match_info["file_content"]
    )
    
    # After fix, should return dict not string
    assert isinstance(result, dict), f"Tool should return dict, got {type(result)}"
    print("✅ Tool returns dict not JSON string")

async def test_orchestrator_chunk_communication():
    """Test orchestrator → chunk communication."""
    print("\n" + "="*60)
    print("TEST: Orchestrator → Chunk Agent")
    print("="*60)
    
    # Start chunk agent
    chunk_process = subprocess.Popen(
        ["python", "examples/pipeline/chunk_agent.py"],
        env={**os.environ, "PORT": "8003"},
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
            Extract context chunks around these search matches:
            - Line 5: "diabetes" 
            - Line 10: "insulin therapy"
            
            From document:
            Patient Eleanor Richardson was diagnosed with Type 2 Diabetes.
            Treatment includes insulin therapy and dietary changes.
            """
            
            print(f"📤 Sending: {message[:50]}...")
            response = await client.call_agent("http://localhost:8003", message)
            print(f"📥 Response: {response[:200]}...")
            
            # Should get chunks back
            assert "chunk" in response.lower() or "context" in response.lower()
            print("✅ Chunk agent responds properly")
    
    finally:
        chunk_process.terminate()

async def test_pipeline_through_chunk():
    """Test pipeline: orchestrator → keyword → grep → chunk."""
    if "--pipeline" not in sys.argv:
        print("Skipping pipeline test (use --pipeline to run)")
        return True
    
    print("\n" + "="*60)
    print("TEST: Pipeline through Chunk")
    print("="*60)
    
    processes = []
    
    try:
        # Start agents in order
        agents = [
            ("simple_orchestrator", "8000"),
            ("keyword", "8001"),
            ("grep", "8002"),
            ("chunk", "8003")
        ]
        
        for agent_name, port in agents:
            processes.append(subprocess.Popen(
                ["python", f"examples/pipeline/{agent_name}_agent.py"],
                env={**os.environ, "PORT": port}
            ))
        
        # Set up config
        import json
        config = {
            "agents": {
                "keyword": {"url": "http://localhost:8001"},
                "grep": {"url": "http://localhost:8002"},
                "chunk": {"url": "http://localhost:8003"}
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
                "Search and extract chunks for diabetes in: Patient has diabetes requiring insulin"
            )
            
            print(f"Pipeline response: {response[:300]}...")
            print("✅ Pipeline works through chunk agent")
    
    finally:
        for p in processes:
            p.terminate()

async def main():
    """Run chunk agent compliance tests."""
    print("\n" + "="*70)
    print("CHUNK AGENT A2A COMPLIANCE TESTS")
    print("="*70)
    
    # Test 1: No JSON detection
    await test_chunk_no_json_detection()
    
    # Test 2: Tools return dicts
    await test_tool_returns_dict()
    
    # Test 3: Direct communication
    await test_orchestrator_chunk_communication()
    
    # Test 4: Pipeline (optional)
    await test_pipeline_through_chunk()
    
    print("\n" + "="*70)
    print("✅ ALL CHUNK TESTS PASSED")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
```

## Test Command
```bash
# Basic compliance test
python tests/test_chunk_compliance.py

# Test with full pipeline (requires grep to be fixed)
SHOW_AGENT_CALLS=true python tests/test_chunk_compliance.py --pipeline
```

## Expected Logs After Fix
```
📨 INCOMING REQUEST TO: Chunk Agent
📝 MESSAGE: Extract context chunks around these matches...
[No JSON detection logs]
[LLM processes request]
[Calls create_document_chunk tool]
Tool returns dict (not JSON string)
[LLM formats response]
📥 RESPONSE: Here are the extracted chunks...
```

## Branch Name
`fix-6-chunk-compliance`

## PR Checklist
- [ ] All JSON detection removed from process_message
- [ ] process_message just returns the message unchanged
- [ ] All tool functions return dicts not JSON strings
- [ ] No `json.dumps()` calls in tools
- [ ] Test shows no JSON detection
- [ ] Natural language communication works
- [ ] Pipeline test passes (if grep is fixed)

## Dependencies
- **MUST COMPLETE FIRST**:
  - Fix #1 (base.py) - Foundation
  - Fix #2 (simple_orchestrator) - For testing
  - Fix #5 (grep) - For pipeline testing

## Expected Outcome
After this fix:
1. Chunk agent accepts any message format
2. No JSON detection or special routing
3. Tools return proper Python dicts
4. Pipeline works: orchestrator → keyword → grep → chunk
5. Full A2A compliance achieved

## Critical Notes
- This is one of the two agents with CRITICAL violations
- Along with grep_agent, this breaks the entire pipeline
- Must be fixed for any downstream agents to work

## References
- Issue #22: Chunk agent violations
- Fix #1: base.py (prerequisite)
- Fix #5: grep_agent (similar violations)