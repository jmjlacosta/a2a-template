#!/usr/bin/env python3
"""
Pattern Search Agent - Searches documents with regex patterns.
Returns structured locations where patterns are found in the document.
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base import A2AAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill


# Pydantic models for structured grep operations
class GrepRequest(BaseModel):
    """Input structure for grep agent."""
    patterns: List[str] = Field(description="List of regex patterns to search")
    document_content: str = Field(description="Document content to search in")
    case_sensitive: bool = Field(default=False, description="Whether search is case sensitive")
    max_matches_per_pattern: int = Field(default=50, description="Max matches per pattern")
    context_lines: int = Field(default=3, description="Lines of context around matches")


class MatchLocation(BaseModel):
    """Single match location in document."""
    pattern: str = Field(description="Pattern that matched")
    line_number: int = Field(description="Line number of match (1-indexed)")
    line_text: str = Field(description="Text of the line containing match")
    match_text: str = Field(description="The actual matched text")
    match_start: int = Field(description="Start position in line")
    match_end: int = Field(description="End position in line")
    context: List[str] = Field(description="Context lines around match")
    context_start_line: int = Field(description="Starting line number of context")
    # For single-line documents
    match_position: Optional[int] = Field(default=None, description="Absolute position in document")
    single_line_doc: bool = Field(default=False, description="Whether document is single line")


class PatternResult(BaseModel):
    """Results for a single pattern."""
    pattern: str = Field(description="The pattern searched")
    matches: List[MatchLocation] = Field(description="All match locations")
    match_count: int = Field(description="Total number of matches found")
    error: Optional[str] = Field(default=None, description="Error if pattern failed")


class GrepResult(BaseModel):
    """Complete grep search results."""
    total_patterns: int = Field(description="Number of patterns searched")
    successful_searches: int = Field(description="Number of successful pattern searches")
    total_matches: int = Field(description="Total matches across all patterns")
    pattern_results: List[PatternResult] = Field(description="Results for each pattern")
    document_lines: int = Field(description="Number of lines in document")
    is_single_line: bool = Field(description="Whether document is single-line")


class GrepAgent(A2AAgent):
    """Pattern search agent that returns match locations."""
    
    def get_agent_name(self) -> str:
        """Return the agent's name."""
        return "Pattern Search Agent"
    
    def get_agent_description(self) -> str:
        """Return detailed agent description."""
        return (
            "Searches documents using regex patterns and returns structured "
            "locations where patterns are found, including line numbers and context."
        )
    
    def get_agent_version(self) -> str:
        """Return agent version."""
        return "3.0.0"
    
    def get_system_instruction(self) -> str:
        """Return the system instruction for pattern searching."""
        return """You are a pattern search specialist. Search documents for regex patterns and return match locations.

When given patterns and document content:
1. Search for each pattern in the document
2. Return exact locations (line numbers, positions)
3. Include context around matches
4. Handle both single-line and multi-line documents

Return results using the GrepResult structure with all match locations."""
    
    async def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process grep request and return match locations.
        
        Args:
            message: Either JSON string with GrepRequest structure or plain text
            
        Returns:
            Dictionary with match locations for DataPart
        """
        # Parse input
        try:
            if isinstance(message, str) and message.startswith('{'):
                data = json.loads(message)
            elif isinstance(message, dict):
                data = message
            else:
                # Plain text message - treat as document with default patterns
                data = {
                    "patterns": [r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"],  # Date pattern as example
                    "document_content": message,
                    "case_sensitive": False
                }
            
            # Create request model
            request = GrepRequest(**data)
            
        except Exception as e:
            self.logger.error(f"Failed to parse request: {e}")
            # Return empty result on parse error
            error_result = GrepResult(
                total_patterns=0,
                successful_searches=0,
                total_matches=0,
                pattern_results=[],
                document_lines=0,
                is_single_line=False
            )
            return error_result.model_dump()
        
        # Perform searches
        result = self._search_patterns(request)
        
        # Return as dict for DataPart
        return result.model_dump()
    
    def _search_patterns(self, request: GrepRequest) -> GrepResult:
        """
        Execute pattern searches on document.
        
        Args:
            request: Validated grep request
            
        Returns:
            GrepResult with all match locations
        """
        # Split document into lines
        lines = request.document_content.splitlines()
        is_single_line = len(lines) <= 3 and any(len(line) > 1000 for line in lines)
        
        # Initialize result
        pattern_results = []
        total_matches = 0
        successful_searches = 0
        
        # Search each pattern
        for pattern in request.patterns:
            pattern_result = self._search_single_pattern(
                pattern=pattern,
                lines=lines,
                case_sensitive=request.case_sensitive,
                max_matches=request.max_matches_per_pattern,
                context_lines=request.context_lines,
                is_single_line=is_single_line,
                full_content=request.document_content
            )
            
            pattern_results.append(pattern_result)
            if pattern_result.error is None:
                successful_searches += 1
                total_matches += pattern_result.match_count
        
        return GrepResult(
            total_patterns=len(request.patterns),
            successful_searches=successful_searches,
            total_matches=total_matches,
            pattern_results=pattern_results,
            document_lines=len(lines),
            is_single_line=is_single_line
        )
    
    def _search_single_pattern(
        self,
        pattern: str,
        lines: List[str],
        case_sensitive: bool,
        max_matches: int,
        context_lines: int,
        is_single_line: bool,
        full_content: str
    ) -> PatternResult:
        """
        Search for a single pattern in document lines.
        
        Returns:
            PatternResult with all matches for this pattern
        """
        matches = []
        
        try:
            # Handle case sensitivity and (?i) prefix
            flags = 0 if case_sensitive else re.IGNORECASE
            clean_pattern = pattern
            
            if pattern.startswith("(?i)"):
                clean_pattern = pattern[4:]
                flags = re.IGNORECASE
            
            # Compile regex
            regex = re.compile(clean_pattern, flags)
            
            # Search through lines
            match_count = 0
            for i, line in enumerate(lines):
                if match_count >= max_matches:
                    break
                
                # Find all matches in this line
                for match in regex.finditer(line):
                    if match_count >= max_matches:
                        break
                    
                    # Get context
                    context_start = max(0, i - context_lines)
                    context_end = min(len(lines), i + context_lines + 1)
                    context = [lines[j].strip() for j in range(context_start, context_end)]
                    
                    # Create match location
                    match_loc = MatchLocation(
                        pattern=pattern,
                        line_number=i + 1,
                        line_text=line.strip(),
                        match_text=match.group(),
                        match_start=match.start(),
                        match_end=match.end(),
                        context=context,
                        context_start_line=context_start + 1,
                        single_line_doc=is_single_line
                    )
                    
                    # Add character position for single-line documents
                    if is_single_line:
                        # Calculate absolute character position
                        chars_before = sum(len(lines[j]) + 1 for j in range(i))  # +1 for newline
                        match_loc.match_position = chars_before + match.start()
                    
                    matches.append(match_loc)
                    match_count += 1
            
            return PatternResult(
                pattern=pattern,
                matches=matches,
                match_count=len(matches),
                error=None
            )
            
        except re.error as e:
            # Pattern compilation error
            return PatternResult(
                pattern=pattern,
                matches=[],
                match_count=0,
                error=f"Invalid regex: {str(e)}"
            )
        except Exception as e:
            # Other errors
            return PatternResult(
                pattern=pattern,
                matches=[],
                match_count=0,
                error=f"Search error: {str(e)}"
            )
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """Return agent skills for the AgentCard."""
        return [
            AgentSkill(
                id="search_patterns",
                name="Search Patterns",
                description="Search document for regex patterns and return match locations",
                tags=["search", "regex", "pattern-matching", "locations"],
                examples=[
                    "Find all dates in document",
                    "Search for medical terms",
                    "Locate section headers",
                    "Find all numbers with units"
                ],
                input_modes=["application/json"],
                output_modes=["application/json"]
            )
        ]
    
    def supports_streaming(self) -> bool:
        """Enable streaming for real-time updates."""
        return True


# Module-level app creation for HealthUniverse deployment
agent = GrepAgent()
agent_card = agent.create_agent_card()
task_store = InMemoryTaskStore()
request_handler = DefaultRequestHandler(
    agent_executor=agent,
    task_store=task_store
)

# Create the app - MUST be named 'app' for HealthUniverse
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
).build()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8003))
    
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    print(f"🔍 Returns structured match locations")
    print("\n📝 Example input:")
    print('  {"patterns": ["\\\\bdate\\\\b", "\\\\d+"], "document_content": "text to search"}')
    
    uvicorn.run(app, host="0.0.0.0", port=port)