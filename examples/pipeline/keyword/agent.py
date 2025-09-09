"""
Keyword Pattern Generator Agent
LLM-powered agent that analyzes medical document previews and generates
regex patterns for identifying key information.
"""

import json
import re
from typing import List, Dict, Any, Optional, Union

from a2a.types import AgentSkill
from base import A2AAgent
from utils.logging import get_logger
from utils.llm_utils import generate_json

logger = get_logger(__name__)


class KeywordAgent(A2AAgent):
    """
    LLM-powered keyword extraction agent that generates regex patterns from documents.
    Uses generate_json() for structured pattern generation.
    """

    # --- A2A Metadata ---
    def get_agent_name(self) -> str:
        return "CS Pipeline - Keyword Generator"

    def get_agent_description(self) -> str:
        return (
            "LLM-powered agent that analyzes medical document previews and generates "
            "regex patterns for identifying key information such as diagnoses, medications, "
            "procedures, and temporal markers."
        )

    def get_agent_version(self) -> str:
        return "2.0.0"  # Template-based version

    def get_agent_skills(self) -> List[AgentSkill]:
        return [
            AgentSkill(
                id="generate_patterns",
                name="Generate Document Patterns",
                description="Analyze document and generate regex patterns using LLM",
                tags=["keyword", "pattern", "extraction", "llm", "medical"],
                inputModes=["text/plain", "application/json"],
                outputModes=["application/json"],
            )
        ]

    def supports_streaming(self) -> bool:
        return True

    def get_system_instruction(self) -> str:
        return (
            "You are an oncological timeline extractor specializing in cancer treatment histories. "
            "Generate ripgrep-compatible regex patterns to build comprehensive cancer timelines. "
            "Focus on: 1) ALL dates in any format, 2) Treatment modalities (chemo, radiation, "
            "surgery, immunotherapy), 3) Treatment cycles and dosing schedules, 4) Disease "
            "staging and progression, 5) Scan dates and response assessments, 6) Key cancer "
            "drugs and biomarkers. Your patterns should capture the complete journey from "
            "diagnosis through treatment lines to response/progression. Use (?i) for "
            "case-insensitive matching. Prioritize temporal patterns and cancer-specific terms."
        )

    # --- Core Processing ---
    async def process_message(self, message: str) -> Union[Dict[str, Any], str]:
        """
        Generate regex patterns from document preview.
        Input can be plain text or JSON with document_preview and focus_areas.
        Returns dict with categorized patterns (will be wrapped in DataPart by framework).
        """
        try:
            # Parse input
            data = self._parse_input(message)
            preview = data.get("document_preview", message[:4000])
            focus_areas = data.get("focus_areas", [])
            
            # Generate patterns using LLM with retry logic
            patterns = await self._generate_patterns(preview, focus_areas)
            
            # Check if LLM returned nothing and retry with a simpler prompt
            if not patterns.get("patterns") or len(patterns.get("patterns", [])) == 0:
                logger.warning("LLM returned no patterns, retrying with simplified prompt...")
                patterns = await self._generate_patterns_simple_retry(preview)
            
            # Ensure we have fallback patterns if needed
            patterns = self._ensure_minimum_patterns(patterns)
            
            # ALWAYS add diagnostic info
            patterns["diagnostic_info"] = {
                "api_keys_detected": self._check_api_keys(),
                "provider_info": self._get_provider_info(),
                "pattern_count": len(patterns.get("patterns", [])),
                "source": patterns.get("source", "unknown")
            }
            
            # Return as dict (will become DataPart)
            return patterns
            
        except Exception as e:
            logger.error(f"Error generating patterns: {e}")
            # Return empty patterns with error info - NO FALLBACKS
            return {
                "medical_patterns": [],
                "date_patterns": [],
                "section_patterns": [],
                "clinical_summary_patterns": [],
                "patterns": [],  # Empty flat list for compatibility
                "diagnostic_info": {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "api_keys_detected": self._check_api_keys(),
                    "provider_info": self._get_provider_info(),
                    "source": "error_no_patterns"
                }
            }

    async def _generate_patterns(self, preview: str, focus_areas: List[str]) -> Dict[str, Any]:
        """Generate patterns using structured LLM output."""
        
        # Build focused prompt
        prompt = self._build_pattern_prompt(preview, focus_areas)
        
        # Define schema for structured output
        schema = {
            "type": "object",
            "properties": {
                "section_patterns": {
                    "type": "array",
                    "description": "Patterns for document section headers",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "Regex pattern"},
                            "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                            "description": {"type": "string", "description": "What this pattern matches"}
                        },
                        "required": ["pattern", "priority", "description"]
                    }
                },
                "clinical_patterns": {
                    "type": "array",
                    "description": "Patterns for clinical findings and diagnoses",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string"},
                            "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                            "description": {"type": "string"}
                        },
                        "required": ["pattern", "priority", "description"]
                    }
                },
                "medication_patterns": {
                    "type": "array",
                    "description": "Patterns for medications and dosages",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string"},
                            "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                            "description": {"type": "string"}
                        },
                        "required": ["pattern", "priority", "description"]
                    }
                },
                "temporal_patterns": {
                    "type": "array",
                    "description": "Patterns for dates and time references",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string"},
                            "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                            "description": {"type": "string"}
                        },
                        "required": ["pattern", "priority", "description"]
                    }
                },
                "vital_patterns": {
                    "type": "array",
                    "description": "Patterns for vital signs and measurements",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string"},
                            "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                            "description": {"type": "string"}
                        },
                        "required": ["pattern", "priority", "description"]
                    }
                }
            },
            "required": ["section_patterns", "clinical_patterns", "medication_patterns"]
        }
        
        try:
            # Generate patterns with structured output
            result = await generate_json(
                prompt=prompt,
                system_instruction=self.get_system_instruction(),
                schema=schema,
                temperature=0.0,  # Zero temperature for deterministic output
                max_tokens=2000,
                strict=False  # Be flexible while patterns stabilize
            )
            
            # Validate and clean patterns
            result = self._validate_patterns(result)
            
            # Add source tracking
            result["source"] = "llm"
            result["status"] = "success"
            
            # Transform to expected format for orchestrator
            # Extract just the pattern strings from each category
            transformed = {
                "medical_patterns": [],
                "date_patterns": [],
                "section_patterns": [],
                "clinical_summary_patterns": [],
                "patterns": []  # Flat list for compatibility
            }
            
            # Map the generated categories to expected names
            if "medication_patterns" in result:
                for p in result["medication_patterns"]:
                    if isinstance(p, dict) and "pattern" in p:
                        transformed["medical_patterns"].append(p["pattern"])
            
            if "temporal_patterns" in result:
                for p in result["temporal_patterns"]:
                    if isinstance(p, dict) and "pattern" in p:
                        transformed["date_patterns"].append(p["pattern"])
                        
            if "section_patterns" in result:
                for p in result["section_patterns"]:
                    if isinstance(p, dict) and "pattern" in p:
                        transformed["section_patterns"].append(p["pattern"])
                        
            if "clinical_patterns" in result:
                for p in result["clinical_patterns"]:
                    if isinstance(p, dict) and "pattern" in p:
                        transformed["clinical_summary_patterns"].append(p["pattern"])
            
            # Create flat list
            transformed["patterns"] = (
                transformed["medical_patterns"] + 
                transformed["date_patterns"] + 
                transformed["section_patterns"] + 
                transformed["clinical_summary_patterns"]
            )
            
            # Add metadata
            transformed["source"] = result.get("source", "llm")
            transformed["status"] = result.get("status", "success")
            
            return transformed
            
        except Exception as e:
            logger.error(f"LLM pattern generation failed: {e}")
            # Return empty patterns - NO FALLBACKS
            return {
                "medical_patterns": [],
                "date_patterns": [],
                "section_patterns": [],
                "clinical_summary_patterns": [],
                "patterns": [],  # Empty flat list for compatibility
                "source": "llm_failed",
                "status": "error",
                "llm_error": {
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:500],  # Limit error message length
                    "provider_attempted": self._get_provider_info().get("provider", "unknown")
                }
            }

    async def _generate_patterns_simple_retry(self, preview: str) -> Dict[str, Any]:
        """Retry pattern generation with a much simpler prompt."""
        logger.info("Attempting simplified pattern generation...")
        
        # Oncology-focused prompt for retry
        simple_prompt = f"""Generate regex patterns to extract an ONCOLOGICAL TIMELINE from this medical document:

{preview[:2000]}

Focus on finding:
1. ALL dates (any format) 
2. Cancer treatment terms (chemo, radiation, surgery, immunotherapy)
3. Treatment cycles (Cycle 1, C1D1, etc.)
4. Staging (Stage IV, T2N1M0, etc.)
5. Response terms (progression, stable, response)
6. Scan dates and results
7. Drug names and dosages

Return JSON with these arrays:
- "medical_patterns": cancer-specific terms
- "date_patterns": ALL date formats
- "patterns": combined list

Example:
{{
  "medical_patterns": ["(?i)\\\\bchemo", "(?i)\\\\bcycle\\\\s*\\\\d+", "(?i)\\\\bprogress"],
  "date_patterns": ["\\\\d{{1,2}}/\\\\d{{1,2}}/\\\\d{{4}}", "(?i)\\\\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\\\w*\\\\s+\\\\d{{1,2}}"],
  "patterns": [all patterns combined]
}}

Generate patterns for building a cancer treatment timeline."""
        
        try:
            # Try with plain text response and parse it
            from utils.llm_utils import generate_text
            response = await generate_text(
                prompt=simple_prompt,
                system_instruction="You are a regex pattern generator. Return only valid JSON.",
                temperature=0.3,  # Slightly higher temperature for retry
                max_tokens=1500
            )
            
            # Try to extract JSON from response
            import json
            import re
            
            # Find JSON in response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    # Ensure expected structure
                    if not isinstance(result, dict):
                        result = {}
                    for key in ["medical_patterns", "date_patterns", "patterns"]:
                        if key not in result:
                            result[key] = []
                    result["source"] = "llm_retry"
                    return result
                except:
                    pass
            
            # If all else fails, return empty
            return {
                "medical_patterns": [],
                "date_patterns": [],
                "patterns": [],
                "source": "llm_retry_failed"
            }
            
        except Exception as e:
            logger.error(f"Retry also failed: {e}")
            return {
                "medical_patterns": [],
                "date_patterns": [],
                "patterns": [],
                "source": "llm_retry_error"
            }
    
    def _build_pattern_prompt(self, preview: str, focus_areas: List[str]) -> str:
        """Build prompt for timeline-focused pattern generation."""
        prompt = f"""Generate ripgrep-compatible regex patterns to BUILD A PATIENT TIMELINE from the FULL medical document.
You are seeing only a preview of the first {len(preview)} characters.

DOCUMENT PREVIEW:
{preview}

PRIMARY GOAL: Extract EVERY date and its associated medical events to build a complete patient timeline.

REQUIREMENTS:
1. Find ALL dates in ANY format (MM/DD/YYYY, YYYY-MM-DD, Month DD YYYY, etc.)
2. Find events that happen AT dates (admitted on, diagnosed on, surgery on)
3. Find temporal relationships (since 2020, before surgery, after discharge)
4. Use (?i) for case-insensitive matching
5. Capture medication changes with dates (started, stopped, changed dose)
6. Find procedure dates and appointment dates
7. Prioritize finding WHEN things happened over WHAT happened

"""
        
        if focus_areas:
            prompt += f"TIMELINE FOCUS: {', '.join(focus_areas)}\n"
            prompt += "Extract patterns that show WHEN these events occurred.\n\n"
        
        prompt += """PATTERN CATEGORIES NEEDED (in priority order):
- Temporal patterns (ALL date formats, years, months, relative times)
- Event patterns (admitted, discharged, diagnosed, underwent, started, stopped)
- Medication patterns (focus on changes: started, discontinued, dose changed)
- Clinical patterns (with temporal context: diagnosed with X in/on DATE)
- Vital patterns (timestamped vital signs)

CRITICAL: Prioritize temporal patterns above everything else. We need dates!

Return ONLY valid JSON matching the schema. No additional text."""
        
        return prompt

    def _parse_input(self, message: str) -> Dict[str, Any]:
        """Parse input message which may be JSON or plain text."""
        try:
            data = json.loads(message)
            if isinstance(data, dict):
                return data
            return {"document_preview": message}
        except:
            return {"document_preview": message}

    def _validate_patterns(self, patterns: Dict[str, List[Dict[str, str]]]) -> Dict[str, List[Dict[str, str]]]:
        """Validate that patterns are valid regex."""
        validated = {}
        
        for category, pattern_list in patterns.items():
            validated[category] = []
            for pattern_obj in pattern_list:
                if isinstance(pattern_obj, dict) and "pattern" in pattern_obj:
                    try:
                        # Test compile the pattern
                        re.compile(pattern_obj["pattern"])
                        validated[category].append(pattern_obj)
                    except re.error as e:
                        logger.debug(f"Invalid pattern '{pattern_obj['pattern']}': {e}")
        
        return validated

    def _ensure_minimum_patterns(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure we always have essential date patterns as a baseline."""
        # ALWAYS add comprehensive date patterns as a reliable baseline
        # These are critical for building patient timelines
        essential_date_patterns = [
            # Standard date formats
            r"(?i)\b\d{1,2}/\d{1,2}/\d{2,4}\b",  # MM/DD/YYYY or M/D/YY
            r"(?i)\b\d{4}-\d{2}-\d{2}\b",  # YYYY-MM-DD
            r"(?i)\b\d{2}-\d{2}-\d{4}\b",  # DD-MM-YYYY
            r"(?i)\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",  # Month DD, YYYY
            r"(?i)\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b",  # DD Month YYYY
            r"(?i)\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",  # Full month
            
            # Relative dates and temporal markers
            r"(?i)\b(yesterday|today|tomorrow|last\s+week|next\s+week|last\s+month|next\s+month)\b",
            r"(?i)\b\d+\s+(days?|weeks?|months?|years?)\s+(ago|later|after|before|prior|since)\b",
            r"(?i)\b(since|from|until|before|after|during|between|prior\s+to|as\s+of)\s+\d{4}\b",
            
            # Medical temporal context
            r"(?i)\b(admitted|discharged|diagnosed|underwent|started|stopped|began|discontinued)\s+(?:on\s+)?\d{1,2}/\d{1,2}/\d{2,4}\b",
            r"(?i)\bon\s+\d{1,2}/\d{1,2}/\d{2,4}\b",  # "on DATE"
            r"(?i)\b(admission|discharge|diagnosis|surgery|procedure)\s+date:?\s*\d{1,2}/\d{1,2}/\d{2,4}\b",
            
            # Year references
            r"(?i)\b(19|20)\d{2}\b",  # Years 1900-2099
            r"(?i)\bin\s+(19|20)\d{2}\b",  # "in YEAR"
            
            # Time with dates
            r"(?i)\b\d{1,2}:\d{2}\s*(am|pm|AM|PM)?\b",  # Time
            r"(?i)\b\d{1,2}/\d{1,2}/\d{2,4}\s+at\s+\d{1,2}:\d{2}\b",  # Date at time
        ]
        
        # Ensure date_patterns exists and add our essential patterns
        if "date_patterns" not in patterns:
            patterns["date_patterns"] = []
        
        # Add essential patterns that aren't already there
        existing = set(patterns.get("date_patterns", []))
        for pattern in essential_date_patterns:
            if pattern not in existing:
                patterns["date_patterns"].append(pattern)
        
        # Also ensure patterns flat list includes all date patterns
        if "patterns" in patterns:
            for pattern in essential_date_patterns:
                if pattern not in patterns["patterns"]:
                    patterns["patterns"].append(pattern)
        
        # Add essential oncology patterns for cancer timeline extraction
        essential_medical_patterns = [
            # Treatment modalities (non-overlapping)
            r"(?i)\bchemo",  # catches chemotherapy, chemo
            r"(?i)\bradiat",  # catches radiation, radiotherapy  
            r"(?i)\bimmuno",  # catches immunotherapy
            r"(?i)\btarget",  # catches targeted therapy
            r"(?i)\bsurg",    # catches surgery, surgical
            r"(?i)\bresect",  # catches resection, resected
            
            # Dosing and cycles
            r"(?i)\b\d+\s*mg",  # all dosages including mg/m2
            r"(?i)\binfusion\b",
            r"(?i)\bcycle\s*\d+",  # Cycle 1, cycle 2, etc.
            r"(?i)\b[CD]\d+",  # C1D1, D15, etc.
            
            # Staging/grading  
            r"(?i)\bstage\s*[IVX1-4]",  # Stage I-IV, Stage 1-4
            r"(?i)\b[TN][0-4]",  # T1-4, N0-3
            r"(?i)\bM[01]",  # M0, M1
            r"(?i)\bgrade\s*[1-3]",
            
            # Response and progression
            r"(?i)\bprogress",  # progression, progressive
            r"(?i)\bresponse\b",
            r"(?i)\bstable\b",
            r"(?i)\brecur",  # recurrence, recurrent
            r"(?i)\b(CR|PR|SD|PD)\b",  # Response abbreviations
            
            # Imaging
            r"(?i)\b(CT|PET|MRI|scan)\b",
            
            # Key biomarkers
            r"(?i)\b(EGFR|ALK|PD-L1|HER2|BRCA|MSI|TMB)\b",
            
            # Common chemo drugs (top ones only to avoid redundancy)
            r"(?i)\b(carboplatin|paclitaxel|pembrolizumab|nivolumab|doxorubicin)\b",
            
            # General medical (keep minimal)
            r"(?i)\bdiagnos",  # diagnosis, diagnosed
            r"(?i)\badmit",    # admission, admitted
            r"(?i)\bdischarg", # discharge, discharged
        ]
        
        # Add medical patterns to ensure we have something useful
        if "medical_patterns" not in patterns:
            patterns["medical_patterns"] = []
        
        for pattern in essential_medical_patterns:
            if pattern not in patterns.get("medical_patterns", []):
                patterns["medical_patterns"].append(pattern)
            if "patterns" in patterns and pattern not in patterns["patterns"]:
                patterns["patterns"].append(pattern)
        
        # Count total patterns after adding essentials
        total = len(patterns.get("patterns", []))
        if total < 10:
            logger.warning(f"Only {total} total patterns after adding essentials - LLM may have issues")
        else:
            logger.info(f"Generated {total} total patterns including essential date and medical patterns")
        
        return patterns

    
    def _check_api_keys(self) -> Dict[str, bool]:
        """Check which API keys are present (without exposing values)"""
        import os
        return {
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
            "google": bool(os.getenv("GOOGLE_API_KEY")),
            "gemini": bool(os.getenv("GEMINI_API_KEY"))
        }
    
    def _get_provider_info(self) -> Dict[str, str]:
        """Get info about which provider would be used"""
        import os
        if os.getenv("ANTHROPIC_API_KEY"):
            return {"provider": "anthropic", "model": "claude-3-5-sonnet"}
        elif os.getenv("OPENAI_API_KEY"):
            return {"provider": "openai", "model": "gpt-4o-mini"}
        elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
            return {"provider": "google", "model": "gemini-2.0-flash-exp"}
        else:
            return {"provider": "none", "model": "none"}