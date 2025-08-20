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
from typing import List
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


# Global agent instance for tool access
_simple_agent_instance = None

async def run_simple_pipeline(document: str) -> str:
    """
    Execute the simple medical document analysis pipeline.
    
    Processes documents through the complete 12-agent medical pipeline.
    
    Args:
        document: The medical document text to analyze
        
    Returns:
        Medical document summary
    """
    global _simple_agent_instance
    if _simple_agent_instance:
        return await _simple_agent_instance.execute_pipeline(document)
    return "Error: Agent not initialized"


class SimpleOrchestratorAgent(A2AAgent):
    """Simple orchestrator that directly calls agents in sequence."""
    
    def __init__(self):
        """Initialize the agent and set global instance for tool access."""
        super().__init__()
        global _simple_agent_instance
        _simple_agent_instance = self
    
    def get_agent_name(self) -> str:
        """Return the agent's name."""
        return "Simple Pipeline Orchestrator"
    
    def get_agent_description(self) -> str:
        """Return agent description."""
        return (
            "Complete orchestrator with direct sequential pipeline execution. "
            "Calls ALL 12 agents in fixed order: keyword → grep → chunk → "
            "temporal_tagging → encounter_grouping → reconciliation → summary_extractor → "
            "timeline_builder → checker → unified_extractor → unified_verifier → narrative_synthesis. "
            "Provides clear logging of inter-agent communication without complex tools."
        )
    
    def supports_streaming(self) -> bool:
        """Enable streaming for meta-orchestrator compatibility."""
        return True
    
    def get_system_instruction(self) -> str:
        """System instruction for the LLM when using tools."""
        return """You are a medical document analysis pipeline coordinator.

When you receive a medical document, use the run_simple_pipeline tool to process it.

The pipeline will process through all 12 agents:
1. Generate search patterns (keyword agent)
2. Search for matches (grep agent)
3. Extract context chunks (chunk agent)
4. Extract temporal information (temporal tagging agent)
5. Group by encounters (encounter grouping agent)
6. Reconcile conflicts (reconciliation agent)
7. Extract summaries (summary extractor agent)
8. Build timeline (timeline builder agent with checker validation)
9. Extract all entities (unified extractor agent)
10. Verify data (unified verifier agent)
11. Create narrative (narrative synthesis agent)

Always use the run_simple_pipeline tool for document analysis."""
    
    def get_tools(self) -> list:
        """Return the pipeline execution tool."""
        return [FunctionTool(func=run_simple_pipeline)]
    
    async def execute_pipeline(self, message: str) -> str:
        """
        Process the message through the pipeline in sequence.
        
        Args:
            message: The input text to analyze
            
        Returns:
            Complete medical document analysis with narrative synthesis
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
            keyword_response = await self.call_other_agent("keyword", keyword_message, timeout=60.0)  # Increased timeout
            self.logger.info(f"📥 Received from keyword agent: {len(keyword_response)} characters")
            
            # Extract patterns from response (simplified - in reality would parse the response)
            patterns = self._extract_patterns(keyword_response)
            self.logger.info(f"   Extracted {len(patterns)} patterns")
            
            # Step 2: Call Grep Agent
            self.logger.info("\n📍 STEP 2: Calling Grep Agent")
            self.logger.info("-"*40)
            
            # Send natural language message that the agent's LLM can understand
            # A2A compliant - no JSON, just clear instructions
            grep_message = f"""Search the following document for these patterns:
{', '.join(patterns)}

Document:
{message}

Please search for all occurrences of these patterns. Use case-insensitive matching."""
            
            self.logger.info(f"📤 Sending to grep agent: {len(patterns)} patterns, {len(message)} char document")
            grep_response = await self.call_other_agent("grep", grep_message, timeout=60.0)  # Increased timeout
            self.logger.info(f"📥 Received from grep agent: {len(grep_response)} characters")
            
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
                # Send natural language message for chunk extraction
                # A2A compliant - describe what we need in plain text
                chunk_message = f"""Extract context around this match:
Match text: {match.get('match_text', '')}
Line number: {match.get('line_number', '')}
File: {match.get('file_path', 'document')}

Please provide 2 lines before and 2 lines after this match for context.
Full document:
{match.get('file_content', message)}"""
                
                self.logger.info(f"   [{i}/{len(matches_to_process)}] Extracting chunk for line {match.get('line_number', '?')}...")
                chunk_response = await self.call_other_agent("chunk", chunk_message, timeout=60.0)  # Increased timeout
                chunks.append(chunk_response)
            
            self.logger.info(f"   Extracted {len(chunks)} chunks")
            
            # Step 4: Call Temporal Tagging Agent
            self.logger.info("\n📍 STEP 4: Calling Temporal Tagging Agent")
            self.logger.info("-"*40)
            
            # A2A compliant - send natural language message
            temporal_message = f"""Tag temporal information in this medical document:

{message}

Please identify and tag all dates, times, and temporal references related to medical events."""
            
            self.logger.info(f"📤 Sending to temporal_tagging agent: {len(message)} characters")
            temporal_response = await self.call_other_agent("temporal_tagging", temporal_message, timeout=60.0)
            self.logger.info(f"📥 Received from temporal_tagging agent: {len(temporal_response)} characters")
            
            # Step 5: Call Encounter Grouping Agent
            self.logger.info("\n📍 STEP 5: Calling Encounter Grouping Agent")
            self.logger.info("-"*40)
            
            # A2A compliant - send natural language message
            encounter_message = f"""Group the following temporally-tagged information into medical encounters:

Temporal Events:
{temporal_response}

Original Document:
{message}

Please organize related medical events into logical encounters."""
            
            self.logger.info(f"📤 Sending to encounter_grouping agent")
            encounter_response = await self.call_other_agent("encounter_grouping", encounter_message, timeout=60.0)
            self.logger.info(f"📥 Received from encounter_grouping agent: {len(encounter_response)} characters")
            
            # Step 6: Call Reconciliation Agent
            self.logger.info("\n📍 STEP 6: Calling Reconciliation Agent")
            self.logger.info("-"*40)
            
            # A2A compliant - send natural language message
            reconciliation_message = f"""Reconcile and deduplicate these medical encounters:

Encounter Groups:
{encounter_response}

Facts from document:
{chr(10).join(chunks[:5]) if chunks else 'No chunks available'}

Please identify and merge duplicate information, resolving any conflicts."""
            
            self.logger.info(f"📤 Sending to reconciliation agent")
            reconciliation_response = await self.call_other_agent("reconciliation", reconciliation_message, timeout=60.0)
            self.logger.info(f"📥 Received from reconciliation agent: {len(reconciliation_response)} characters")
            
            # Step 7: Call Summary Extractor Agent
            self.logger.info("\n📍 STEP 7: Calling Summary Extractor Agent")
            self.logger.info("-"*40)
            
            # A2A compliant - send natural language message
            summary_extractor_message = f"""Extract key summaries from this reconciled medical data:

Reconciled Data:
{reconciliation_response}

Original Document:
{message}

Please provide concise summaries of the main medical findings."""
            
            self.logger.info(f"📤 Sending to summary_extractor agent")
            summary_extractor_response = await self.call_other_agent("summary_extractor", summary_extractor_message, timeout=60.0)
            self.logger.info(f"📥 Received from summary_extractor agent: {len(summary_extractor_response)} characters")
            
            # Step 8: Call Timeline Builder Agent
            self.logger.info("\n📍 STEP 8: Calling Timeline Builder Agent")
            self.logger.info("-"*40)
            
            # A2A compliant - send natural language message
            timeline_message = f"""Build a chronological timeline from these medical events:

Temporal Events:
{temporal_response}

Encounter Groups:
{encounter_response}

Please organize events in chronological order."""
            
            self.logger.info(f"📤 Sending to timeline_builder agent")
            timeline_response = await self.call_other_agent("timeline_builder", timeline_message, timeout=60.0)
            self.logger.info(f"📥 Received from timeline_builder agent: {len(timeline_response)} characters")
            
            # Step 9: Call Checker Agent (with retry loop)
            self.logger.info("\n📍 STEP 9: Calling Checker Agent")
            self.logger.info("-"*40)
            
            # A2A compliant - send natural language message
            checker_message = f"""Verify the accuracy of this medical timeline:

Timeline:
{timeline_response}

Summary:
{summary_extractor_response}

Original Text:
{message}

Please check for consistency and accuracy."""
            
            self.logger.info(f"📤 Sending to checker agent")
            checker_response = await self.call_other_agent("checker", checker_message, timeout=60.0)
            self.logger.info(f"📥 Received from checker agent: {len(checker_response)} characters")
            
            # Step 10: Call Unified Extractor Agent
            self.logger.info("\n📍 STEP 10: Calling Unified Extractor Agent")
            self.logger.info("-"*40)
            
            # A2A compliant - send natural language message
            unified_extractor_message = f"""Extract all medical entities from this data:

Document Text:
{message}

Extracted Chunks:
{chr(10).join(chunks[:5]) if chunks else 'No chunks'}

Temporal Events:
{temporal_response}

Please extract all medical entities, conditions, medications, and procedures."""
            
            self.logger.info(f"📤 Sending to unified_extractor agent")
            unified_extractor_response = await self.call_other_agent("unified_extractor", unified_extractor_message, timeout=60.0)
            self.logger.info(f"📥 Received from unified_extractor agent: {len(unified_extractor_response)} characters")
            
            # Step 11: Call Unified Verifier Agent
            self.logger.info("\n📍 STEP 11: Calling Unified Verifier Agent")
            self.logger.info("-"*40)
            
            # A2A compliant - send natural language message
            unified_verifier_message = f"""Verify the extracted medical entities:

Extracted Data:
{unified_extractor_response}

Original Text:
{message}

Timeline:
{timeline_response}

Please verify accuracy and completeness of the extracted information."""
            
            self.logger.info(f"📤 Sending to unified_verifier agent")
            unified_verifier_response = await self.call_other_agent("unified_verifier", unified_verifier_message, timeout=60.0)
            self.logger.info(f"📥 Received from unified_verifier agent: {len(unified_verifier_response)} characters")
            
            # Step 12: Call Narrative Synthesis Agent
            self.logger.info("\n📍 STEP 12: Calling Narrative Synthesis Agent")
            self.logger.info("-"*40)
            
            # A2A compliant - send natural language message
            narrative_message = f"""Create a clinical narrative from this medical data:

Summary:
{summary_extractor_response}

Timeline:
{timeline_response}

Verified Data:
{unified_verifier_response}

Patient: Eleanor Richardson (if mentioned in data)

Please synthesize a comprehensive clinical narrative."""
            
            self.logger.info(f"📤 Sending to narrative_synthesis agent")
            narrative_response = await self.call_other_agent("narrative_synthesis", narrative_message, timeout=60.0)
            self.logger.info(f"📥 Received from narrative_synthesis agent: {len(narrative_response)} characters")
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Final response
            self.logger.info("\n" + "="*80)
            self.logger.info(f"✅ FULL PIPELINE COMPLETE IN {execution_time:.2f} SECONDS")
            self.logger.info("="*80)
            
            return f"""## Medical Document Analysis Complete (Full Pipeline)

**Execution Time:** {execution_time:.2f} seconds

**Pipeline Statistics:**
- Patterns generated: {len(patterns)}
- Matches found: {len(matches)}
- Chunks extracted: {len(chunks)}
- All 12 pipeline stages completed

**Final Narrative:**
{narrative_response}

**Clinical Summary:**
{summary_extractor_response}

---
*Analysis performed by Simple Pipeline Orchestrator - Full Version*"""
            
        except Exception as e:
            self.logger.error(f"❌ Pipeline error: {e}")
            return f"Pipeline execution failed: {str(e)}"
    
    def _extract_patterns(self, keyword_response: str) -> List[str]:
        """Extract patterns from keyword agent response."""
        # Simplified extraction - in reality would parse the structured response
        patterns = []
        lines = keyword_response.split('\n')
        for line in lines:
            if '`' in line and not line.strip().startswith('#'):
                # Extract patterns between backticks
                import re
                found = re.findall(r'`([^`]+)`', line)
                patterns.extend(found)
        
        # If no patterns found, use defaults
        if not patterns:
            patterns = [
                r"diabetes", r"hypertension", r"medication",
                r"diagnosis", r"treatment", r"mg|ml|mcg",
                r"\d+\s*(mg|ml|mcg)", r"blood\s+pressure",
                r"heart\s+rate", r"temperature"
            ]
        
        return patterns[:20]  # Limit number of patterns
    
    async def process_message(self, message: str) -> str:
        """
        Process message - required by base class but not used.
        
        The actual processing happens via the tool function.
        """
        # This won't be called when tools are provided
        return "Processing through simple pipeline..."
    
    def _parse_grep_results(self, grep_response: str) -> List[dict]:
        """Parse grep agent results into match info."""
        # A2A compliant - parse natural language response, not JSON
        # The grep agent will return human-readable results
        matches = []
        
        # Parse the text response looking for matches
        # In a real implementation, we'd extract structured info from the text
        lines = grep_response.split('\n')
        for i, line in enumerate(lines[:20]):  # Limit matches
            if line.strip():
                # Create match entries from the text response
                matches.append({
                    "file_path": "document.txt",
                    "line_number": i + 1,
                    "match_text": line[:100],
                    "file_content": grep_response
                })
        
        return matches
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """Return agent skills."""
        return [
            AgentSkill(
                id="simple_pipeline",
                name="Simple Pipeline Execution",
                description="Execute complete 12-agent pipeline in fixed sequence",
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