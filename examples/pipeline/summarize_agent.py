#!/usr/bin/env python3
"""
Medical Summarizer Agent - Analyzes and summarizes medical text using LLM.
Returns plain text summaries that are wrapped in TextPart Artifacts.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base import A2AAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill
from utils.llm_utils import generate_text


class SummarizeAgent(A2AAgent):
    """LLM-powered medical text summarization agent."""
    
    def get_agent_name(self) -> str:
        """Return the agent's name."""
        return "Medical Summarizer"
    
    def get_agent_description(self) -> str:
        """Return detailed agent description."""
        return (
            "LLM-powered agent that analyzes medical text chunks and creates "
            "clinically relevant summaries. Always uses LLM to generate summaries "
            "and returns them as plain text (wrapped in TextPart Artifacts)."
        )
    
    def get_agent_version(self) -> str:
        """Return agent version."""
        return "3.0.0"
    
    def get_system_instruction(self) -> str:
        """Return the system instruction for medical summarization."""
        return """You are a medical document summarization specialist. Analyze medical text and create accurate, clinically relevant summaries.

Focus on:
- Primary diagnoses and conditions
- Current medications and treatments
- Key lab results and findings
- Important dates and timeline
- Clinical recommendations

Guidelines:
- Be concise but comprehensive
- Use appropriate medical terminology
- Highlight critical findings
- Maintain chronological order when relevant
- Never invent information not in the source text

Format: Provide a clear, readable summary in paragraph or bullet format as appropriate."""
    
    async def process_message(self, message: str) -> str:
        """
        Process summarization request using LLM.
        
        Args:
            message: JSON string with chunk_content and optional metadata
            
        Returns:
            Plain text summary (will be wrapped in TextPart Artifact by base class)
        """
        # Parse input
        try:
            if isinstance(message, str) and message.startswith('{'):
                data = json.loads(message)
            elif isinstance(message, dict):
                data = message
            else:
                # Plain text message - summarize directly
                data = {"chunk_content": message}
            
            chunk_content = data.get("chunk_content", "")
            chunk_metadata = data.get("chunk_metadata", {})
            summary_style = data.get("summary_style", "clinical")
            
        except Exception as e:
            self.logger.error(f"Failed to parse request: {e}")
            # Return error as text (will still be wrapped in Artifact)
            return f"Error parsing summarization request: {str(e)}"
        
        # Check if there's content to summarize
        if not chunk_content or not chunk_content.strip():
            return "No content provided to summarize."
        
        # Build prompt based on style
        if summary_style == "clinical":
            style_instruction = "Create a clinical-style summary focusing on diagnoses, treatments, and key findings."
        elif summary_style == "concise":
            style_instruction = "Create a brief 2-3 sentence summary capturing the most important medical information."
        elif summary_style == "detailed":
            style_instruction = "Create a comprehensive summary including all relevant medical details."
        else:
            style_instruction = "Create a clear medical summary."
        
        # Add metadata context if available
        metadata_context = ""
        if chunk_metadata:
            source = chunk_metadata.get("source", "medical document")
            total_matches = chunk_metadata.get("total_matches", 0)
            chunks_analyzed = chunk_metadata.get("chunks_analyzed", 0)
            
            if total_matches > 0:
                metadata_context = f"\nContext: Analyzing {chunks_analyzed} text chunks from {source} (found {total_matches} relevant sections).\n"
        
        # Create prompt for LLM
        prompt = f"""{style_instruction}
{metadata_context}
Text to summarize:
---
{chunk_content}
---

Provide a clear medical summary based on the above text. Focus on clinically relevant information and maintain accuracy."""

        # Call LLM to generate summary
        try:
            summary = await generate_text(
                prompt=prompt,
                system_instruction=self.get_system_instruction(),
                temperature=0.3,  # Lower temperature for factual medical summaries
                max_tokens=1000
            )
            
            if not summary:
                return "Unable to generate summary. Please try again."
            
            # Return plain text summary (base class handles Artifact wrapping)
            return summary.strip()
            
        except Exception as e:
            self.logger.error(f"LLM summarization failed: {e}")
            return f"Error generating summary: {str(e)}"
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """Return agent skills for the AgentCard."""
        return [
            AgentSkill(
                id="medical_summarization",
                name="Medical Text Summarization",
                description="Generate clinically relevant summaries from medical text using LLM",
                tags=["summarization", "medical", "clinical", "llm"],
                examples=[
                    "Summarize medical findings",
                    "Create clinical summary",
                    "Generate concise medical brief",
                    "Summarize patient records"
                ],
                input_modes=["text/plain", "application/json"],
                output_modes=["text/plain"]
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
    print(f"🤖 LLM-powered summarization (no fallbacks)")
    print(f"📝 Returns text summaries as Artifacts")
    print("\n📝 Example input:")
    print('  {"chunk_content": "medical text...", "summary_style": "clinical"}')
    
    uvicorn.run(app, host="0.0.0.0", port=port)