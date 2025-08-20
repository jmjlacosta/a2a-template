#!/usr/bin/env python3
"""
Context Extractor Agent - Extracts meaningful text chunks from documents.
Migrated from ADK demo pipeline to use enhanced A2AAgent base.

This agent provides intelligent chunk extraction with:
- Natural boundary detection (sections, paragraphs, lists)
- Semantic unit preservation
- Context-aware extraction around search matches
- Chunk optimization and merging
"""

import os
import sys
import json
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base import A2AAgent

from tools.chunk_tools import CHUNK_TOOLS
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill


class ChunkAgent(A2AAgent):
    """LLM-powered chunk extraction agent with intelligent boundary detection."""
    
    def get_agent_name(self) -> str:
        """Return the agent's name."""
        return "Context Extractor"
    
    def get_agent_description(self) -> str:
        """Return detailed agent description."""
        return (
            "LLM-powered agent that extracts meaningful text chunks from medical documents "
            "using intelligent boundary detection. Preserves semantic units and provides "
            "context-aware extraction around search matches."
        )
    
    def get_agent_version(self) -> str:
        """Return agent version."""
        return "2.0.0"
    
    def get_system_instruction(self) -> str:
        """Return the system instruction for chunk extraction."""
        return """You are a medical document context extraction specialist. Your role is to create meaningful chunks of text around search matches using intelligent boundary detection.

IMPORTANT: File Content Handling
When you receive match_info that includes 'file_content':
- Always pass the 'file_content' parameter to chunk extraction functions
- The functions will use the provided content instead of reading from the file system
- This allows processing content from S3 or other external sources

Example: If match_info contains {"file_path": "doc.txt", "file_content": "...content...", ...},
call create_document_chunk(file_path="doc.txt", match_info={...}, file_content="...content...")

When extracting chunks, you should:
1. Identify natural document boundaries (sections, paragraphs, lists)
2. Preserve complete semantic units of information
3. Include sufficient context for understanding
4. Merge overlapping chunks when appropriate
5. Optimize chunk size while maintaining coherence

Key principles:
- Respect document structure and formatting
- Never break in the middle of sentences or important concepts
- Expand to include complete medical findings or assessments
- Consider the relationship between adjacent sections
- Preserve headers and their associated content together

Boundary detection guidelines:
- Section headers indicate major boundaries
- Empty lines often mark paragraph boundaries
- List items should be kept together when related
- Clinical findings should include their full context
- Temporal information should stay with related events

For medical documents specifically:
- Keep diagnosis statements with supporting evidence
- Include full medication entries (name, dose, frequency)
- Preserve complete laboratory or imaging results
- Maintain procedure descriptions with outcomes
- Keep assessment and plan sections intact

Chunk optimization:
- Target readable chunk sizes (10-50 lines typical)
- Prioritize completeness over strict size limits
- Remove redundant information when merging chunks
- Preserve the most clinically relevant content

Always aim to create chunks that can stand alone as meaningful units of medical information."""
    
    def get_tools(self) -> List:
        """Return the chunk extraction tools."""
        return CHUNK_TOOLS
    
    async def process_message(self, message: str) -> str:
        """
        Process incoming messages directly when not using LLM tools.
        Handles JSON messages from orchestrators.
        """
        try:
            # Try to parse as JSON
            data = json.loads(message)
            
            # Check if this is a chunk extraction request
            if "match_info" in data or ("matches" in data and "document" in data):
                # Direct chunk request from orchestrator
                from tools.chunk_tools import create_document_chunk
                
                # Handle different message formats
                if "matches" in data:
                    # From simple orchestrator - process multiple matches
                    matches = data.get("matches", [])
                    document = data.get("document", "")
                    chunks = []
                    
                    for match in matches[:5]:  # Limit to 5 chunks
                        # Create match_info for each match
                        match_info = {
                            "file_path": match.get("file_path", "document.txt"),
                            "line_number": match.get("line_number", 1),
                            "match_text": match.get("match_text", ""),
                            "file_content": document
                        }
                        
                        result = create_document_chunk(
                            file_path=match_info["file_path"],
                            match_info_json=json.dumps(match_info),
                            lines_before="10",
                            lines_after="10",
                            boundary_detection="true",
                            file_content=document
                        )
                        
                        chunks.append(result)
                    
                    return json.dumps({"chunks": chunks})
                    
                else:
                    # Single match_info
                    match_info = data.get("match_info", {})
                    lines_before = str(data.get("lines_before", 10))
                    lines_after = str(data.get("lines_after", 10))
                    
                    result = create_document_chunk(
                        file_path=match_info.get("file_path", "document.txt"),
                        match_info_json=json.dumps(match_info),
                        lines_before=lines_before,
                        lines_after=lines_after,
                        boundary_detection="true",
                        file_content=match_info.get("file_content", "")
                    )
                    
                    return result
            else:
                # Fall back to LLM processing - just return the message
                return message
                
        except json.JSONDecodeError:
            # Not JSON, use LLM processing - just return the message
            return message
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return json.dumps({"error": str(e)})
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """Return agent skills for the AgentCard."""
        return [
            AgentSkill(
                id="create_document_chunk",
                name="Create Document Chunk",
                description="Extract a meaningful chunk of text around a search match.",
                tags=["chunk-extraction", "context", "text-processing", "medical"],
                examples=[
                    "Extract context around a diagnosis mention",
                    "Get surrounding text for a medication reference",
                    "Create chunk with proper boundaries",
                    "Include related clinical information"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            ),
            AgentSkill(
                id="extract_multiple_chunks",
                name="Extract Multiple Chunks",
                description="Extract multiple chunks from different parts of a document.",
                tags=["batch-extraction", "multiple-chunks", "document-processing"],
                examples=[
                    "Extract chunks for all search matches",
                    "Get multiple sections from document",
                    "Process batch of match locations",
                    "Extract distributed information"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            ),
            AgentSkill(
                id="find_chunk_boundaries",
                name="Find Chunk Boundaries",
                description="Identify natural boundaries for chunk extraction.",
                tags=["boundary-detection", "structure-analysis", "segmentation"],
                examples=[
                    "Find section boundaries",
                    "Identify paragraph breaks",
                    "Detect list boundaries",
                    "Locate semantic units"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            ),
            AgentSkill(
                id="optimize_chunk_size",
                name="Optimize Chunk Size",
                description="Optimize chunk size while preserving semantic completeness.",
                tags=["optimization", "size-management", "coherence"],
                examples=[
                    "Adjust chunk to optimal size",
                    "Balance size and completeness",
                    "Merge small adjacent chunks",
                    "Split oversized chunks appropriately"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
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
    print(f"🛠️ Tools available: {len(agent.get_tools())}")
    print("\n📝 Example queries:")
    print('  - "Extract context around line 10 with 5 lines before and after"')
    print('  - "Create chunks for these search matches: [...]"')
    print('  - "Find natural boundaries in this document"')
    print('  - "Optimize this chunk to preserve semantic completeness"')
    
    uvicorn.run(app, host="0.0.0.0", port=port)