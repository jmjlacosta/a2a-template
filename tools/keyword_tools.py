"""
Keyword generation tools - simplified for single-purpose LLM pattern generation.
The actual LLM call and Pydantic validation happens in the agent.
"""
import json
from typing import List, Optional
from google.adk.tools import FunctionTool


def generate_keyword_patterns(
    document_preview: str,
    focus_areas: Optional[List[str]] = None,
    max_patterns: int = 30
) -> str:
    """
    Generate keyword patterns from document preview using LLM.
    
    This function prepares the request for the LLM to generate patterns.
    The actual LLM call and pattern generation happens in the agent executor.
    
    Args:
        document_preview: First lines of the document to analyze
        focus_areas: Specific areas to focus on (clinical_summary, dates, etc.)
        max_patterns: Maximum number of patterns to generate
        
    Returns:
        JSON string with pattern generation request for LLM processing
    """
    if not focus_areas:
        focus_areas = ["clinical_summary", "dates", "medications", "diagnoses", "procedures"]
    
    # Limit preview to reasonable size
    preview_lines = document_preview.split('\n')[:30]
    preview_text = '\n'.join(preview_lines)
    
    # Build request for LLM processing
    request = {
        "action": "generate_patterns",
        "preview": preview_text,
        "focus_areas": focus_areas,
        "max_patterns": max_patterns,
        "instructions": f"""Analyze this medical document preview and generate regex patterns.

Focus Areas: {', '.join(focus_areas)}

CRITICAL: Generate patterns to find:
1. ALL dates and temporal markers
2. Clinical summary and assessment sections
3. Medical terminology specific to this document
4. Document structure and section headers

Requirements:
- Use ripgrep-compatible regex syntax
- Include case-insensitive flags (?i) where appropriate
- Generate REAL patterns based on the actual document content
- NO placeholder or generic patterns
- Maximum {max_patterns} patterns total
- Prioritize: {', '.join(focus_areas[:3])}"""
    }
    
    return json.dumps(request, indent=2)


# Create FunctionTool instance for Google ADK
generate_patterns_tool = FunctionTool(func=generate_keyword_patterns)

# Export simplified tool list
KEYWORD_TOOLS = [
    generate_patterns_tool
]