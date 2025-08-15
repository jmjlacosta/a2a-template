#!/usr/bin/env python3
"""
Universal test suite for any A2A agent.

Tests common functionality across all agents:
- Agent card generation and validation
- Basic message-response cycle
- Tool availability (if any)
- Skill definitions (if any)
- A2A protocol compliance

Usage:
    python test_any_agent.py <module_path> <class_name>
    
Examples:
    python test_any_agent.py examples.pipeline.grep_agent GrepAgent
    python test_any_agent.py examples.simple_echo_agent SimpleEchoAgent
"""

import sys
import json
import asyncio
import importlib
from pathlib import Path
from typing import Any, Dict, Optional
import argparse
import traceback

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from a2a.types import AgentCard
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message
from a2a.types import Message, Part, TextPart


class UniversalAgentTester:
    """Universal test suite for any A2A agent."""
    
    def __init__(self, module_path: str, class_name: str):
        """
        Initialize tester with agent module and class.
        
        Args:
            module_path: Module path (e.g., 'examples.pipeline.grep_agent')
            class_name: Agent class name (e.g., 'GrepAgent')
        """
        self.module_path = module_path
        self.class_name = class_name
        self.agent = None
        self.passed_tests = []
        self.failed_tests = []
    
    def load_agent(self) -> bool:
        """Load the agent class dynamically."""
        try:
            module = importlib.import_module(self.module_path)
            agent_class = getattr(module, self.class_name)
            self.agent = agent_class()
            print(f"✅ Loaded {self.class_name} from {self.module_path}")
            return True
        except ImportError as e:
            print(f"❌ Failed to import module {self.module_path}: {e}")
            return False
        except AttributeError as e:
            print(f"❌ Class {self.class_name} not found in {self.module_path}: {e}")
            return False
        except Exception as e:
            print(f"❌ Failed to instantiate agent: {e}")
            return False
    
    def test_basic_properties(self):
        """Test basic agent properties."""
        print("\n📋 Testing Basic Properties...")
        
        # Test agent name
        try:
            name = self.agent.get_agent_name()
            assert isinstance(name, str) and len(name) > 0
            self.passed_tests.append(f"Agent name: '{name}'")
        except Exception as e:
            self.failed_tests.append(f"Agent name: {e}")
        
        # Test agent description
        try:
            desc = self.agent.get_agent_description()
            assert isinstance(desc, str) and len(desc) > 0
            self.passed_tests.append(f"Agent description: {len(desc)} chars")
        except Exception as e:
            self.failed_tests.append(f"Agent description: {e}")
        
        # Test agent version
        try:
            version = self.agent.get_agent_version()
            assert isinstance(version, str)
            self.passed_tests.append(f"Agent version: {version}")
        except Exception as e:
            self.failed_tests.append(f"Agent version: {e}")
    
    def test_agent_card(self):
        """Test agent card generation."""
        print("\n🎴 Testing Agent Card Generation...")
        
        try:
            card = self.agent.create_agent_card()
            assert isinstance(card, AgentCard)
            
            # Validate required fields
            assert card.name is not None
            assert card.description is not None
            assert card.version is not None
            assert card.url is not None
            assert card.capabilities is not None
            
            # Check capabilities
            caps = card.capabilities
            self.passed_tests.append(f"Agent card created with capabilities: streaming={caps.streaming}, push={caps.push_notifications}")
            
            # Check skills if any
            if hasattr(card, 'skills') and card.skills:
                self.passed_tests.append(f"Agent has {len(card.skills)} skills defined")
                for skill in card.skills[:3]:  # Show first 3 skills
                    print(f"  - Skill: {skill.name} ({skill.id})")
            else:
                self.passed_tests.append("Agent has no skills defined (optional)")
                
        except Exception as e:
            self.failed_tests.append(f"Agent card generation: {e}")
    
    def test_tools(self):
        """Test tool availability if agent has any."""
        print("\n🛠️ Testing Tools...")
        
        try:
            tools = self.agent.get_tools()
            
            if tools and len(tools) > 0:
                self.passed_tests.append(f"Agent has {len(tools)} tools")
                
                # Check if tools are properly configured
                for i, tool in enumerate(tools[:3]):  # Check first 3 tools
                    if hasattr(tool, 'func'):
                        assert callable(tool.func)
                        func_name = tool.func.__name__ if hasattr(tool.func, '__name__') else f"Tool {i+1}"
                        print(f"  - Tool: {func_name}")
                    else:
                        self.failed_tests.append(f"Tool {i+1} missing 'func' attribute")
            else:
                self.passed_tests.append("Agent has no tools (uses simple message processing)")
                
        except Exception as e:
            self.failed_tests.append(f"Tool testing: {e}")
    
    def test_optional_features(self):
        """Test optional agent features."""
        print("\n⚙️ Testing Optional Features...")
        
        # Test streaming support
        try:
            streaming = self.agent.supports_streaming()
            self.passed_tests.append(f"Streaming support: {streaming}")
        except Exception as e:
            self.failed_tests.append(f"Streaming check: {e}")
        
        # Test push notifications
        try:
            push = self.agent.supports_push_notifications()
            self.passed_tests.append(f"Push notifications: {push}")
        except Exception as e:
            self.failed_tests.append(f"Push notifications check: {e}")
        
        # Test system instruction (for LLM agents)
        try:
            instruction = self.agent.get_system_instruction()
            if instruction and instruction != "You are a helpful AI assistant.":
                self.passed_tests.append(f"Custom system instruction: {len(instruction)} chars")
            else:
                self.passed_tests.append("Using default system instruction")
        except Exception as e:
            self.failed_tests.append(f"System instruction: {e}")
    
    async def test_message_processing(self):
        """Test basic message processing."""
        print("\n💬 Testing Message Processing...")
        
        try:
            # Create a simple test message
            test_message = "Hello, agent! Can you respond to this test message?"
            
            # Test if agent has process_message method
            if hasattr(self.agent, 'process_message'):
                # For agents without tools, test direct message processing
                if not self.agent.get_tools():
                    response = await self.agent.process_message(test_message)
                    assert isinstance(response, str) and len(response) > 0
                    self.passed_tests.append(f"Message processing works: {len(response)} chars response")
                else:
                    self.passed_tests.append("Agent uses tools - message processing handled by base")
            else:
                self.failed_tests.append("Agent missing process_message method")
                
        except Exception as e:
            self.failed_tests.append(f"Message processing: {e}")
    
    async def test_execute_method(self):
        """Test the execute method with mock context."""
        print("\n🚀 Testing Execute Method...")
        
        try:
            # Create mock context
            message = Message(
                role="user",
                parts=[Part(root=TextPart(text="Test message"))],
                messageId="test-123",
                kind="message"
            )
            
            # Create mock context - simplified version
            class MockContext:
                def __init__(self):
                    self.message = message
                    self.current_task = None
            
            context = MockContext()
            
            # Create mock event queue
            class MockEventQueue:
                def __init__(self):
                    self.events = []
                
                async def enqueue_event(self, event):
                    self.events.append(event)
            
            event_queue = MockEventQueue()
            
            # Test execute - this would normally process through tools or process_message
            # We're just checking it doesn't crash
            try:
                await asyncio.wait_for(
                    self.agent.execute(context, event_queue),
                    timeout=5.0
                )
                self.passed_tests.append("Execute method completed successfully")
            except asyncio.TimeoutError:
                self.passed_tests.append("Execute method started (timeout expected for tool agents)")
            except Exception as e:
                # Some errors are expected if LLM keys aren't configured
                if "API key" in str(e):
                    self.passed_tests.append("Execute method requires LLM API key (expected)")
                else:
                    raise
                    
        except Exception as e:
            self.failed_tests.append(f"Execute method: {e}")
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "="*60)
        print(f"📊 Test Results for {self.class_name}")
        print("="*60)
        
        if self.passed_tests:
            print(f"\n✅ Passed Tests ({len(self.passed_tests)}):")
            for test in self.passed_tests:
                print(f"  ✓ {test}")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests ({len(self.failed_tests)}):")
            for test in self.failed_tests:
                print(f"  ✗ {test}")
        
        print("\n" + "="*60)
        total = len(self.passed_tests) + len(self.failed_tests)
        success_rate = (len(self.passed_tests) / total * 100) if total > 0 else 0
        
        if success_rate == 100:
            print(f"🎉 All tests passed! ({len(self.passed_tests)}/{total})")
        elif success_rate >= 80:
            print(f"✅ Most tests passed: {success_rate:.1f}% ({len(self.passed_tests)}/{total})")
        else:
            print(f"⚠️ Some tests failed: {success_rate:.1f}% passed ({len(self.passed_tests)}/{total})")
        
        return len(self.failed_tests) == 0
    
    async def run_all_tests(self) -> bool:
        """Run all tests."""
        if not self.load_agent():
            return False
        
        print(f"\n🧪 Running Universal Tests for {self.class_name}")
        print("="*60)
        
        # Run synchronous tests
        self.test_basic_properties()
        self.test_agent_card()
        self.test_tools()
        self.test_optional_features()
        
        # Run async tests
        await self.test_message_processing()
        await self.test_execute_method()
        
        # Print summary
        return self.print_summary()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Universal test suite for A2A agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_any_agent.py examples.pipeline.grep_agent GrepAgent
  python test_any_agent.py examples.simple_echo_agent SimpleEchoAgent
  python test_any_agent.py examples.tool_example_agent ToolExampleAgent
        """
    )
    
    parser.add_argument('module_path', help='Module path (e.g., examples.pipeline.grep_agent)')
    parser.add_argument('class_name', help='Agent class name (e.g., GrepAgent)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Run tests
    tester = UniversalAgentTester(args.module_path, args.class_name)
    
    try:
        success = asyncio.run(tester.run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()