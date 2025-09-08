#!/usr/bin/env python3
"""
Simple Orchestrator Agent - Direct sequential pipeline execution.
A straightforward orchestrator that calls agents in a fixed sequence without complex tools.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base import A2AAgent
from google.adk.tools import FunctionTool
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class SimpleOrchestratorAgent(A2AAgent):
    """Simple orchestrator that directly calls agents in sequence."""
    
    def get_agent_name(self) -> str:
        """Return the agent's name."""
        return "Simple Pipeline Orchestrator"
    
    def get_agent_description(self) -> str:
        """Return agent description."""
        return (
            "Simple orchestrator with direct sequential pipeline execution. "
            "Calls agents in a fixed order: keyword → grep → chunk → summarize. "
            "Provides clear logging of inter-agent communication without complex tools."
        )
    
    def supports_streaming(self) -> bool:
        """Enable streaming for meta-orchestrator compatibility."""
        return True
    
    def get_system_instruction(self) -> str:
        """System instruction for the LLM when using tools."""
        return """You are a medical document analysis pipeline coordinator.

When you receive a medical document, use the run_simple_pipeline tool to process it.

The pipeline will:
1. Generate search patterns (keyword agent)
2. Search for matches (grep agent)
3. Extract context chunks (chunk agent)
4. Summarize findings (summarize agent)

Always use the run_simple_pipeline tool for document analysis."""
    
    def get_tools(self) -> list:
        """Return the pipeline execution tool."""
        # Create bound function that has access to self
        async def run_simple_pipeline(document: str) -> str:
            """
            Execute the simple medical document analysis pipeline.
            
            Processes documents through: keyword → grep → chunk → summarize.
            
            Args:
                document: The medical document text to analyze
                
            Returns:
                Medical document summary
            """
            return await self.execute_pipeline(document)
        
        return [FunctionTool(func=run_simple_pipeline)]
    
    async def execute_pipeline(self, message: str) -> str:
        """
        Process the message through the pipeline in sequence.
        
        Args:
            message: The input text to analyze
            
        Returns:
            Final summarized analysis
        """
        start_time = time.time()
        self.logger.info("="*80)
        self.logger.info("🚀 SIMPLE ORCHESTRATOR STARTING PIPELINE")
        self.logger.info("="*80)
        
        try:
            # Step 1: Call Keyword Agent
            self.logger.info("\n📍 STEP 1: Calling Keyword Agent")
            self.logger.info("-"*40)
            
            keyword_message = f"""Generate regex patterns for finding medical information in this document:

{message[:1000]}

Generate comprehensive patterns for all medical information."""
            
            self.logger.info(f"📤 Sending to keyword agent: {len(keyword_message)} characters")
            keyword_response = await self.call_agent("keyword", keyword_message)
            self.logger.info(f"📥 Received from keyword agent: {len(keyword_response)} characters")
            
            # Extract patterns from response
            patterns = self._extract_patterns(keyword_response)
            self.logger.info(f"   Extracted {len(patterns)} patterns")
            
            # Step 2: Call Grep Agent
            self.logger.info("\n📍 STEP 2: Calling Grep Agent")
            self.logger.info("-"*40)
            
            # Send as dict directly - no JSON string manipulation needed
            grep_request = {
                "patterns": patterns,
                "document_content": message,
                "case_sensitive": False
            }
            
            self.logger.info(f"📤 Sending to grep agent: {len(patterns)} patterns, {len(message)} char document")
            grep_response = await self.call_agent("grep", grep_request)
            self.logger.info(f"📥 Received from grep agent: {len(str(grep_response))} characters")
            
            # Parse grep results
            matches = self._parse_grep_results(grep_response)
            self.logger.info(f"   Found {len(matches)} matches")
            
            # Deduplicate matches by line number for single-line documents
            unique_lines = {}
            for match in matches:
                line_num = match.get("line_number", 1)
                if line_num not in unique_lines:
                    unique_lines[line_num] = match
            
            # For single-line documents, just take the first match or split into segments
            if len(unique_lines) == 1 and len(matches) > 1:
                self.logger.info(f"   ⚠️ Single-line document with {len(matches)} matches")
                # For single-line docs, we'll just process once with the full content
                matches_to_process = [matches[0]] if matches else []
            else:
                # For multi-line docs, take unique lines up to limit
                matches_to_process = list(unique_lines.values())[:5]
            
            self.logger.info(f"   Deduped to {len(matches_to_process)} unique chunks to extract")
            
            # Step 3: Call Chunk Agent for unique matches only
            self.logger.info(f"\n📍 STEP 3: Calling Chunk Agent ({len(matches_to_process)} times)")
            self.logger.info("-"*40)
            
            chunks = []
            for i, match in enumerate(matches_to_process, 1):
                # Include document content for chunk extraction
                chunk_request = {
                    "match_info": match,
                    "document_content": message,  # Pass the full document
                    "lines_before": 2,
                    "lines_after": 2
                }
                
                self.logger.info(f"   [{i}/{len(matches_to_process)}] Extracting chunk for line {match.get('line_number', '?')}...")
                chunk_response = await self.call_agent("chunk", chunk_request)
                chunks.append(chunk_response)
            
            self.logger.info(f"   Extracted {len(chunks)} chunks")
            
            # Step 4: Call Summarize Agent
            self.logger.info("\n📍 STEP 4: Calling Summarize Agent")
            self.logger.info("-"*40)
            
            # Extract text content from structured chunk responses
            chunk_texts = []
            for chunk_response in chunks[:5]:  # Limit for summarization
                # First extract data from artifact structure
                data = self._extract_from_artifact(chunk_response)
                
                if isinstance(data, dict):
                    # Handle new structured ChunkResult format
                    if "chunks" in data:
                        for extracted_chunk in data.get("chunks", []):
                            if isinstance(extracted_chunk, dict) and "content" in extracted_chunk:
                                chunk_texts.append(extracted_chunk["content"])
                    # Handle old format
                    elif "chunk" in data:
                        chunk_data = data.get("chunk", {})
                        if "content" in chunk_data:
                            chunk_texts.append(chunk_data["content"])
                    # Direct content
                    elif "content" in data:
                        chunk_texts.append(data["content"])
                    else:
                        # Fallback to string representation
                        chunk_texts.append(str(data))
                else:
                    chunk_texts.append(str(data))
            
            # Combine chunks for summarization
            combined_chunks = "\n\n".join(chunk_texts)
            
            summarize_request = {
                "chunk_content": combined_chunks,
                "chunk_metadata": {
                    "source": "Eleanor Richardson medical record",
                    "total_matches": len(matches),
                    "chunks_analyzed": len(chunks)
                },
                "summary_style": "clinical"
            }
            
            self.logger.info(f"📤 Sending to summarize agent: {len(combined_chunks)} characters")
            summary_response = await self.call_agent("summarize", summarize_request)
            self.logger.info(f"📥 Received from summarize agent: {len(str(summary_response))} characters")
            
            # Extract text from summary artifact (it returns TextPart)
            summary_text = self._extract_from_artifact(summary_response)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Final response
            self.logger.info("\n" + "="*80)
            self.logger.info(f"✅ PIPELINE COMPLETE IN {execution_time:.2f} SECONDS")
            self.logger.info("="*80)
            
            return f"""## Medical Document Analysis Complete

**Execution Time:** {execution_time:.2f} seconds

**Pipeline Statistics:**
- Patterns generated: {len(patterns)}
- Matches found: {len(matches)}
- Chunks extracted: {len(chunks)}
- Chunks analyzed: {min(len(chunks), 5)}

**Summary:**
{summary_text}

---
*Analysis performed by Simple Pipeline Orchestrator*"""
            
        except Exception as e:
            self.logger.error(f"❌ Pipeline error: {e}")
            return f"Pipeline execution failed: {str(e)}"
    
    def _extract_from_artifact(self, response: Any) -> Any:
        """
        Extract data or text from artifact response structure.
        
        Artifacts have the structure:
        {
            "artifactId": "...",
            "parts": [
                {"kind": "data", "data": {...}} or
                {"kind": "text", "text": "..."}
            ]
        }
        """
        if isinstance(response, dict):
            # Check if this is an artifact with parts
            if "parts" in response and isinstance(response["parts"], list):
                for part in response["parts"]:
                    if isinstance(part, dict):
                        if part.get("kind") == "data":
                            return part.get("data")
                        elif part.get("kind") == "text":
                            return part.get("text")
            
            # Check if response has artifactId and parts (full artifact)
            if "artifactId" in response and "parts" in response:
                return self._extract_from_artifact({"parts": response["parts"]})
        
        # Fallback - return as is
        return response
    
    def _extract_patterns(self, keyword_response: Any) -> List[str]:
        """Extract patterns from keyword agent response."""
        patterns = []
        
        # First extract data from artifact structure
        data = self._extract_from_artifact(keyword_response)
        
        # Handle structured response from new keyword agent
        if isinstance(data, dict):
            # Check for the new Pydantic structure
            if "medical_patterns" in data:
                # Combine all pattern types from the new structure
                patterns.extend(data.get("medical_patterns", []))
                patterns.extend(data.get("date_patterns", []))
                patterns.extend(data.get("section_patterns", []))
                patterns.extend(data.get("clinical_summary_patterns", []))
            elif "pattern_groups" in data:
                # Extract from pattern groups
                for group in data.get("pattern_groups", []):
                    patterns.extend(group.get("patterns", []))
            elif "patterns" in data:
                # Old structure fallback
                patterns = data["patterns"]
        
        # If no patterns found, return empty list (no fake patterns)
        # The keyword agent should always provide patterns via LLM
        if not patterns:
            self.logger.warning("No patterns received from keyword agent")
            patterns = []
        
        return patterns[:30]  # Limit number of patterns
    
    async def process_message(self, message: str) -> str:
        """
        Process message through the pipeline.
        
        Since base class doesn't invoke tools automatically,
        we directly execute the pipeline here.
        """
        # Directly execute the pipeline
        return await self.execute_pipeline(message)
    
    def _parse_grep_results(self, grep_response: Any) -> List[dict]:
        """Parse grep agent results into match info."""
        matches = []
        
        # First extract data from artifact structure
        data = self._extract_from_artifact(grep_response)
        
        # Handle new structured GrepResult format
        if isinstance(data, dict):
            # Check for new Pydantic structure
            if "pattern_results" in data:
                # Extract all matches from all patterns
                for pattern_result in data.get("pattern_results", []):
                    for match in pattern_result.get("matches", []):
                        # Convert MatchLocation to simple dict for chunk agent
                        matches.append({
                            "line_number": match.get("line_number", 1),
                            "line_text": match.get("line_text", ""),
                            "match_text": match.get("match_text", ""),
                            "context": match.get("context", []),
                            "pattern": match.get("pattern", ""),
                            "match_position": match.get("match_position"),
                            "single_line_doc": match.get("single_line_doc", False)
                        })
            # Old format compatibility
            elif "search_results" in data:
                # Handle old grep_tools format
                for result in data.get("search_results", []):
                    matches.extend(result.get("matches", []))
            elif "matches" in data:
                matches = data["matches"]
        
        # If no matches found, return empty list
        if not matches:
            self.logger.warning("No matches found from grep agent")
        
        return matches
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """Return agent skills."""
        return [
            AgentSkill(
                id="simple_pipeline",
                name="Simple Pipeline Execution",
                description="Execute fixed sequence: keyword → grep → chunk → summarize",
                tags=["pipeline", "sequential", "simple", "direct"],
                input_modes=["text/plain"],
                output_modes=["text/plain", "text/markdown"]
            )
        ]


# Create the agent instance
agent = SimpleOrchestratorAgent()

# Create agent card and task store
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
    port = int(os.getenv("PORT", 8008))
    
    print(f"\n{'='*80}")
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"{'='*80}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    print(f"\n✨ Features:")
    print(f"  • Direct sequential execution")
    print(f"  • No complex tools or LLM decisions")
    print(f"  • Clear step-by-step logging")
    print(f"  • Execution time tracking")
    print(f"{'='*80}\n")
    
    uvicorn.run(app, host="0.0.0.0", port=port)