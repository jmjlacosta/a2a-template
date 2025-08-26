#!/usr/bin/env python3
"""
Test script to validate all production fixes from boss's review.
Verifies all changes are correctly implemented and working.
"""

import os
import sys
import json
import asyncio
import tempfile
from pathlib import Path

# Test colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def test_result(name: str, passed: bool, details: str = ""):
    """Print test result with color."""
    if passed:
        print(f"{GREEN}✓{RESET} {name}")
        if details:
            print(f"  {details}")
    else:
        print(f"{RED}✗{RESET} {name}")
        if details:
            print(f"  {RED}{details}{RESET}")
    return passed

async def test_production_fixes():
    """Test all production fixes from the boss's review."""
    print("\n" + "="*60)
    print("Testing Production Fixes from Boss's Review")
    print("="*60 + "\n")
    
    all_passed = True
    
    # Test 1: Base URL is root, not endpoint
    print(f"{YELLOW}1. Base URL Configuration{RESET}")
    try:
        from base import A2AAgent
        
        # Mock agent to test base URL
        class TestAgent(A2AAgent):
            def get_agent_name(self): return "Test"
            def get_agent_description(self): return "Test agent"
            async def process_message(self, msg): return "ok"
        
        # Test with HU_APP_URL
        os.environ["HU_APP_URL"] = "https://test.example.com"
        agent = TestAgent()
        card = agent.create_agent_card()
        
        passed = card.url == "https://test.example.com"
        all_passed &= test_result(
            "Base URL is root (not endpoint)",
            passed,
            f"URL: {card.url} (should be root, not /a2a/v1/...)"
        )
        
        # Clean up
        del os.environ["HU_APP_URL"]
    except Exception as e:
        all_passed &= test_result("Base URL test", False, str(e))
    
    print()
    
    # Test 2: Timeout parameter in a2a_client
    print(f"{YELLOW}2. A2A Client Timeout Parameter{RESET}")
    try:
        from utils.a2a_client import A2AClient
        import inspect
        
        # Check method signatures
        methods_to_check = ["call_agent", "call_agent_message", "_request"]
        timeout_found = {}
        
        for method_name in methods_to_check:
            method = getattr(A2AClient, method_name)
            sig = inspect.signature(method)
            has_timeout = "timeout_sec" in sig.parameters
            timeout_found[method_name] = has_timeout
            
            test_result(
                f"Method {method_name} has timeout_sec parameter",
                has_timeout,
                f"Parameters: {list(sig.parameters.keys())}"
            )
        
        all_passed &= all(timeout_found.values())
    except Exception as e:
        all_passed &= test_result("Timeout parameter test", False, str(e))
    
    print()
    
    # Test 3: LLM runner handles both stream and single result
    print(f"{YELLOW}3. LLM Runner Stream/Single Result Handling{RESET}")
    try:
        # Check the implementation
        with open("utils/llm_utils.py", "r") as f:
            content = f.read()
        
        # Check for __aiter__ handling
        has_aiter_check = "hasattr(result, \"__aiter__\")" in content
        all_passed &= test_result(
            "Checks for __aiter__ to detect streams",
            has_aiter_check
        )
        
        # Check for both async iteration and single result handling
        has_async_for = "async for" in content and "in result:" in content
        has_await_result = "await result" in content
        
        all_passed &= test_result(
            "Handles async iteration for streams",
            has_async_for
        )
        
        all_passed &= test_result(
            "Handles single result with await",
            has_await_result
        )
        
    except Exception as e:
        all_passed &= test_result("LLM runner test", False, str(e))
    
    print()
    
    # Test 4: Optional empty registry support
    print(f"{YELLOW}4. Optional Empty Registry Support{RESET}")
    try:
        from utils.registry import load_registry
        
        # Create temporary empty registry
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"agents": {}}, f)
            temp_path = f.name
        
        try:
            # Test without ALLOW_EMPTY_REGISTRY
            os.environ.pop("ALLOW_EMPTY_REGISTRY", None)
            try:
                load_registry(temp_path)
                test_result("Empty registry raises error by default", False)
                all_passed = False
            except ValueError as e:
                passed = "ALLOW_EMPTY_REGISTRY=1" in str(e)
                all_passed &= test_result(
                    "Empty registry raises helpful error",
                    passed,
                    str(e)[:80]
                )
            
            # Test with ALLOW_EMPTY_REGISTRY=1
            os.environ["ALLOW_EMPTY_REGISTRY"] = "1"
            try:
                agents = load_registry(temp_path)
                passed = agents == {}
                all_passed &= test_result(
                    "Empty registry allowed with ALLOW_EMPTY_REGISTRY=1",
                    passed
                )
            except Exception as e:
                all_passed &= test_result("Empty registry with flag", False, str(e))
            
            # Clean up
            os.environ.pop("ALLOW_EMPTY_REGISTRY", None)
        finally:
            Path(temp_path).unlink()
            
    except Exception as e:
        all_passed &= test_result("Empty registry test", False, str(e))
    
    print()
    
    # Test 5: URL normalization in registry
    print(f"{YELLOW}5. URL Normalization in Registry{RESET}")
    try:
        from utils.registry import load_registry, clear_cache
        
        # Clear cache first
        clear_cache()
        
        # Create registry with trailing slashes
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "agents": {
                    "test1": {"url": "http://example.com/"},
                    "test2": {"url": "http://example.com//"},
                    "test3": {"url": "http://example.com"}
                }
            }, f)
            temp_path = f.name
        
        try:
            agents = load_registry(temp_path)
            
            # All URLs should have trailing slashes removed
            all_normalized = all(
                not url["url"].endswith("/") 
                for url in agents.values()
            )
            
            all_passed &= test_result(
                "All URLs have trailing slashes removed",
                all_normalized,
                f"URLs: {[a['url'] for a in agents.values()]}"
            )
            
        finally:
            Path(temp_path).unlink()
            clear_cache()
            
    except Exception as e:
        all_passed &= test_result("URL normalization test", False, str(e))
    
    print()
    
    # Test 6: A2A client tolerant response parsing
    print(f"{YELLOW}6. A2A Client Tolerant Response Parsing{RESET}")
    try:
        # Check the implementation
        with open("utils/a2a_client.py", "r") as f:
            content = f.read()
        
        # Check for tolerant parsing features
        checks = [
            ("Checks content-type header", 'content-type' in content.lower()),
            ("Tries JSON parsing", 'json.loads(text)' in content),
            ("Wraps plain text as {'text': ...}", '{"text": text}' in content),
            ("Handles JSON decode errors", 'json.JSONDecodeError' in content)
        ]
        
        for desc, found in checks:
            all_passed &= test_result(desc, found)
            
    except Exception as e:
        all_passed &= test_result("Tolerant parsing test", False, str(e))
    
    print()
    
    # Test 7: Generation config adaptability
    print(f"{YELLOW}7. Generation Config Adaptability{RESET}")
    try:
        with open("utils/llm_utils.py", "r") as f:
            content = f.read()
        
        # Check for adaptive generation config
        has_try_except = "try:" in content and "generation_config" in content
        has_fallback = "generate_content_config" in content
        has_type_error = "except TypeError:" in content
        
        all_passed &= test_result(
            "Uses try/except for generation_config",
            has_try_except
        )
        
        all_passed &= test_result(
            "Falls back to generate_content_config",
            has_fallback
        )
        
        all_passed &= test_result(
            "Handles TypeError for version compatibility",
            has_type_error
        )
        
    except Exception as e:
        all_passed &= test_result("Generation config test", False, str(e))
    
    print()
    
    # Test 8: Capability field names (snake_case)
    print(f"{YELLOW}8. Capability Field Names{RESET}")
    try:
        with open("base.py", "r") as f:
            content = f.read()
        
        # Check for correct field names
        has_push_notifications = "push_notifications" in content
        no_camel_case = "pushNotifications" not in content
        
        all_passed &= test_result(
            "Uses push_notifications (snake_case)",
            has_push_notifications and no_camel_case
        )
        
    except Exception as e:
        all_passed &= test_result("Capability fields test", False, str(e))
    
    # Final summary
    print("\n" + "="*60)
    if all_passed:
        print(f"{GREEN}✓ ALL PRODUCTION FIXES VERIFIED!{RESET}")
        print("The template is production-ready for HTTP-only A2A calls")
        print("with automatic LLM provider selection.")
    else:
        print(f"{RED}✗ Some tests failed. Please review above.{RESET}")
    print("="*60 + "\n")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(test_production_fixes())
    sys.exit(0 if success else 1)