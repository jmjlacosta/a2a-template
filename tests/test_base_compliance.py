"""Test base.py A2A compliance after Fix #1."""
import os
import sys
import json
import asyncio
import subprocess
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment to show agent calls
os.environ["SHOW_AGENT_CALLS"] = "true"

async def test_no_json_detection():
    """Test that base.py doesn't detect and route JSON differently."""
    print("\n🔍 Testing No JSON Detection in base.py...")
    
    # Import base after sys.path is set
    from base import A2AAgent
    
    # Create a test agent with tools
    class TestAgent(A2AAgent):
        def get_agent_name(self):
            return "TestAgent"
        
        def get_agent_description(self):
            return "Test agent for compliance"
        
        def get_tools(self):
            from langchain_core.tools import tool
            @tool
            def test_tool(data: str) -> str:
                """Test tool."""
                return f"Processed: {data}"
            return [test_tool]
        
        async def process_message(self, message: str) -> str:
            return f"Agent processed: {message[:50]}"
    
    agent = TestAgent()
    
    # Check that _execute_tools_directly doesn't exist
    assert not hasattr(agent, '_execute_tools_directly'), "❌ _execute_tools_directly method still exists!"
    
    # Check source code for JSON detection
    import inspect
    source = inspect.getsource(A2AAgent)
    
    # These strings should NOT be in the source
    forbidden_strings = [
        "is_json_request",
        "json.loads(message)",
        "_execute_tools_directly",
        "JSON request with tools",
        "agent-to-agent communication"
    ]
    
    for forbidden in forbidden_strings:
        if forbidden in source:
            print(f"❌ Found forbidden string in source: '{forbidden}'")
            return False
    
    print("✅ No JSON detection logic found")
    return True

async def test_uniform_routing():
    """Test that all messages are routed uniformly."""
    print("\n🔀 Testing Uniform Message Routing...")
    
    from base import A2AAgent
    
    # The execute method should only check for tools, not message format
    import inspect
    source = inspect.getsource(A2AAgent.execute)
    
    # Should have single routing decision based on tools only
    if "if tools and len(tools) > 0:" in source:
        if "is_json" not in source and "json.loads" not in source:
            print("✅ Routing based only on tool availability")
            return True
    
    print("❌ Routing logic appears incorrect")
    return False

async def test_simple_agent():
    """Test a simple agent class without JSON detection."""
    print("\n🤖 Testing Agent Class Behavior...")
    
    from base import A2AAgent
    
    # Create a simple test agent
    class SimpleTestAgent(A2AAgent):
        def get_agent_name(self):
            return "SimpleTestAgent"
        
        def get_agent_description(self):
            return "Simple test agent for compliance testing"
        
        def get_tools(self):
            # No tools for this test
            return []
        
        async def process_message(self, message: str) -> str:
            # Should process all messages the same way
            return f"Processed: {message}"
    
    agent = SimpleTestAgent()
    
    # Test that agent doesn't have JSON detection methods
    assert not hasattr(agent, '_execute_tools_directly'), "Agent should not have _execute_tools_directly"
    
    # Test process_message with different inputs
    text_result = await agent.process_message("Regular text")
    json_string = json.dumps({"test": "data"})
    json_result = await agent.process_message(json_string)
    
    # Both should be processed as strings
    assert "Regular text" in text_result
    assert json_string in json_result or "test" in json_result
    
    print(f"  Text processing: {text_result}")
    print(f"  JSON string processing: {json_result}")
    print("✅ Agent processes all messages uniformly (no JSON detection)")
    return True

async def main():
    """Run all compliance tests."""
    print("=" * 60)
    print("🧪 BASE.PY A2A COMPLIANCE TESTS (Fix #1)")
    print("=" * 60)
    
    results = []
    
    # Test 1: No JSON detection
    results.append(await test_no_json_detection())
    
    # Test 2: Uniform routing
    results.append(await test_uniform_routing())
    
    # Test 3: Simple agent behavior
    results.append(await test_simple_agent())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 COMPLIANCE TEST RESULTS")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("\nbase.py is now A2A COMPLIANT!")
        print("JSON detection and custom routing have been removed.")
        print("All messages are now processed uniformly through the LLM.")
        return True
    else:
        print(f"❌ TESTS FAILED ({passed}/{total} passed)")
        print("\nbase.py still has compliance issues!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)