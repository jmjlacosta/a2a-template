#!/usr/bin/env python3
"""
Context Extractor Agent - Extracts meaningful text chunks from documents.
Handles both multi-line and single-line documents with intelligent boundary detection.
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base import A2AAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill


# Pydantic models for structured chunk operations
class MatchInfo(BaseModel):
    """Information about a match from grep agent."""
    line_number: int = Field(description="Line number of match")
    line_text: str = Field(description="Text of the line")
    match_text: str = Field(description="Actual matched text")
    pattern: Optional[str] = Field(default=None, description="Pattern that matched")
    match_position: Optional[int] = Field(default=None, description="Character position for single-line docs")
    single_line_doc: bool = Field(default=False, description="Whether document is single-line")
    context: Optional[List[str]] = Field(default=None, description="Context lines")


class ChunkRequest(BaseModel):
    """Request for chunk extraction."""
    match_info: Dict[str, Any] = Field(description="Match information from grep")
    document_content: Optional[str] = Field(default=None, description="Full document content")
    lines_before: int = Field(default=5, description="Lines of context before match")
    lines_after: int = Field(default=5, description="Lines of context after match")
    use_boundary_detection: bool = Field(default=True, description="Use intelligent boundaries")


class ChunkMetadata(BaseModel):
    """Metadata about chunk extraction."""
    extraction_method: str = Field(description="Method used: line-based or character-based")
    single_line_document: bool = Field(description="Whether document is single-line")
    chunk_size_chars: int = Field(description="Size of chunk in characters")
    chunk_size_lines: Optional[int] = Field(default=None, description="Size in lines if applicable")
    boundaries_used: bool = Field(description="Whether intelligent boundaries were used")
    sentence_boundaries: bool = Field(default=False, description="Whether sentence boundaries were used")


class ExtractedChunk(BaseModel):
    """Single extracted chunk."""
    content: str = Field(description="The extracted text chunk")
    start_position: Optional[int] = Field(default=None, description="Start character position")
    end_position: Optional[int] = Field(default=None, description="End character position")
    start_line: Optional[int] = Field(default=None, description="Start line number")
    end_line: Optional[int] = Field(default=None, description="End line number")
    match_info: Dict[str, Any] = Field(description="Original match information")
    metadata: ChunkMetadata = Field(description="Extraction metadata")


class ChunkResult(BaseModel):
    """Result of chunk extraction."""
    chunks: List[ExtractedChunk] = Field(description="Extracted chunks")
    total_chunks: int = Field(description="Number of chunks extracted")
    deduplication_applied: bool = Field(description="Whether chunks were deduplicated")
    merging_applied: bool = Field(description="Whether overlapping chunks were merged")
    document_type: str = Field(description="Type: single-line or multi-line")


class ChunkAgent(A2AAgent):
    """Context extraction agent with intelligent chunking."""
    
    def get_agent_name(self) -> str:
        """Return the agent's name."""
        return "Context Extractor"
    
    def get_agent_description(self) -> str:
        """Return detailed agent description."""
        return (
            "Extracts meaningful text chunks from documents using intelligent boundary detection. "
            "Handles single-line documents with sentence boundaries and multi-line documents "
            "with section boundaries. Automatically deduplicates and merges overlapping chunks."
        )
    
    def get_agent_version(self) -> str:
        """Return agent version."""
        return "3.0.0"
    
    def get_system_instruction(self) -> str:
        """Return the system instruction for chunk extraction."""
        return """You are a document chunk extraction specialist. Extract meaningful chunks of text around search matches.

For single-line documents:
- Use sentence boundaries for natural breaks
- Extract context around match positions
- Preserve complete thoughts and statements

For multi-line documents:
- Detect section boundaries
- Preserve semantic units
- Include complete paragraphs

Always:
- Deduplicate overlapping chunks
- Merge adjacent chunks when appropriate
- Return structured chunk data"""
    
    async def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process chunk extraction request.
        
        Args:
            message: JSON with match_info and optional document_content
            
        Returns:
            Dictionary with extracted chunks for DataPart
        """
        # Parse input
        try:
            if isinstance(message, str) and message.startswith('{'):
                data = json.loads(message)
            elif isinstance(message, dict):
                data = message
            else:
                # Plain text - create minimal request
                data = {
                    "match_info": {"line_number": 1, "match_text": ""},
                    "document_content": message
                }
            
            # Create request model
            request = ChunkRequest(**data)
            
        except Exception as e:
            self.logger.error(f"Failed to parse request: {e}")
            # Return empty result
            error_result = ChunkResult(
                chunks=[],
                total_chunks=0,
                deduplication_applied=False,
                merging_applied=False,
                document_type="unknown"
            )
            return error_result.model_dump()
        
        # Extract chunks
        result = self._extract_chunks(request)
        
        # Return as dict for DataPart
        return result.model_dump()
    
    def _extract_chunks(self, request: ChunkRequest) -> ChunkResult:
        """
        Extract chunks based on request.
        
        Args:
            request: Validated chunk request
            
        Returns:
            ChunkResult with extracted chunks
        """
        # Get document content
        if request.document_content:
            content = request.document_content
        else:
            # Try to get from match_info if available
            match_info = request.match_info
            if "file_content" in match_info:
                content = match_info["file_content"]
            else:
                # No content available
                self.logger.warning("No document content provided")
                return ChunkResult(
                    chunks=[],
                    total_chunks=0,
                    deduplication_applied=False,
                    merging_applied=False,
                    document_type="unknown"
                )
        
        # Detect document type
        is_single_line = self._is_single_line_document(content)
        
        if is_single_line:
            # Use character-based extraction for single-line docs
            chunk = self._extract_character_chunk(
                content=content,
                match_info=request.match_info,
                context_chars=request.lines_before * 80  # Approximate chars per line
            )
        else:
            # Use line-based extraction for multi-line docs
            chunk = self._extract_line_chunk(
                content=content,
                match_info=request.match_info,
                lines_before=request.lines_before,
                lines_after=request.lines_after,
                use_boundaries=request.use_boundary_detection
            )
        
        # Create result
        return ChunkResult(
            chunks=[chunk] if chunk else [],
            total_chunks=1 if chunk else 0,
            deduplication_applied=False,
            merging_applied=False,
            document_type="single-line" if is_single_line else "multi-line"
        )
    
    def _is_single_line_document(self, content: str) -> bool:
        """Check if document is essentially single-line."""
        lines = content.splitlines()
        
        # Very few lines with at least one very long line
        if len(lines) <= 3:
            for line in lines:
                if len(line) > 1000:
                    return True
        
        # Very low newline ratio
        newline_ratio = content.count('\n') / max(len(content), 1)
        if newline_ratio < 0.001:
            return True
        
        return False
    
    def _extract_character_chunk(
        self,
        content: str,
        match_info: Dict[str, Any],
        context_chars: int = 500
    ) -> Optional[ExtractedChunk]:
        """
        Extract chunk using character positions for single-line documents.
        
        Uses sentence boundaries for natural breaks.
        """
        # Get match position
        match_position = match_info.get("match_position")
        if match_position is None:
            # Try to find match text in content
            match_text = match_info.get("match_text", "")
            if match_text:
                match_position = content.find(match_text)
            
            if match_position == -1 or match_position is None:
                # Default to middle of content
                match_position = len(content) // 2
        
        # Find sentence boundaries
        start_pos, end_pos = self._find_sentence_boundaries(
            content=content,
            center_pos=match_position,
            context_chars=context_chars
        )
        
        # Extract chunk
        chunk_text = content[start_pos:end_pos].strip()
        
        # Create metadata
        metadata = ChunkMetadata(
            extraction_method="character-based",
            single_line_document=True,
            chunk_size_chars=len(chunk_text),
            boundaries_used=True,
            sentence_boundaries=True
        )
        
        return ExtractedChunk(
            content=chunk_text,
            start_position=start_pos,
            end_position=end_pos,
            match_info=match_info,
            metadata=metadata
        )
    
    def _find_sentence_boundaries(
        self,
        content: str,
        center_pos: int,
        context_chars: int
    ) -> Tuple[int, int]:
        """
        Find natural sentence boundaries around a position.
        
        Returns:
            Tuple of (start_pos, end_pos)
        """
        # Initial boundaries
        start_pos = max(0, center_pos - context_chars)
        end_pos = min(len(content), center_pos + context_chars)
        
        # Look for sentence start
        sentence_starts = []
        # Search backward for sentence endings
        for i in range(start_pos, max(0, start_pos - 200), -1):
            if i > 0 and content[i-1] in '.!?':
                # Check if followed by space or capital letter
                if i < len(content) and (content[i].isspace() or content[i].isupper()):
                    sentence_starts.append(i)
        
        # Use closest sentence start if found
        if sentence_starts:
            start_pos = max(sentence_starts)
        else:
            # At least move to word boundary
            while start_pos > 0 and not content[start_pos-1].isspace():
                start_pos -= 1
        
        # Look for sentence end
        sentence_ends = []
        # Search forward for sentence endings
        for i in range(end_pos, min(len(content), end_pos + 200)):
            if content[i] in '.!?':
                # Check if followed by space or end of content
                if i + 1 >= len(content) or content[i+1].isspace():
                    sentence_ends.append(i + 1)
        
        # Use closest sentence end if found
        if sentence_ends:
            end_pos = min(sentence_ends)
        else:
            # At least move to word boundary
            while end_pos < len(content) and not content[end_pos].isspace():
                end_pos += 1
        
        return start_pos, end_pos
    
    def _extract_line_chunk(
        self,
        content: str,
        match_info: Dict[str, Any],
        lines_before: int,
        lines_after: int,
        use_boundaries: bool
    ) -> Optional[ExtractedChunk]:
        """
        Extract chunk using line numbers for multi-line documents.
        """
        lines = content.splitlines()
        line_number = match_info.get("line_number", 1) - 1  # Convert to 0-indexed
        
        # Ensure line number is valid
        if line_number < 0 or line_number >= len(lines):
            line_number = min(max(0, line_number), len(lines) - 1)
        
        # Basic boundaries
        start_line = max(0, line_number - lines_before)
        end_line = min(len(lines), line_number + lines_after + 1)
        
        # Apply intelligent boundary detection
        if use_boundaries:
            start_line, end_line = self._detect_boundaries(
                lines=lines,
                target_line=line_number,
                start_line=start_line,
                end_line=end_line
            )
        
        # Extract chunk
        chunk_lines = lines[start_line:end_line]
        chunk_text = '\n'.join(chunk_lines)
        
        # Create metadata
        metadata = ChunkMetadata(
            extraction_method="line-based",
            single_line_document=False,
            chunk_size_chars=len(chunk_text),
            chunk_size_lines=len(chunk_lines),
            boundaries_used=use_boundaries,
            sentence_boundaries=False
        )
        
        return ExtractedChunk(
            content=chunk_text,
            start_line=start_line + 1,  # Convert back to 1-indexed
            end_line=end_line,
            match_info=match_info,
            metadata=metadata
        )
    
    def _detect_boundaries(
        self,
        lines: List[str],
        target_line: int,
        start_line: int,
        end_line: int
    ) -> Tuple[int, int]:
        """
        Detect semantic boundaries for chunk extraction.
        """
        # Look backward for section start
        for i in range(target_line, max(start_line - 10, 0), -1):
            if self._is_section_header(lines[i]):
                start_line = i
                break
            elif i < target_line - 2 and not lines[i].strip():
                # Paragraph break
                start_line = i + 1
                break
        
        # Look forward for section end
        for i in range(target_line + 1, min(end_line + 10, len(lines))):
            if self._is_section_header(lines[i]):
                end_line = i
                break
            elif i > target_line + 2 and not lines[i].strip():
                # Paragraph break
                end_line = i
                break
        
        return start_line, end_line
    
    def _is_section_header(self, line: str) -> bool:
        """Check if line is a section header."""
        line = line.strip()
        if not line:
            return False
        
        # All caps header
        if line.isupper() and len(line) > 3:
            return True
        
        # Ends with colon
        if line.endswith(':') and len(line) < 50:
            return True
        
        # Common medical headers
        header_keywords = [
            'CHIEF COMPLAINT', 'HISTORY', 'ASSESSMENT', 'PLAN',
            'DIAGNOSIS', 'MEDICATIONS', 'PHYSICAL EXAM', 'LABORATORY'
        ]
        
        for keyword in header_keywords:
            if keyword in line.upper():
                return True
        
        return False
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """Return agent skills for the AgentCard."""
        return [
            AgentSkill(
                id="extract_chunks",
                name="Extract Text Chunks",
                description="Extract meaningful chunks around search matches with intelligent boundaries",
                tags=["chunk-extraction", "context", "boundaries", "deduplication"],
                examples=[
                    "Extract context around match",
                    "Get chunk with sentence boundaries",
                    "Extract from single-line document",
                    "Create chunks with section boundaries"
                ],
                input_modes=["application/json"],
                output_modes=["application/json"]
            )
        ]
    
    def supports_streaming(self) -> bool:
        """Enable streaming for real-time chunk extraction."""
        return True


# Module-level app creation for HealthUniverse deployment
agent = ChunkAgent()
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
    port = int(os.getenv("PORT", 8004))
    
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    print(f"📄 Handles single-line and multi-line documents")
    print(f"✂️ Intelligent boundary detection and deduplication")
    print("\n📝 Example input:")
    print('  {"match_info": {...}, "document_content": "...", "lines_before": 5}')
    
    uvicorn.run(app, host="0.0.0.0", port=port)