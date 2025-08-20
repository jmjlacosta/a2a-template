# Enhancement: Add A2A Compliance Tests to test_any_agent.py

## Background
Based on our comprehensive A2A compliance audit (Issue #22), we've identified critical violations in our agent implementations. The test_any_agent.py file should be enhanced to catch these non-compliance issues automatically.

## Current State
The existing test_any_agent.py tests:
- Basic agent properties
- Agent card generation  
- Tool availability
- Optional features
- Message processing
- Execute method

## Required Enhancements

### 1. Add JSON Detection Test
Test that agents DO NOT detect JSON and route differently.

```python
async def test_no_json_detection(self):
    """Test that agent doesn't detect JSON and route differently (A2A violation)."""
    print("\n🔍 Testing A2A Compliance - No JSON Detection...")
    
    # Test with JSON string
    json_msg = json.dumps({"test": "data", "patterns": ["test"]})
    text_msg = "Process this: test data with patterns"
    
    # Both should be processed the same way
    if hasattr(self.agent, 'process_message'):
        json_response = await self.agent.process_message(json_msg)
        text_response = await self.agent.process_message(text_msg)
        
        # Check that JSON isn't being parsed and processed differently
        # JSON message should be treated as text
        assert "test" not in json_response or "data" not in json_response
        self.passed_tests.append("No JSON detection - A2A compliant")
```

### 2. Add Tool Return Type Test
Test that tools return proper A2A types (not JSON strings).

```python
def test_tool_return_types(self):
    """Test that tools return proper types, not JSON strings."""
    print("\n📦 Testing Tool Return Types...")
    
    tools = self.agent.get_tools()
    if tools:
        for tool in tools:
            # Mock call to check return type
            # Tools should return dict/list/DataPart, not JSON strings
            pass
```

### 3. Add Message Format Compliance Test
Test that agents accept and return proper A2A message formats.

```python
async def test_a2a_message_format(self):
    """Test A2A message format compliance."""
    print("\n📨 Testing A2A Message Format...")
    
    # Test with proper A2A message
    message = Message(
        role="user",
        parts=[Part(root=TextPart(text="Test message"))],
        messageId="test-123",
        kind="message"
    )
    
    # Agent should process this properly
    # Response should be TextPart or DataPart, not raw string
```

### 4. Add Duplicate Method Detection
Test for duplicate process_message methods.

```python
def test_no_duplicate_methods(self):
    """Test that agent doesn't have duplicate methods."""
    print("\n🔄 Testing for Duplicate Methods...")
    
    # Check for duplicate process_message
    import inspect
    source = inspect.getsource(self.agent.__class__)
    
    # Count occurrences of "def process_message"
    count = source.count("def process_message")
    assert count <= 1, f"Found {count} process_message definitions"
    
    # Count occurrences of "async def process_message"  
    async_count = source.count("async def process_message")
    assert async_count <= 1, f"Found {async_count} async process_message definitions"
```

### 5. Add Opaque Execution Test
Test that agents follow "Opaque Execution" principle.

```python
async def test_opaque_execution(self):
    """Test Opaque Execution - no custom routing based on message content."""
    print("\n🔒 Testing Opaque Execution...")
    
    # Various message types should all go through same path
    messages = [
        "Simple text",
        json.dumps({"key": "value"}),
        "<xml>data</xml>",
        "SELECT * FROM users"
    ]
    
    # All should be processed uniformly
    for msg in messages:
        # Test that processing doesn't branch based on content type
        pass
```

### 6. Add Pipeline Integration Test
Test that agent can communicate with other agents properly.

```python
async def test_agent_to_agent_communication(self):
    """Test agent-to-agent communication compliance."""
    print("\n🔗 Testing Agent-to-Agent Communication...")
    
    # Test sending to another agent using A2AAgentClient
    # Response should be proper A2A format
```

## Implementation Plan

1. **Create new test class**: `A2AComplianceTester` extending `UniversalAgentTester`
2. **Add compliance tests** as methods in the new class
3. **Add flag** `--compliance` to run compliance tests
4. **Document violations** found during testing
5. **Create fixture agents** for testing edge cases

## Test Command Examples
```bash
# Regular tests
python tests/test_any_agent.py examples.pipeline.grep_agent GrepAgent

# With compliance tests
python tests/test_any_agent.py examples.pipeline.grep_agent GrepAgent --compliance

# Test all pipeline agents
for agent in keyword grep chunk temporal_tagging encounter_grouping reconciliation summary_extractor timeline_builder checker unified_extractor unified_verifier narrative_synthesis; do
    python tests/test_any_agent.py examples.pipeline.${agent}_agent ${agent^}Agent --compliance
done
```

## Success Criteria
- Detects JSON routing violations
- Detects duplicate method definitions
- Validates tool return types
- Ensures A2A message format compliance
- Catches opaque execution violations
- Tests agent-to-agent communication

## References
- Issue #22: A2A Compliance Audit
- A2A Specification v0.3.0
- Current violations in base.py, grep_agent.py, chunk_agent.py, summarize_agent.py

## Note
This enhancement will help catch A2A non-compliance issues automatically, preventing future violations and ensuring all agents follow the specification properly.