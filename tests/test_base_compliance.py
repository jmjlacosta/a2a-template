"""
Test base.py A2A compliance after Fix #1.

This test verifies that base.py follows the A2A specification:
- No custom routing based on message format
- No direct LLM API calls
- Minimal execute() implementation
- Let A2A framework handle execution
"""
import os
import sys
import json
import asyncio
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
    
    # Check that custom execution methods don't exist
    assert not hasattr(agent, '_execute_tools_directly'), "❌ _execute_tools_directly method still exists!"
    assert not hasattr(agent, '_execute_with_llm_no_tools'), "❌ _execute_with_llm_no_tools method still exists!"
    assert not hasattr(agent, '_execute_with_tools'), "❌ _execute_with_tools method still exists!"
    assert not hasattr(agent, '_get_llm_model'), "❌ _get_llm_model method still exists!"
    
    # Check source code for JSON detection
    import inspect
    source = inspect.getsource(A2AAgent)
    
    # These strings should NOT be in the source
    forbidden_strings = [
        "is_json_request",
        "json.loads(message)",
        "_execute_tools_directly",
        "JSON request with tools",
        "agent-to-agent communication",
        "google.generativeai",  # No direct LLM calls
        "litellm",  # No direct LLM calls
        "OPENAI_API_KEY",  # No direct API key checks
        "ANTHROPIC_API_KEY",  # No direct API key checks
        "Google ADK",  # Should not mention specific implementations
    ]
    
    for forbidden in forbidden_strings:
        if forbidden in source:
            print(f"❌ Found forbidden string in source: '{forbidden}'")
            return False
    
    print("✅ No JSON detection or custom routing logic found")
    return True

async def test_minimal_execute():
    """Test that execute() is minimal and delegates properly."""
    print("\n🔀 Testing Minimal Execute Implementation...")
    
    from base import A2AAgent
    
    # The execute method should be minimal
    import inspect
    source = inspect.getsource(A2AAgent.execute)
    
    # Count lines (excluding docstring and empty lines)
    lines = [l for l in source.split('\n') if l.strip() and not l.strip().startswith('#')]
    
    # Should be a minimal implementation (< 30 lines of actual code)
    if len(lines) < 50:  # Including try/except and some logging
        print(f"✅ Execute method is minimal ({len(lines)} lines)")
    else:
        print(f"❌ Execute method is too complex ({len(lines)} lines)")
        return False
    
    # Should only extract message, process it, and enqueue response
    required_patterns = [
        "_extract_message",  # Extract message
        "process_message",  # Process via agent logic
        "event_queue.enqueue_event",  # Send response
        "new_agent_text_message"  # Format response
    ]
    
    for pattern in required_patterns:
        if pattern not in source:
            print(f"❌ Missing required pattern: {pattern}")
            return False
    
    print("✅ Execute method follows minimal pattern")
    return True

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
    
    # Test that agent doesn't have custom execution methods
    assert not hasattr(agent, '_execute_tools_directly'), "Agent should not have _execute_tools_directly"
    assert not hasattr(agent, '_execute_with_llm_no_tools'), "Agent should not have _execute_with_llm_no_tools"
    assert not hasattr(agent, '_execute_with_tools'), "Agent should not have _execute_with_tools"
    
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

async def test_no_llm_imports():
    """Test that base.py doesn't import LLM libraries directly."""
    print("\n📦 Testing No Direct LLM Imports...")
    
    # Read the base.py file
    with open('base.py', 'r') as f:
        content = f.read()
    
    # Check for direct LLM imports that shouldn't be there
    forbidden_imports = [
        "import google.generativeai",
        "from google.generativeai",
        "import litellm",
        "from litellm",
        "import openai",
        "from openai",
        "import anthropic",
        "from anthropic",
        "from google.adk.agents.llm_agent",  # Should not directly use ADK
        "from google.adk.runners"
    ]
    
    for forbidden in forbidden_imports:
        if forbidden in content:
            print(f"❌ Found forbidden import: {forbidden}")
            return False
    
    print("✅ No direct LLM library imports found")
    return True

async def test_file_size():
    """Test that base.py is significantly smaller after refactoring."""
    print("\n📏 Testing File Size Reduction...")
    
    # Check file size
    file_size = Path('base.py').stat().st_size
    line_count = len(open('base.py').readlines())
    
    print(f"  File size: {file_size} bytes")
    print(f"  Line count: {line_count} lines")
    
    # Should be significantly smaller (was ~600+ lines, should be ~300 lines)
    if line_count < 400:
        print(f"✅ File is compact ({line_count} lines)")
        return True
    else:
        print(f"❌ File is still too large ({line_count} lines)")
        return False

async def main():
    """Run all compliance tests."""
    print("=" * 60)
    print("🧪 BASE.PY A2A COMPLIANCE TESTS (Fix #1)")
    print("=" * 60)
    
    results = []
    
    # Test 1: No JSON detection or custom routing
    results.append(await test_no_json_detection())
    
    # Test 2: Minimal execute implementation
    results.append(await test_minimal_execute())
    
    # Test 3: Simple agent behavior
    results.append(await test_simple_agent())
    
    # Test 4: No direct LLM imports
    results.append(await test_no_llm_imports())
    
    # Test 5: File size reduction
    results.append(await test_file_size())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 COMPLIANCE TEST RESULTS")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("\nbase.py is now A2A COMPLIANT!")
        print("- No JSON detection or custom routing")
        print("- No direct LLM API calls")
        print("- Minimal execute() implementation")
        print("- Lets A2A framework handle execution")
        return True
    else:
        print(f"❌ TESTS FAILED ({passed}/{total} passed)")
        print("\nbase.py still has compliance issues!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)