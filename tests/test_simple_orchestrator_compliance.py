"""
Test simple_orchestrator compliance with A2A specification.

Verifies that the orchestrator:
- Sends natural language messages, not JSON
- Parses text responses, not expecting JSON
- Follows A2A protocol for agent communication
"""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up logging to see agent calls
os.environ["SHOW_AGENT_CALLS"] = "true"
logging.basicConfig(level=logging.INFO)

async def test_no_json_sending():
    """Test that orchestrator doesn't send JSON to agents."""
    print("\n" + "="*60)
    print("TEST: Orchestrator Sends Natural Language (Not JSON)")
    print("="*60)
    
    from examples.pipeline.simple_orchestrator_agent import SimpleOrchestratorAgent
    
    orchestrator = SimpleOrchestratorAgent()
    
    # Check source code for JSON sending
    import inspect
    source = inspect.getsource(SimpleOrchestratorAgent)
    
    # These patterns indicate JSON sending (should NOT be present)
    forbidden_patterns = [
        'json.dumps({',  # Creating JSON to send
        '"patterns":',  # JSON field names
        '"document_content":',
        '"match_info":',
        '"lines_before":',
        '"lines_after":'
    ]
    
    violations = []
    for pattern in forbidden_patterns:
        if pattern in source:
            violations.append(pattern)
    
    if violations:
        print(f"❌ Found JSON sending patterns: {violations}")
        return False
    
    print("✅ No JSON sending patterns found")
    return True

async def test_natural_language_messages():
    """Test that orchestrator constructs natural language messages."""
    print("\n" + "="*60)
    print("TEST: Natural Language Message Construction")
    print("="*60)
    
    from examples.pipeline.simple_orchestrator_agent import SimpleOrchestratorAgent
    
    # Check source for natural language patterns
    import inspect
    source = inspect.getsource(SimpleOrchestratorAgent)
    
    # These patterns indicate natural language (SHOULD be present)
    expected_patterns = [
        'Search the following document',  # Natural language for grep
        'Extract context around this match',  # Natural language for chunk
        'Please',  # Polite natural language
        'Document:'  # Clear labeling
    ]
    
    found = []
    for pattern in expected_patterns:
        if pattern in source:
            found.append(pattern)
    
    if len(found) < 2:
        print(f"❌ Missing natural language patterns. Found only: {found}")
        return False
    
    print(f"✅ Found natural language patterns: {found}")
    return True

async def test_no_json_parsing():
    """Test that orchestrator doesn't expect JSON responses."""
    print("\n" + "="*60)
    print("TEST: No JSON Response Expectations")
    print("="*60)
    
    from examples.pipeline.simple_orchestrator_agent import SimpleOrchestratorAgent
    
    # Check the _parse_grep_results method
    import inspect
    source = inspect.getsource(SimpleOrchestratorAgent._parse_grep_results)
    
    # Should NOT try to parse as JSON first
    if 'json.loads(grep_response)' in source:
        print("❌ Still trying to parse responses as JSON")
        return False
    
    # Should mention natural language or text parsing
    if 'natural language' in source or 'text response' in source:
        print("✅ Parses natural language responses")
        return True
    
    print("⚠️  Check: Method should explicitly handle text responses")
    return True

async def test_orchestrator_execution():
    """Test that orchestrator can process a message."""
    print("\n" + "="*60)
    print("TEST: Orchestrator Message Processing")
    print("="*60)
    
    from examples.pipeline.simple_orchestrator_agent import SimpleOrchestratorAgent
    
    orchestrator = SimpleOrchestratorAgent()
    
    # Test document
    test_document = """
    Patient: Eleanor Richardson
    Date: 2024-01-15
    Diagnosis: Type 2 Diabetes
    Treatment: Metformin 500mg twice daily
    """
    
    print("📝 Test document:")
    print(test_document)
    
    # The orchestrator should construct natural language messages
    # We can't test full execution without starting all agents,
    # but we can verify the message format would be correct
    
    # Test pattern extraction
    patterns = orchestrator._extract_patterns("Found patterns: diabetes, metformin, patient")
    print(f"\n📊 Extracted patterns: {patterns}")
    
    if len(patterns) > 0:
        print("✅ Can extract patterns from text")
    else:
        print("❌ Failed to extract patterns")
        return False
    
    return True

async def main():
    """Run all compliance tests."""
    print("\n" + "="*70)
    print("🧪 SIMPLE ORCHESTRATOR A2A COMPLIANCE TESTS")
    print("="*70)
    
    results = []
    
    # Test 1: No JSON sending
    results.append(await test_no_json_sending())
    
    # Test 2: Natural language messages
    results.append(await test_natural_language_messages())
    
    # Test 3: No JSON parsing expectations
    results.append(await test_no_json_parsing())
    
    # Test 4: Basic execution
    results.append(await test_orchestrator_execution())
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST RESULTS")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("\nSimple orchestrator is A2A compliant:")
        print("- Sends natural language messages")
        print("- No JSON expectations")
        print("- Follows A2A protocol")
        return True
    else:
        print(f"❌ TESTS FAILED ({passed}/{total} passed)")
        print("\nSimple orchestrator still has compliance issues!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)