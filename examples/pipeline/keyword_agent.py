#!/usr/bin/env python3
"""
Keyword Pattern Generator Agent - Generates regex patterns from document previews.
Uses LLM to identify patterns for finding medical information and dates.
No fallback patterns - always uses LLM for authentic pattern generation.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel, Field

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base import A2AAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill


# Pydantic model for structured keyword patterns
class PatternGroup(BaseModel):
    """Group of related patterns with metadata."""
    category: str = Field(description="Category of patterns (medical, dates, sections)")
    patterns: List[str] = Field(description="List of regex patterns")
    priority: str = Field(description="Priority level: high, medium, low")
    description: str = Field(description="What these patterns match")


class KeywordPatterns(BaseModel):
    """Structured output for keyword pattern generation."""
    document_type: str = Field(description="Type of document analyzed")
    total_patterns: int = Field(description="Total number of patterns generated")
    pattern_groups: List[PatternGroup] = Field(description="Organized groups of patterns")
    
    # Specific pattern categories we need
    medical_patterns: List[str] = Field(
        description="Patterns for medical terms, conditions, medications"
    )
    date_patterns: List[str] = Field(
        description="Patterns for finding all dates and temporal markers"
    )
    section_patterns: List[str] = Field(
        description="Patterns for document sections and headers"
    )
    clinical_summary_patterns: List[str] = Field(
        description="Patterns specifically for clinical summary sections"
    )


class KeywordAgent(A2AAgent):
    """LLM-powered keyword pattern generator for medical documents."""
    
    def get_agent_name(self) -> str:
        """Return the agent's name."""
        return "Keyword Pattern Generator"
    
    def get_agent_description(self) -> str:
        """Return detailed agent description."""
        return (
            "LLM-powered agent that analyzes medical document previews and generates "
            "regex patterns for identifying clinical summaries, dates, medical terms, "
            "and document sections. Always uses LLM for authentic pattern generation."
        )
    
    def get_agent_version(self) -> str:
        """Return agent version."""
        return "3.0.0"
    
    def get_system_instruction(self) -> str:
        """Return the system instruction for pattern generation."""
        return """You are a medical document pattern generator. Analyze document previews and generate regex patterns.

CRITICAL REQUIREMENTS:
1. Generate patterns to find clinical summary sections
2. Find ALL dates and temporal markers in the document
3. Identify medical terminology and conditions
4. Locate section headers and document structure

When you receive a document preview, generate regex patterns that:
- Use ripgrep-compatible syntax
- Include case-insensitive flags (?i) where appropriate
- Are specific enough to avoid false positives
- Cover both abbreviated and full forms of medical terms

Focus especially on:
- Clinical summaries and assessment sections
- Every date format (MM/DD/YYYY, DD-MM-YYYY, Month DD YYYY, etc.)
- Temporal phrases (yesterday, last week, 3 days ago, etc.)
- Medical diagnoses and medications
- Vital signs and lab values

Return patterns using the KeywordPatterns structure with proper categorization."""
    
    # No tools needed - everything happens in process_message
    
    async def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process the message and return keyword patterns.
        
        This method is called when tools don't handle the request.
        We'll use it to ensure proper pattern generation.
        
        Args:
            message: Document preview or pattern generation request
            
        Returns:
            Dictionary with keyword patterns for DataPart
        """
        # Parse the message to get document preview
        try:
            if isinstance(message, str) and message.startswith('{'):
                data = json.loads(message)
                preview = data.get('document_preview', data.get('preview', message))
            else:
                preview = message
        except:
            preview = message
        
        # Call LLM to generate patterns (no fallbacks!)
        from utils.llm_utils import generate_text
        
        # Create prompt for pattern generation
        prompt = f"""Analyze this medical document preview and generate comprehensive regex patterns.

Document Preview:
{preview[:1500]}

Generate patterns in this EXACT JSON structure (no other text):
{{
    "document_type": "medical_record",
    "total_patterns": 15,
    "pattern_groups": [],
    "medical_patterns": [
        "(?i)diabetes",
        "(?i)hypertension",
        "(?i)metformin",
        "\\\\d+\\\\s*mg"
    ],
    "date_patterns": [
        "\\\\d{{1,2}}/\\\\d{{1,2}}/\\\\d{{4}}",
        "\\\\d{{4}}-\\\\d{{2}}-\\\\d{{2}}"
    ],
    "section_patterns": [
        "(?i)^CHIEF COMPLAINT:",
        "(?i)^ASSESSMENT"
    ],
    "clinical_summary_patterns": [
        "(?i)ASSESSMENT AND PLAN"
    ]
}}

Requirements:
- Fill ALL arrays with REAL patterns from the document
- In JSON, use double backslash (\\\\) for regex escaping (e.g., "\\\\d+" for digits)
- Include specific medical terms you find
- Find ALL date formats in the document
- Return ONLY the JSON object, no other text"""

        # Get LLM response
        llm_response = await generate_text(
            prompt=prompt,
            system_instruction=self.get_system_instruction(),
            temperature=0.3,  # Lower temperature for consistent patterns
            max_tokens=3000  # Increased to avoid truncation
        )
        
        # Log the raw LLM response for debugging
        self.logger.info(f"LLM response length: {len(llm_response) if llm_response else 0}")
        self.logger.debug(f"Raw LLM response: {llm_response[:500] if llm_response else 'None'}")
        
        # Parse and validate with Pydantic
        try:
            # Clean up response if needed
            cleaned_response = llm_response
            if llm_response and '```json' in llm_response:
                # Extract JSON from code block
                start = llm_response.find('```json') + 7
                end = llm_response.find('```', start)
                if end > start:
                    cleaned_response = llm_response[start:end]
                    self.logger.info("Extracted JSON from code block")
            
            # Parse JSON
            self.logger.info(f"Attempting to parse JSON of length {len(cleaned_response)}")
            pattern_data = json.loads(cleaned_response)
            self.logger.info(f"Successfully parsed JSON with keys: {list(pattern_data.keys())}")
            
            # Create Pydantic model
            patterns = KeywordPatterns(**pattern_data)
            self.logger.info(f"Created KeywordPatterns with {patterns.total_patterns} total patterns")
            
            # Return as dict for DataPart
            result = patterns.model_dump()
            self.logger.info(f"Returning pattern dict with medical_patterns: {len(result.get('medical_patterns', []))}")
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing failed at position {e.pos}: {e}")
            
            # Log more context around the error
            if cleaned_response and e.pos:
                start = max(0, e.pos - 50)
                end = min(len(cleaned_response), e.pos + 50)
                self.logger.error(f"Context around error: ...{cleaned_response[start:end]}...")
            else:
                self.logger.error(f"Failed to parse: {cleaned_response[:200] if cleaned_response else 'empty response'}")
            
            # NO FALLBACK PATTERNS - return empty as required
            error_result = KeywordPatterns(
                document_type="parse_error",
                total_patterns=0,
                pattern_groups=[],
                medical_patterns=[],
                date_patterns=[],
                section_patterns=[],
                clinical_summary_patterns=[]
            )
            
            self.logger.error("LLM did not return valid JSON - returning empty patterns")
            return error_result.model_dump()
            
        except Exception as e:
            self.logger.error(f"Pattern generation failed completely: {e}")
            self.logger.error(f"LLM response was: {llm_response[:200] if llm_response else 'None'}")
            
            # Return minimal valid structure
            error_result = KeywordPatterns(
                document_type="unknown",
                total_patterns=0,
                pattern_groups=[],
                medical_patterns=[],
                date_patterns=[],
                section_patterns=[],
                clinical_summary_patterns=[]
            )
            
            return error_result.model_dump()
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """Return agent skills for the AgentCard."""
        return [
            AgentSkill(
                id="generate_keyword_patterns",
                name="Generate Keyword Patterns",
                description="Analyze document and generate regex patterns for medical information and dates",
                tags=["pattern-generation", "regex", "medical", "dates", "llm-powered"],
                examples=[
                    "Generate patterns from document preview",
                    "Find all date patterns in medical record",
                    "Identify clinical summary sections",
                    "Extract medical terminology patterns"
                ],
                input_modes=["application/json", "text/plain"],
                output_modes=["application/json"]
            )
        ]
    
    def supports_streaming(self) -> bool:
        """Enable streaming for real-time pattern generation."""
        return True


# Module-level app creation for HealthUniverse deployment
agent = KeywordAgent()
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
    port = int(os.getenv("PORT", 8002))
    
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    print(f"🛠️ LLM-powered pattern generation (no fallbacks)")
    print("\n📝 Example queries:")
    print('  - "Analyze this document and generate search patterns"')
    print('  - "Find all date patterns in this medical record"')
    print('  - "Generate patterns for clinical summary sections"')
    
    uvicorn.run(app, host="0.0.0.0", port=port)