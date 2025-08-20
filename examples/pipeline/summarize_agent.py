#!/usr/bin/env python3
"""
Medical Summarizer Agent - Analyzes and summarizes medical text.
Migrated from ADK demo pipeline to use enhanced A2AAgent base.

This agent provides medical text analysis with:
- Intelligent summarization at various detail levels
- Medical entity extraction (diagnoses, medications, procedures)
- Relevance scoring based on clinical importance
- Clinical summary generation
- Medical terminology analysis
"""

import os
import sys
import json
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base import A2AAgent
from tools.summarize_tools import SUMMARIZE_TOOLS
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill


class SummarizeAgent(A2AAgent):
    """LLM-powered medical text summarization agent."""
    
    def get_agent_name(self) -> str:
        """Return the agent's name."""
        return "Medical Summarizer"
    
    def get_agent_description(self) -> str:
        """Return detailed agent description."""
        return (
            "LLM-powered agent that analyzes medical text chunks and creates accurate, "
            "clinically relevant summaries. Extracts medical entities, scores relevance, "
            "and generates various summary formats for clinical decision-making."
        )
    
    def get_agent_version(self) -> str:
        """Return agent version."""
        return "2.0.0"
    
    def get_system_instruction(self) -> str:
        """Return the system instruction for medical summarization."""
        return """You are a medical document summarization specialist. Your role is to analyze medical text chunks and create accurate, clinically relevant summaries.

Core responsibilities:
1. Summarize medical text with appropriate detail level
2. Extract key medical entities (diagnoses, treatments, medications)
3. Score relevance based on medical importance
4. Generate clinical summaries from multiple sources
5. Analyze medical terminology

When summarizing medical text:
- Prioritize clinically actionable information
- Maintain medical accuracy and precision
- Preserve critical details (dosages, dates, values)
- Use appropriate medical terminology
- Highlight abnormal findings or critical results

For entity extraction:
- Diagnoses: Include ICD codes, staging, severity
- Medications: Drug name, dose, route, frequency
- Procedures: Type, date, findings, complications
- Lab results: Value, reference range, significance
- Symptoms: Onset, duration, severity, associated factors

Relevance scoring (0-10):
- Consider medical importance over text length
- Weight primary diagnoses and active treatments highly
- Factor in temporal relevance (current vs past)
- Account for pattern match quality
- Prioritize abnormal or critical findings

Summary styles:
- Concise: 2-3 sentences with key findings
- Detailed: Comprehensive paragraph with context
- Clinical: Structured format focusing on diagnoses/treatments
- Bullet: Key points in digestible format

Quality guidelines:
- Never invent or assume medical information
- Flag inconsistencies or contradictions
- Note when information is incomplete
- Maintain patient safety focus
- Use standard medical abbreviations appropriately

For batch processing:
- Identify relationships between chunks
- Combine related information logically
- Avoid redundancy while maintaining completeness
- Create coherent narrative from fragments

Always aim to produce summaries that would be useful for clinical decision-making."""
    
    def get_tools(self) -> List:
        """Return the summarization tools."""
        return SUMMARIZE_TOOLS
    
    async def process_message(self, message: str) -> str:
        """
        Process incoming messages directly when not using LLM tools.
        Handles JSON messages from orchestrators.
        """
        try:
            # Try to parse as JSON
            data = json.loads(message)
            
            # Check if this is a summarization request
            if "chunk_content" in data or "chunks" in data:
                # Direct summarization request from orchestrator
                from tools.summarize_tools import summarize_medical_chunk
                
                # Get content to summarize
                if "chunks" in data:
                    # Multiple chunks
                    chunks = data.get("chunks", [])
                    if isinstance(chunks, list):
                        # Join chunks into single content
                        chunk_content = "\n\n".join(str(c) for c in chunks[:5])
                    else:
                        chunk_content = str(chunks)
                else:
                    chunk_content = data.get("chunk_content", "")
                
                metadata = data.get("chunk_metadata", {})
                summary_type = data.get("summary_style", "clinical")
                
                result = summarize_medical_chunk(
                    chunk_content=chunk_content,
                    chunk_metadata_json=json.dumps(metadata),
                    summary_type=summary_type,
                    max_length="500"
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
                id="summarize_medical_chunk",
                name="Summarize Medical Chunk",
                description="Create concise, accurate summary of medical text.",
                tags=["summarization", "medical", "text-analysis", "clinical"],
                examples=[
                    "Summarize this diagnosis section",
                    "Create a concise summary of medications",
                    "Generate clinical summary of findings",
                    "Summarize in bullet format"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            ),
            AgentSkill(
                id="extract_medical_entities",
                name="Extract Medical Entities",
                description="Extract diagnoses, medications, procedures, and other medical entities.",
                tags=["entity-extraction", "NER", "medical-terminology"],
                examples=[
                    "Extract all medications with dosages",
                    "Find diagnosis codes",
                    "Identify procedures mentioned",
                    "Extract lab values and ranges"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            ),
            AgentSkill(
                id="score_medical_relevance",
                name="Score Medical Relevance",
                description="Score text relevance based on clinical importance (0-10).",
                tags=["relevance-scoring", "ranking", "clinical-importance"],
                examples=[
                    "Score relevance of this finding",
                    "Rank importance of multiple chunks",
                    "Evaluate clinical significance",
                    "Prioritize by medical importance"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            ),
            AgentSkill(
                id="batch_summarize_chunks",
                name="Batch Summarize Chunks",
                description="Summarize multiple text chunks into coherent narrative.",
                tags=["batch-processing", "multi-chunk", "synthesis"],
                examples=[
                    "Combine multiple section summaries",
                    "Synthesize findings from different sources",
                    "Create unified patient summary",
                    "Merge related information"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            ),
            AgentSkill(
                id="generate_clinical_summary",
                name="Generate Clinical Summary",
                description="Create structured clinical summary with key findings.",
                tags=["clinical-summary", "structured-output", "decision-support"],
                examples=[
                    "Generate discharge summary format",
                    "Create SOAP note summary",
                    "Produce clinical brief",
                    "Format for physician handoff"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            ),
            AgentSkill(
                id="analyze_medical_terminology",
                name="Analyze Medical Terminology",
                description="Analyze and explain medical terms and abbreviations.",
                tags=["terminology", "abbreviations", "medical-language"],
                examples=[
                    "Explain medical abbreviations",
                    "Define medical terms",
                    "Expand acronyms",
                    "Clarify medical jargon"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json", "text/plain"]
            )
        ]
    
    def supports_streaming(self) -> bool:
        """Enable streaming for real-time summarization."""
        return True


# Module-level app creation for HealthUniverse deployment
agent = SummarizeAgent()
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
    port = int(os.getenv("PORT", 8005))
    
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    print(f"🛠️ Tools available: {len(agent.get_tools())}")
    print("\n📝 Example queries:")
    print('  - "Summarize this medical text in concise format"')
    print('  - "Extract all medications and diagnoses from this chunk"')
    print('  - "Score the clinical relevance of this finding"')
    print('  - "Generate a clinical summary from these chunks"')
    print('  - "Analyze the medical terminology in this text"')
    
    uvicorn.run(app, host="0.0.0.0", port=port)