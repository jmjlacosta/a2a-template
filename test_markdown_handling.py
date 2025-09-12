#!/usr/bin/env python3
"""
Test suite for markdown-as-TextPart requirement.
CRITICAL: Validates that markdown content is ALWAYS sent as TextPart, not FilePart.
"""

import asyncio
import json
import sys
import os
from typing import Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from a2a.types import TextPart, DataPart, FilePart

# Import directly from message_utils module
import utils.message_utils as msg_utils
from base import A2AAgent


class TestMarkdownAgent(A2AAgent):
    """Test agent for validating markdown handling."""
    
    def get_agent_name(self) -> str:
        return "Markdown Test Agent"
    
    def get_agent_description(self) -> str:
        return "Tests markdown-as-TextPart handling"
    
    async def process_message(self, message: str) -> str:
        return "Test response"


def test_markdown_detection():
    """Test that markdown content is correctly detected."""
    print("\n=== Testing Markdown Detection ===")
    
    # Test markdown file extension
    assert msg_utils.detect_content_type("", "README.md") == "text/markdown"
    assert msg_utils.detect_content_type("", "CHANGELOG.md") == "text/markdown"
    print("✅ Markdown file extensions detected correctly")
    
    # Test markdown content detection
    markdown_content = """
# This is a heading
## Subheading
- List item
- [ ] Todo item
**Bold text**
```python
code block
```
    """
    assert msg_utils.detect_content_type(markdown_content) == "text/markdown"
    print("✅ Markdown content patterns detected correctly")
    
    # Test other text formats
    assert msg_utils.detect_content_type("", "file.txt") == "text/plain"
    assert msg_utils.detect_content_type("", "data.json") == "application/json"
    assert msg_utils.detect_content_type('{"key": "value"}') == "application/json"
    print("✅ Other text formats detected correctly")


def test_markdown_as_textpart():
    """Test that markdown files are ALWAYS created as TextPart."""
    print("\n=== Testing Markdown as TextPart ===")
    
    # Test markdown file with .md extension
    markdown_content = "# Heading\n\nThis is markdown content."
    part = msg_utils.create_part_from_file(markdown_content, "README.md")
    
    assert isinstance(part, TextPart), f"Expected TextPart, got {type(part)}"
    assert part.kind == "text"
    assert part.text == markdown_content
    assert hasattr(part, 'metadata') and part.metadata and part.metadata.get('contentType') == "text/markdown"
    print("✅ Markdown file created as TextPart with correct metadata")
    
    # Test markdown content as bytes
    markdown_bytes = markdown_content.encode('utf-8')
    part_bytes = msg_utils.create_part_from_file(markdown_bytes, "README.md")
    
    assert isinstance(part_bytes, TextPart), f"Expected TextPart for bytes, got {type(part_bytes)}"
    assert part_bytes.kind == "text"
    assert part_bytes.text == markdown_content
    print("✅ Markdown bytes converted to TextPart")
    
    # Test that binary files are still FilePart
    binary_content = b'\x89PNG\r\n\x1a\n'  # PNG header
    part_binary = msg_utils.create_part_from_file(binary_content, "image.png")
    
    assert isinstance(part_binary, FilePart), f"Expected FilePart for binary, got {type(part_binary)}"
    assert part_binary.kind == "file"
    print("✅ Binary files still created as FilePart")


def test_is_text_content():
    """Test the is_text_content function for markdown."""
    print("\n=== Testing is_text_content ===")
    
    # CRITICAL: Markdown files must ALWAYS be text
    assert msg_utils.is_text_content("", "README.md") == True
    assert msg_utils.is_text_content("", "CHANGELOG.md") == True
    assert msg_utils.is_text_content("", "docs/guide.md") == True
    print("✅ Markdown files identified as text content")
    
    # Other text files
    assert msg_utils.is_text_content("", "script.js") == True
    assert msg_utils.is_text_content("", "config.json") == True
    assert msg_utils.is_text_content("", "styles.css") == True
    print("✅ Other text files identified correctly")
    
    # Binary files
    assert msg_utils.is_text_content("", "image.png") == False
    assert msg_utils.is_text_content("", "video.mp4") == False
    assert msg_utils.is_text_content("", "app.exe") == False
    print("✅ Binary files identified correctly")


async def test_agent_artifact_creation():
    """Test that the agent creates markdown artifacts correctly."""
    print("\n=== Testing Agent Artifact Creation ===")
    
    agent = TestMarkdownAgent()
    
    # Test markdown content creation
    markdown_content = """
# Test Report
    
## Summary
This is a test report in markdown format.
    
## Results
- ✅ Test 1: Passed
- ✅ Test 2: Passed
- ❌ Test 3: Failed
    
## Code Example
```python
def test():
    return "success"
```
    """
    
    # Test the create_part_from_content method
    part = agent.create_part_from_content(
        markdown_content,
        filename="report.md"
    )
    
    assert isinstance(part, TextPart), f"Expected TextPart for markdown, got {type(part)}"
    assert part.kind == "text"
    assert part.text == markdown_content
    print("✅ Agent creates markdown content as TextPart")
    
    # Test with various content types
    json_data = {"status": "success", "count": 42}
    json_part = agent.create_part_from_content(json_data)
    # JSON dict without filename should be DataPart
    assert isinstance(json_part, (DataPart, TextPart)), f"JSON dict should be DataPart or TextPart, got {type(json_part)}"
    if isinstance(json_part, TextPart):
        # If it's TextPart, it should contain JSON string
        import json
        assert json.loads(json_part.text) == json_data, "TextPart should contain valid JSON"
    print("✅ Agent creates JSON data properly")
    
    text_content = "Plain text content"
    text_part = agent.create_part_from_content(text_content)
    assert isinstance(text_part, TextPart), "Plain text should be TextPart"
    print("✅ Agent creates plain text as TextPart")


def test_edge_cases():
    """Test edge cases for markdown handling."""
    print("\n=== Testing Edge Cases ===")
    
    # Empty markdown file
    part = msg_utils.create_part_from_file("", "empty.md")
    assert isinstance(part, TextPart)
    assert part.text == ""
    print("✅ Empty markdown file handled correctly")
    
    # Large markdown file
    large_content = "# Header\n" + ("Line of text\n" * 1000)
    part = msg_utils.create_part_from_file(large_content, "large.md")
    assert isinstance(part, TextPart)
    assert len(part.text) > 1000
    print("✅ Large markdown file handled correctly")
    
    # Markdown with special characters
    special_content = "# Test 测试 🚀\n\n```\n<html>test</html>\n```"
    part = msg_utils.create_part_from_file(special_content, "special.md")
    assert isinstance(part, TextPart)
    assert "🚀" in part.text
    print("✅ Special characters in markdown handled correctly")
    
    # File without extension but markdown content
    markdown_like = "# This looks like markdown\n\n- Item 1\n- Item 2"
    part = msg_utils.create_part_from_file(markdown_like, "README")
    # Should still detect as text based on content
    assert isinstance(part, TextPart)
    print("✅ Markdown content without .md extension handled as text")


def run_all_tests():
    """Run all test cases."""
    print("=" * 50)
    print("MARKDOWN HANDLING TEST SUITE")
    print("CRITICAL: Markdown MUST be sent as TextPart")
    print("=" * 50)
    
    try:
        # Synchronous tests
        test_markdown_detection()
        test_markdown_as_textpart()
        test_is_text_content()
        test_edge_cases()
        
        # Async tests
        asyncio.run(test_agent_artifact_creation())
        
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED!")
        print("Markdown-as-TextPart requirement validated.")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()