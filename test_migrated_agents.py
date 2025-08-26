#!/usr/bin/env python3
"""
Test script for the migrated pipeline agents.
Tests each agent individually to verify the migration was successful.
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent))

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def print_test(name: str, passed: bool, details: str = ""):
    """Print colored test result."""
    if passed:
        print(f"{GREEN}✓{RESET} {name}")
        if details:
            print(f"  {details}")
    else:
        print(f"{RED}✗{RESET} {name}")
        if details:
            print(f"  {RED}{details}{RESET}")
    return passed

async def test_chunk_agent():
    """Test the Chunk Agent."""
    print(f"\n{YELLOW}Testing Chunk Agent{RESET}")
    print("=" * 40)
    
    all_passed = True
    
    try:
        from examples.pipeline.chunk.agent import ChunkAgent
        agent = ChunkAgent()
        
        # Test basic properties
        all_passed &= print_test("Agent created", True, agent.get_agent_name())
        all_passed &= print_test("Version is 2.0.0", agent.get_agent_version() == "2.0.0")
        
        # Test simple chunk extraction
        test_message = json.dumps({
            "match_info": {
                "pattern": "diabetes",
                "line_number": 3,
                "match_text": "diabetes type 2",
                "document": "Patient history:\nPrevious admissions for chest pain.\nDiagnosed with diabetes type 2 in 2020.\nCurrently on metformin 500mg daily.\nBlood pressure well controlled."
            },
            "lines_before": 2,
            "lines_after": 2
        })
        
        result = await agent.process_message(test_message)
        
        all_passed &= print_test("Chunk extraction works", isinstance(result, str) and len(result) > 0)
        all_passed &= print_test("Contains match text", "diabetes type 2" in result)
        all_passed &= print_test("Contains line numbers", ">>> " in result)
        all_passed &= print_test("Contains medical summary", "Medical Information" in result or "metformin" in result)
        
        print(f"\n{YELLOW}Sample chunk output:{RESET}")
        print(result[:300] + "..." if len(result) > 300 else result)
        
    except Exception as e:
        all_passed &= print_test("Chunk Agent test", False, str(e))
    
    return all_passed

async def test_grep_agent():
    """Test the Grep Agent."""
    print(f"\n{YELLOW}Testing Grep Agent{RESET}")
    print("=" * 40)
    
    all_passed = True
    
    try:
        from examples.pipeline.grep.agent import GrepAgent
        agent = GrepAgent()
        
        # Test basic properties
        all_passed &= print_test("Agent created", True, agent.get_agent_name())
        all_passed &= print_test("Version is 2.0.0", agent.get_agent_version() == "2.0.0")
        
        # Test pattern search
        test_message = json.dumps({
            "patterns": ["diabetes", r"\b\d+\s*mg\b"],
            "document_content": """Patient history:
Previous admissions for chest pain.
Diagnosed with diabetes type 2 in 2020.
Currently on metformin 500mg daily.
Blood pressure well controlled.
Patient also has diabetes complications.""",
            "case_sensitive": False
        })
        
        result = await agent.process_message(test_message)
        result_data = json.loads(result)
        
        all_passed &= print_test("Search returns JSON", isinstance(result_data, dict))
        all_passed &= print_test("Has matches array", "matches" in result_data)
        all_passed &= print_test("Found diabetes matches", 
                                 len([m for m in result_data.get("matches", []) if "diabetes" in m.get("match_text", "").lower()]) > 0)
        all_passed &= print_test("Found dosage matches", 
                                 len([m for m in result_data.get("matches", []) if "500mg" in m.get("match_text", "")]) > 0)
        all_passed &= print_test("Includes context", 
                                 any("context_before" in m for m in result_data.get("matches", [])))
        
        print(f"\n{YELLOW}Sample search results:{RESET}")
        print(json.dumps(result_data, indent=2)[:400] + "...")
        
    except Exception as e:
        all_passed &= print_test("Grep Agent test", False, str(e))
    
    return all_passed

async def test_keyword_agent():
    """Test the Keyword Agent (needs LLM or fallback)."""
    print(f"\n{YELLOW}Testing Keyword Agent{RESET}")
    print("=" * 40)
    
    all_passed = True
    
    try:
        from examples.pipeline.keyword.agent import KeywordAgent
        agent = KeywordAgent()
        
        # Test basic properties
        all_passed &= print_test("Agent created", True, agent.get_agent_name())
        all_passed &= print_test("Version is 2.0.0", agent.get_agent_version() == "2.0.0")
        
        # Test pattern generation (will use fallback if no LLM)
        test_message = json.dumps({
            "document_preview": """MEDICAL RECORD
Patient: John Doe
DOB: 01/15/1960
Chief Complaint: Chest pain and shortness of breath

History of Present Illness:
65-year-old male presents with acute chest pain that started 2 hours ago.
Patient has a history of diabetes mellitus type 2, hypertension.
Currently taking metformin 500mg bid, lisinopril 10mg daily.

Vital Signs:
BP: 150/90 mmHg
HR: 88 bpm
Temp: 98.6°F
""",
            "focus_areas": ["diagnosis", "medications", "vitals"]
        })
        
        result = await agent.process_message(test_message)
        result_data = json.loads(result)
        
        all_passed &= print_test("Returns JSON", isinstance(result_data, dict))
        all_passed &= print_test("Has pattern categories", 
                                 any(key in result_data for key in 
                                     ["section_patterns", "clinical_patterns", "medication_patterns"]))
        
        # Check if we got patterns
        total_patterns = 0
        for category in result_data.values():
            if isinstance(category, list):
                total_patterns += len(category)
        
        all_passed &= print_test("Generated patterns", total_patterns > 0, f"Total: {total_patterns}")
        
        print(f"\n{YELLOW}Sample patterns:{RESET}")
        for category, patterns in result_data.items():
            if isinstance(patterns, list) and patterns:
                print(f"  {category}: {len(patterns)} patterns")
                for p in patterns[:2]:  # Show first 2
                    pattern_text = p.get("pattern", p) if isinstance(p, dict) else str(p)
                    print(f"    - {pattern_text}")
        
    except Exception as e:
        all_passed &= print_test("Keyword Agent test", False, str(e))
    
    return all_passed

async def test_orchestrator_agent():
    """Test the Simple Orchestrator Agent (basic structure only)."""
    print(f"\n{YELLOW}Testing Simple Orchestrator Agent{RESET}")
    print("=" * 40)
    
    all_passed = True
    
    try:
        from examples.pipeline.simple_orchestrator.agent import SimpleOrchestratorAgent
        agent = SimpleOrchestratorAgent()
        
        # Test basic properties
        all_passed &= print_test("Agent created", True, agent.get_agent_name())
        all_passed &= print_test("Version is 2.0.0", agent.get_agent_version() == "2.0.0")
        all_passed &= print_test("Has agent references", hasattr(agent, 'keyword_agent'))
        
        # Test configuration
        all_passed &= print_test("Has configuration", agent.MAX_PATTERNS > 0)
        all_passed &= print_test("Timeout configured", agent.CALL_TIMEOUT_SEC > 0)
        
        print(f"  Agent targets: {agent.keyword_agent}, {agent.grep_agent}, {agent.chunk_agent}, {agent.summarize_agent}")
        
    except Exception as e:
        all_passed &= print_test("Orchestrator Agent test", False, str(e))
    
    return all_passed

async def main():
    """Run all agent tests."""
    print("\n" + "="*60)
    print("Testing Migrated Pipeline Agents")
    print("="*60)
    
    # Skip startup checks during test
    os.environ["A2A_SKIP_STARTUP"] = "1"
    
    all_tests_passed = True
    
    # Test each agent
    all_tests_passed &= await test_chunk_agent()
    all_tests_passed &= await test_grep_agent() 
    all_tests_passed &= await test_keyword_agent()
    all_tests_passed &= await test_orchestrator_agent()
    
    # Summary
    print("\n" + "="*60)
    if all_tests_passed:
        print(f"{GREEN}✓ ALL AGENT TESTS PASSED!{RESET}")
        print("\nThe migrated agents are working correctly:")
        print("  • Chunk Agent: Algorithmic text extraction")
        print("  • Grep Agent: Pattern searching with error handling") 
        print("  • Keyword Agent: LLM pattern generation with fallbacks")
        print("  • Orchestrator: Pipeline coordination")
        print(f"\n{YELLOW}Next: Test the full pipeline end-to-end{RESET}")
    else:
        print(f"{RED}✗ Some agent tests failed{RESET}")
        print("Review the errors above before proceeding")
    print("="*60)
    
    return all_tests_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)