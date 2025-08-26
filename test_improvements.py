#!/usr/bin/env python3
"""
Test script to validate all improvements from the latest review.
Tests registry pass-through, message kinds, timeouts, warnings, and startup checks.
"""

import os
import sys
import json
import asyncio
import tempfile
from pathlib import Path

# Test colors
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

async def test_improvements():
    """Test all improvements from the latest review."""
    print("\n" + "="*60)
    print("Testing Latest Improvements")
    print("="*60 + "\n")
    
    all_passed = True
    
    # Test 1: Registry passes through raw URLs
    print(f"{YELLOW}1. Registry URL Pass-through{RESET}")
    try:
        from utils.registry import resolve_agent_url, clear_cache
        
        # Clear cache first
        clear_cache()
        
        # Test direct URL pass-through
        test_urls = [
            "http://example.com",
            "https://example.com/",
            "https://example.com/path",
        ]
        
        for url in test_urls:
            result = resolve_agent_url(url)
            expected = url.rstrip("/")
            passed = result == expected
            all_passed &= test_result(
                f"Pass-through: {url}",
                passed,
                f"Got: {result}"
            )
        
        # Test registry lookup still works
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "agents": {
                    "test-agent": {"url": "http://registered.com"}
                }
            }, f)
            temp_path = f.name
        
        try:
            result = resolve_agent_url("test-agent", temp_path)
            all_passed &= test_result(
                "Registry lookup still works",
                result == "http://registered.com"
            )
        finally:
            Path(temp_path).unlink()
            clear_cache()
            
    except Exception as e:
        all_passed &= test_result("Registry pass-through test", False, str(e))
    
    print()
    
    # Test 2: Message includes kind field
    print(f"{YELLOW}2. Message Kind Field{RESET}")
    try:
        # Check the a2a_client implementation
        with open("utils/a2a_client.py", "r") as f:
            content = f.read()
        
        has_kind = '"kind": "message"' in content
        all_passed &= test_result(
            "Outbound messages include kind: 'message'",
            has_kind
        )
        
        # Test actual message construction
        from utils.a2a_client import A2AClient
        client = A2AClient("http://test.com")
        
        # Mock the _request method to capture payload
        captured_payload = None
        async def mock_request(endpoint, payload, **kwargs):
            nonlocal captured_payload
            captured_payload = payload
            return {"text": "ok"}
        
        client._request = mock_request
        
        # Call and check payload
        await client.call_agent("test message")
        
        if captured_payload:
            msg = captured_payload.get("message", {})
            has_kind = msg.get("kind") == "message"
            all_passed &= test_result(
                "Message object has kind field",
                has_kind,
                f"Message: {json.dumps(msg, indent=2)[:100]}..."
            )
        
    except Exception as e:
        all_passed &= test_result("Message kind test", False, str(e))
    
    print()
    
    # Test 3: Timeout propagation
    print(f"{YELLOW}3. Timeout Propagation{RESET}")
    try:
        import inspect
        from base import A2AAgent
        
        # Check call_other_agent signature
        sig = inspect.signature(A2AAgent.call_other_agent)
        has_timeout_param = "timeout" in sig.parameters
        
        all_passed &= test_result(
            "call_other_agent has timeout parameter",
            has_timeout_param
        )
        
        # Check implementation passes timeout to client
        with open("base.py", "r") as f:
            content = f.read()
        
        passes_timeout = "timeout_sec=timeout" in content
        all_passed &= test_result(
            "Timeout is passed to A2AClient",
            passes_timeout
        )
        
    except Exception as e:
        all_passed &= test_result("Timeout propagation test", False, str(e))
    
    print()
    
    # Test 4: Rate-limited warnings
    print(f"{YELLOW}4. Rate-limited Legacy Warnings{RESET}")
    try:
        # Check implementation
        with open("base.py", "r") as f:
            content = f.read()
        
        checks = [
            ("Has _legacy_warnings tracking", "_legacy_warnings" in content),
            ("Has _MAX_LEGACY_WARNINGS limit", "_MAX_LEGACY_WARNINGS" in content),
            ("Has _LEGACY_WARN_INTERVAL", "_LEGACY_WARN_INTERVAL" in content),
            ("Has _log_legacy_warning method", "def _log_legacy_warning" in content),
            ("Checks A2A_WARN_LEGACY_PARTS env", "A2A_WARN_LEGACY_PARTS" in content),
            ("Logs structured hints", '"action": "migrate_to_kind_union"' in content)
        ]
        
        for desc, found in checks:
            all_passed &= test_result(desc, found)
            
    except Exception as e:
        all_passed &= test_result("Legacy warnings test", False, str(e))
    
    print()
    
    # Test 5: Runner shutdown improvements
    print(f"{YELLOW}5. Runner Shutdown Improvements{RESET}")
    try:
        with open("utils/llm_utils.py", "r") as f:
            content = f.read()
        
        checks = [
            ("Uses asyncio.wait_for with timeout", "asyncio.wait_for(runner.shutdown(), timeout=" in content),
            ("Handles TimeoutError", "except asyncio.TimeoutError:" in content),
            ("Handles CancelledError", "except asyncio.CancelledError:" in content),
            ("Uses asyncio.shield for cleanup", "asyncio.shield" in content),
            ("Logs shutdown completion", "Runner shutdown completed" in content),
            ("Logs timeout warnings", "Runner shutdown timeout" in content)
        ]
        
        for desc, found in checks:
            all_passed &= test_result(desc, found)
            
    except Exception as e:
        all_passed &= test_result("Runner shutdown test", False, str(e))
    
    print()
    
    # Test 6: Startup utilities
    print(f"{YELLOW}6. Startup Checks & Debug{RESET}")
    try:
        # Check startup.py exists and has required functions
        from utils.startup import check_http_endpoint, debug_agent_card, startup_checks
        
        all_passed &= test_result("Startup module exists with required functions", True)
        
        # Check integration in base.py
        with open("base.py", "r") as f:
            content = f.read()
        
        checks = [
            ("Base imports startup checks", "from utils.startup import" in content),
            ("Checks A2A_SKIP_STARTUP env", "A2A_SKIP_STARTUP" in content),
            ("Runs startup checks in __init__", "run_startup_checks(self)" in content)
        ]
        
        for desc, found in checks:
            all_passed &= test_result(desc, found)
        
        # Check startup.py features
        with open("utils/startup.py", "r") as f:
            startup_content = f.read()
        
        features = [
            ("HTTP endpoint self-check", "check_http_endpoint" in startup_content),
            ("Debug card output", "A2A_DEBUG_CARD" in startup_content),
            ("Validates protocol version", 'get("protocolVersion") == "0.3.0"' in startup_content),
            ("Checks base URL format", "not url.endswith" in startup_content)
        ]
        
        for desc, found in features:
            all_passed &= test_result(desc, found)
            
    except Exception as e:
        all_passed &= test_result("Startup checks test", False, str(e))
    
    # Final summary
    print("\n" + "="*60)
    if all_passed:
        print(f"{GREEN}✓ ALL IMPROVEMENTS VERIFIED!{RESET}")
        print("The template now includes:")
        print("  • Registry URL pass-through")
        print("  • Explicit message kind discriminators")
        print("  • Timeout propagation throughout")
        print("  • Rate-limited legacy warnings")
        print("  • Bounded runner shutdown")
        print("  • Startup self-checks and debug output")
    else:
        print(f"{RED}✗ Some tests failed. Please review above.{RESET}")
    print("="*60 + "\n")
    
    return all_passed

if __name__ == "__main__":
    # Set env to skip actual startup checks during test
    os.environ["A2A_SKIP_STARTUP"] = "1"
    
    success = asyncio.run(test_improvements())
    sys.exit(0 if success else 1)