"""
Keyword Pattern Generator Agent
LLM-powered agent that analyzes medical document previews and generates
regex patterns for identifying key information.
"""

import json
import re
from typing import List, Dict, Any, Optional

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
        return False

    def get_system_instruction(self) -> str:
        return (
            "You are a medical document pattern generator specializing in creating "
            "ripgrep-compatible regex patterns. Generate precise patterns that identify "
            "clinical information including diagnoses, medications, procedures, vitals, "
            "lab values, and temporal markers. Use (?i) for case-insensitive matching "
            "where appropriate. Balance specificity to minimize false positives."
        )

    # --- Core Processing ---
    async def process_message(self, message: str) -> str:
        """
        Generate regex patterns from document preview.
        Input can be plain text or JSON with document_preview and focus_areas.
        Returns JSON with categorized patterns.
        """
        try:
            # Parse input
            data = self._parse_input(message)
            preview = data.get("document_preview", message[:4000])
            focus_areas = data.get("focus_areas", [])
            
            # Generate patterns using LLM
            patterns = await self._generate_patterns(preview, focus_areas)
            
            # Ensure we have fallback patterns if needed
            patterns = self._ensure_minimum_patterns(patterns)
            
            # Return as JSON
            return json.dumps(patterns, indent=2)
            
        except Exception as e:
            logger.error(f"Error generating patterns: {e}")
            # Return fallback patterns
            return json.dumps(self._get_fallback_patterns_json())

    async def _generate_patterns(self, preview: str, focus_areas: List[str]) -> Dict[str, List[Dict[str, str]]]:
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
                temperature=0.3,  # Low temperature for consistency
                max_tokens=2000,
                strict=False  # Be flexible while patterns stabilize
            )
            
            # Validate and clean patterns
            result = self._validate_patterns(result)
            
            return result
            
        except Exception as e:
            logger.warning(f"LLM pattern generation failed: {e}, using enhanced fallbacks")
            return self._get_fallback_patterns_json()

    def _build_pattern_prompt(self, preview: str, focus_areas: List[str]) -> str:
        """Build prompt for pattern generation."""
        prompt = f"""Generate ripgrep-compatible regex patterns to search the FULL medical document.
You are seeing only a preview of the first {len(preview)} characters.

DOCUMENT PREVIEW:
{preview}

REQUIREMENTS:
1. Create patterns that will find relevant information throughout the ENTIRE document
2. Use (?i) for case-insensitive matching where appropriate
3. Include common medical abbreviations and variations
4. Avoid overly broad patterns that cause false positives
5. Escape special regex characters properly
6. Test for both structured and narrative text formats

"""
        
        if focus_areas:
            prompt += f"FOCUS AREAS: {', '.join(focus_areas)}\n"
            prompt += "Prioritize patterns related to these areas.\n\n"
        
        prompt += """PATTERN CATEGORIES NEEDED:
- Section headers (History, Assessment, Plan, etc.)
- Clinical findings (diagnoses, symptoms, conditions)
- Medications (drug names, dosages, frequencies)
- Temporal markers (dates, durations, timing)
- Vital signs (BP, HR, temp, weight, etc.)

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

    def _ensure_minimum_patterns(self, patterns: Dict[str, List[Dict[str, str]]]) -> Dict[str, List[Dict[str, str]]]:
        """Ensure we have at least some patterns in each category."""
        # Count total patterns
        total = sum(len(p) for p in patterns.values())
        
        if total < 5:
            # Merge with fallback patterns
            fallbacks = self._get_fallback_patterns_json()
            for category in fallbacks:
                if category not in patterns:
                    patterns[category] = fallbacks[category]
                elif len(patterns[category]) == 0:
                    patterns[category] = fallbacks[category]
        
        return patterns

    def _get_fallback_patterns_json(self) -> Dict[str, List[Dict[str, str]]]:
        """Get fallback patterns in structured format."""
        return {
            "section_patterns": [
                {"pattern": r"(?i)^\s*(history|hx)(?:\s+of)?(?:\s+present)?(?:\s+illness)?", "priority": "high", "description": "History section"},
                {"pattern": r"(?i)^\s*(assessment|a&p|assessment\s+and\s+plan)", "priority": "high", "description": "Assessment section"},
                {"pattern": r"(?i)^\s*(plan|treatment\s+plan|management)", "priority": "high", "description": "Plan section"},
                {"pattern": r"(?i)^\s*(physical\s+exam(?:ination)?|pe|exam)", "priority": "medium", "description": "Physical exam section"},
            ],
            "clinical_patterns": [
                {"pattern": r"(?i)diabetes(?:\s+mellitus)?(?:\s+type\s+[12])?", "priority": "high", "description": "Diabetes diagnosis"},
                {"pattern": r"(?i)hypertension|htn|high\s+blood\s+pressure", "priority": "high", "description": "Hypertension"},
                {"pattern": r"(?i)coronary\s+artery\s+disease|cad|mi|myocardial\s+infarction", "priority": "high", "description": "Heart disease"},
                {"pattern": r"(?i)diagnosis(?:es)?[:]\s*", "priority": "high", "description": "Diagnosis marker"},
                {"pattern": r"(?i)chief\s+complaint|cc|presenting\s+complaint", "priority": "medium", "description": "Chief complaint"},
            ],
            "medication_patterns": [
                {"pattern": r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|cc|units?|iu)\b", "priority": "high", "description": "Medication dosage"},
                {"pattern": r"(?i)metformin|lisinopril|atorvastatin|aspirin|insulin", "priority": "high", "description": "Common medications"},
                {"pattern": r"(?i)(?:medication|med|rx)s?\s*[:]\s*", "priority": "medium", "description": "Medication section marker"},
                {"pattern": r"(?i)(?:q\.?d\.?|b\.?i\.?d\.?|t\.?i\.?d\.?|q\.?i\.?d\.?|prn|daily|twice|three\s+times)", "priority": "medium", "description": "Medication frequency"},
            ],
            "temporal_patterns": [
                {"pattern": r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", "priority": "high", "description": "Date MM/DD/YYYY"},
                {"pattern": r"\b\d{4}-\d{2}-\d{2}\b", "priority": "high", "description": "Date YYYY-MM-DD"},
                {"pattern": r"(?i)(?:yesterday|today|tomorrow|last\s+(?:week|month|year))", "priority": "medium", "description": "Relative time"},
                {"pattern": r"\b\d+\s*(?:day|week|month|year)s?\s+ago\b", "priority": "medium", "description": "Time duration"},
            ],
            "vital_patterns": [
                {"pattern": r"(?i)(?:blood\s+pressure|bp)[\s:]+\d{2,3}/\d{2,3}", "priority": "high", "description": "Blood pressure"},
                {"pattern": r"(?i)(?:heart\s+rate|hr|pulse)[\s:]+\d{2,3}", "priority": "high", "description": "Heart rate"},
                {"pattern": r"(?i)(?:temperature|temp)[\s:]+\d{2,3}(?:\.\d)?", "priority": "high", "description": "Temperature"},
                {"pattern": r"(?i)(?:weight|wt)[\s:]+\d+(?:\.\d+)?\s*(?:kg|lbs?|pounds?)", "priority": "medium", "description": "Weight"},
                {"pattern": r"(?i)(?:height|ht)[\s:]+\d+(?:'\d+\"|cm|inches?)", "priority": "medium", "description": "Height"},
            ]
        }