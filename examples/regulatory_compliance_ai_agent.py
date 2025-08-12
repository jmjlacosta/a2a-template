#!/usr/bin/env python3
"""
AI-Enhanced Regulatory Compliance Validator Agent

This agent validates clinical trial protocols using pattern detection followed by
AI-powered analysis to accurately determine compliance violations for:
- HIPAA Privacy and Security Rules
- 21 CFR Part 11 (Electronic Records/Signatures)
- IRB (Institutional Review Board) requirements
- ONC HTI-1 (Health Data, Technology, and Interoperability) transparency requirements

The agent uses a two-stage approach:
1. Pattern matching to identify potential areas of concern
2. LLM analysis to determine if the context actually represents a violation
"""

import sys
import json
import re
import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent))

from base import BaseLLMAgentExecutor

logger = logging.getLogger(__name__)


class ComplianceLevel(Enum):
    """Compliance severity levels."""
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"
    NOT_APPLICABLE = "not_applicable"


class RegulatoryFramework(Enum):
    """Regulatory frameworks being checked."""
    HIPAA = "HIPAA"
    CFR_PART_11 = "21 CFR Part 11"
    IRB = "IRB"
    ONC_HTI_1 = "ONC HTI-1"


@dataclass
class ComplianceIssue:
    """Represents a compliance issue found during validation."""
    framework: RegulatoryFramework
    level: ComplianceLevel
    category: str
    description: str
    context: str
    ai_analysis: str
    location: Optional[str] = None
    recommendation: Optional[str] = None
    reference: Optional[str] = None
    confidence: float = 0.0  # AI confidence score


@dataclass
class ComplianceReport:
    """Complete compliance validation report."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    summary: Dict[str, Any] = field(default_factory=dict)
    issues: List[ComplianceIssue] = field(default_factory=list)
    compliant_areas: List[str] = field(default_factory=list)
    risk_score: int = 0
    recommendations: List[str] = field(default_factory=list)
    ai_insights: List[str] = field(default_factory=list)


class RegulatoryComplianceAIAgent(BaseLLMAgentExecutor):
    """
    AI-Enhanced agent that validates clinical trial documentation for regulatory compliance.
    Uses pattern detection followed by LLM analysis for accurate violation assessment.
    """
    
    def __init__(self):
        super().__init__()
        self.compliance_rules = self._initialize_compliance_rules()
        
    def get_agent_name(self) -> str:
        return "AI Regulatory Compliance Validator"
    
    def get_agent_description(self) -> str:
        return (
            "AI-enhanced validation of clinical trial protocols against "
            "HIPAA, 21 CFR Part 11, IRB requirements, and ONC HTI-1 transparency rules. "
            "Uses advanced AI analysis to accurately identify violations and provide "
            "detailed compliance reports with risk assessments and recommendations."
        )
    
    def get_system_instruction(self) -> str:
        return """You are an expert regulatory compliance analyst specializing in healthcare 
        and clinical trials. Your role is to analyze text excerpts and determine if they 
        represent actual regulatory violations or compliance issues.
        
        You have deep knowledge of:
        - HIPAA Privacy and Security Rules
        - 21 CFR Part 11 (Electronic Records and Signatures)
        - IRB requirements and human subjects protection
        - ONC HTI-1 transparency and interoperability requirements
        
        When analyzing text, consider:
        1. The specific regulatory requirement
        2. Whether the text indicates compliance, non-compliance, or is neutral
        3. The severity of any violation (critical, violation, warning, or compliant)
        4. Context clues that indicate proper safeguards or lack thereof
        
        Be precise and avoid false positives. Only flag actual violations or clear risks."""
    
    def get_tools(self) -> List[Any]:
        """
        Return list of tools for the LLM agent.
        For compliance validation, we don't need external tools - just analysis.
        """
        return []  # No external tools needed for compliance analysis
    
    def _initialize_compliance_rules(self) -> Dict[RegulatoryFramework, List[Dict[str, Any]]]:
        """Initialize comprehensive compliance rules for each framework."""
        return {
            RegulatoryFramework.HIPAA: [
                {
                    "category": "PHI Protection",
                    "pattern": r"(patient|participant|subject)\s+(identif|name|SSN|social security|date of birth|DOB|address|phone|email|medical record)",
                    "requirement": "HIPAA requires de-identification of PHI using Safe Harbor (removing 18 identifiers) or Expert Determination",
                    "check_prompt": "Does this text indicate proper de-identification of Protected Health Information (PHI) according to HIPAA Safe Harbor requirements?"
                },
                {
                    "category": "Data Security",
                    "pattern": r"(encrypt|cryptograph|secure|protect|password|authentication|access control)",
                    "requirement": "HIPAA Security Rule requires encryption for PHI at rest (AES-256) and in transit (TLS 1.2+)",
                    "check_prompt": "Does this text demonstrate appropriate encryption and security measures for PHI as required by HIPAA Security Rule?"
                },
                {
                    "category": "Audit Controls",
                    "pattern": r"(audit|log|track|monitor|record access|activity log)",
                    "requirement": "HIPAA requires audit logs tracking who accessed PHI, when, and what actions were taken",
                    "check_prompt": "Does this text show proper audit logging and monitoring as required by HIPAA?"
                },
                {
                    "category": "Authorization",
                    "pattern": r"(consent|authorization|permission|waiver|opt-in|opt-out)",
                    "requirement": "HIPAA requires written authorization for use/disclosure of PHI for research",
                    "check_prompt": "Does this text indicate proper HIPAA authorization or consent procedures?"
                },
                {
                    "category": "Breach Response",
                    "pattern": r"(breach|incident|unauthorized|disclosure|notification|security event)",
                    "requirement": "HIPAA Breach Notification Rule requires notification within 60 days",
                    "check_prompt": "Does this text show adequate breach notification procedures per HIPAA requirements?"
                },
                {
                    "category": "Minimum Necessary",
                    "pattern": r"(minimum necessary|data minimization|need to know|limited data set)",
                    "requirement": "HIPAA Minimum Necessary standard limits PHI use to minimum needed",
                    "check_prompt": "Does this text demonstrate compliance with HIPAA's Minimum Necessary standard?"
                }
            ],
            
            RegulatoryFramework.CFR_PART_11: [
                {
                    "category": "Electronic Records",
                    "pattern": r"(electronic record|e-record|digital document|EDC|electronic data)",
                    "requirement": "21 CFR Part 11 requires validation, audit trails, and record retention for electronic records",
                    "check_prompt": "Does this text show proper controls for electronic records per 21 CFR Part 11?"
                },
                {
                    "category": "Audit Trail",
                    "pattern": r"(audit trail|change history|version control|modification log|track changes)",
                    "requirement": "21 CFR Part 11 requires secure, computer-generated, time-stamped audit trails",
                    "check_prompt": "Does this text indicate compliant audit trails per 21 CFR Part 11 requirements?"
                },
                {
                    "category": "Electronic Signatures",
                    "pattern": r"(electronic signature|e-signature|digital signature|signed electronically)",
                    "requirement": "21 CFR Part 11 requires e-signatures to include printed name, date/time, and meaning",
                    "check_prompt": "Does this text show proper electronic signature implementation per 21 CFR Part 11?"
                },
                {
                    "category": "System Validation",
                    "pattern": r"(validation|qualification|IQ|OQ|PQ|validated system|21 CFR)",
                    "requirement": "21 CFR Part 11 requires documented system validation (IQ/OQ/PQ)",
                    "check_prompt": "Does this text demonstrate proper system validation per 21 CFR Part 11?"
                },
                {
                    "category": "Access Controls",
                    "pattern": r"(access control|user authentication|password|biometric|role-based)",
                    "requirement": "21 CFR Part 11 requires access controls and user authentication",
                    "check_prompt": "Does this text show adequate access controls per 21 CFR Part 11?"
                },
                {
                    "category": "Data Integrity",
                    "pattern": r"(data integrity|backup|recovery|archive|retention|ALCOA)",
                    "requirement": "21 CFR Part 11 requires data integrity and retention procedures",
                    "check_prompt": "Does this text demonstrate proper data integrity controls per 21 CFR Part 11?"
                }
            ],
            
            RegulatoryFramework.IRB: [
                {
                    "category": "Informed Consent",
                    "pattern": r"(informed consent|consent form|participant consent|subject consent)",
                    "requirement": "45 CFR 46.116 requires 8 basic and 6 additional elements in informed consent",
                    "check_prompt": "Does this text show proper informed consent procedures per IRB requirements?"
                },
                {
                    "category": "Risk Assessment",
                    "pattern": r"(risk|benefit|adverse event|safety|harm|minimal risk)",
                    "requirement": "IRB requires thorough risk-benefit assessment per 45 CFR 46.111",
                    "check_prompt": "Does this text demonstrate adequate risk assessment and mitigation?"
                },
                {
                    "category": "Vulnerable Populations",
                    "pattern": r"(children|minor|pregnant|prisoner|vulnerable|impaired|elderly)",
                    "requirement": "45 CFR 46 Subparts B-D require additional protections for vulnerable populations",
                    "check_prompt": "Does this text show proper protections for vulnerable populations?"
                },
                {
                    "category": "Protocol Review",
                    "pattern": r"(protocol|study design|research plan|methodology|IRB approval)",
                    "requirement": "IRB must review and approve all research protocols",
                    "check_prompt": "Does this text indicate proper IRB review and approval processes?"
                },
                {
                    "category": "Safety Monitoring",
                    "pattern": r"(DSMB|data safety|monitoring|stopping rules|safety committee)",
                    "requirement": "IRB requires data safety monitoring plans for higher-risk studies",
                    "check_prompt": "Does this text show adequate safety monitoring procedures?"
                },
                {
                    "category": "Confidentiality",
                    "pattern": r"(confidential|privacy|anonymous|de-identified|coded)",
                    "requirement": "IRB requires protection of participant confidentiality",
                    "check_prompt": "Does this text demonstrate proper confidentiality protections?"
                }
            ],
            
            RegulatoryFramework.ONC_HTI_1: [
                {
                    "category": "Data Transparency",
                    "pattern": r"(data sharing|transparency|open access|public|repository|ClinicalTrials\.gov)",
                    "requirement": "ONC HTI-1 requires transparent data sharing and clinical trial registration",
                    "check_prompt": "Does this text show compliance with data transparency requirements?"
                },
                {
                    "category": "Interoperability",
                    "pattern": r"(FHIR|HL7|interoperab|standard format|USCDI|API)",
                    "requirement": "ONC HTI-1 requires FHIR R4 and USCDI v3 for interoperability",
                    "check_prompt": "Does this text demonstrate proper interoperability standards?"
                },
                {
                    "category": "Patient Access",
                    "pattern": r"(patient access|participant portal|data request|download|export)",
                    "requirement": "ONC HTI-1 requires patient access to their data within 24 hours",
                    "check_prompt": "Does this text show adequate patient data access provisions?"
                },
                {
                    "category": "API Standards",
                    "pattern": r"(API|SMART on FHIR|third-party|application|developer)",
                    "requirement": "ONC HTI-1 requires standardized APIs for third-party applications",
                    "check_prompt": "Does this text indicate proper API implementation?"
                },
                {
                    "category": "Information Blocking",
                    "pattern": r"(information blocking|restrict|withhold|deny access|interference)",
                    "requirement": "ONC HTI-1 prohibits information blocking except for specific exceptions",
                    "check_prompt": "Does this text indicate any information blocking practices?"
                }
            ]
        }
    
    def _extract_context(self, text: str, match_start: int, match_end: int, context_chars: int = 200) -> str:
        """Extract meaningful context around a pattern match."""
        # Find sentence boundaries
        sentences = re.split(r'[.!?]\s+', text)
        
        # Find which sentence(s) contain the match
        current_pos = 0
        relevant_sentences = []
        
        for sentence in sentences:
            sentence_end = current_pos + len(sentence) + 1
            
            # Check if this sentence overlaps with the match
            if (current_pos <= match_start <= sentence_end) or \
               (current_pos <= match_end <= sentence_end) or \
               (match_start <= current_pos and sentence_end <= match_end):
                relevant_sentences.append(sentence.strip())
            
            current_pos = sentence_end
        
        # If we found relevant sentences, use them
        if relevant_sentences:
            context = '. '.join(relevant_sentences)
        else:
            # Fallback to character-based extraction
            start = max(0, match_start - context_chars)
            end = min(len(text), match_end + context_chars)
            context = text[start:end].strip()
        
        # Clean up the context
        context = ' '.join(context.split())  # Normalize whitespace
        
        return context
    
    async def _analyze_with_llm(
        self, 
        context: str, 
        framework: RegulatoryFramework,
        category: str,
        requirement: str,
        check_prompt: str
    ) -> Tuple[ComplianceLevel, str, float]:
        """
        Use LLM to analyze if the context represents a compliance violation.
        
        Returns:
            Tuple of (compliance_level, analysis_explanation, confidence_score)
        """
        prompt = f"""
        Regulatory Framework: {framework.value}
        Category: {category}
        Requirement: {requirement}
        
        Text to Analyze:
        "{context}"
        
        Question: {check_prompt}
        
        Analyze this text and determine:
        1. Compliance Level: Is this COMPLIANT, WARNING, VIOLATION, or CRITICAL?
        2. Explanation: Why did you make this determination?
        3. Confidence: How confident are you (0.0 to 1.0)?
        
        Consider:
        - Does the text explicitly state compliance or non-compliance?
        - Are there safeguards mentioned?
        - Is this just mentioning a topic vs. describing actual practices?
        - Would this pass a regulatory audit?
        
        Respond in JSON format:
        {{
            "level": "COMPLIANT|WARNING|VIOLATION|CRITICAL",
            "explanation": "Brief explanation of your determination",
            "confidence": 0.0-1.0,
            "specific_concern": "The specific issue if any",
            "passes_audit": true/false
        }}
        """
        
        try:
            # Use the LLM agent through runner
            if self._runner and self._agent:
                # Use Google ADK's LLM through the runner
                from google.adk.runners import types
                
                session_id = f"compliance_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Create proper Content message with parts
                text_part = types.Part(text=prompt)
                message = types.Content(parts=[text_part], role="user")
                
                # Use run_async for non-streaming response
                response_text = ""
                async for event in self._runner.run_async(
                    user_id="compliance_validator",
                    session_id=session_id,
                    new_message=message,
                ):
                    if hasattr(event, 'text'):
                        response_text += event.text
                    elif hasattr(event, 'content') and hasattr(event.content, 'text'):
                        response_text += event.content.text
            else:
                # Fallback if no LLM is configured
                logger.warning("No LLM configured, using pattern-based analysis only")
                return ComplianceLevel.WARNING, "LLM not available - pattern-based analysis only", 0.5
            
            # Parse the JSON response
            # Handle potential JSON extraction from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Fallback parsing if JSON not found
                logger.warning(f"Could not parse JSON from LLM response: {response_text[:200]}")
                return ComplianceLevel.WARNING, "Unable to fully analyze - manual review recommended", 0.5
            
            # Map the level
            level_map = {
                "COMPLIANT": ComplianceLevel.COMPLIANT,
                "WARNING": ComplianceLevel.WARNING,
                "VIOLATION": ComplianceLevel.VIOLATION,
                "CRITICAL": ComplianceLevel.CRITICAL
            }
            
            level = level_map.get(result.get("level", "WARNING"), ComplianceLevel.WARNING)
            explanation = result.get("explanation", "Analysis completed")
            confidence = float(result.get("confidence", 0.7))
            
            # Add specific concern to explanation if present
            if result.get("specific_concern"):
                explanation += f" Specific concern: {result['specific_concern']}"
            
            return level, explanation, confidence
            
        except Exception as e:
            logger.error(f"Error in LLM analysis: {str(e)}")
            # Fallback to conservative approach
            return ComplianceLevel.WARNING, f"Manual review recommended - analysis error: {str(e)}", 0.3
    
    async def _analyze_text_for_compliance(
        self, 
        text: str, 
        framework: RegulatoryFramework
    ) -> List[ComplianceIssue]:
        """Analyze text for compliance issues using pattern matching + LLM analysis."""
        issues = []
        rules = self.compliance_rules[framework]
        
        # Track what we've already analyzed to avoid duplicates
        analyzed_contexts = set()
        
        for rule in rules:
            pattern = rule["pattern"]
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            for match in matches:
                # Extract context
                context = self._extract_context(text, match.start(), match.end())
                
                # Skip if we've already analyzed this context
                context_hash = hash(context)
                if context_hash in analyzed_contexts:
                    continue
                analyzed_contexts.add(context_hash)
                
                # Use LLM to analyze the context
                level, ai_analysis, confidence = await self._analyze_with_llm(
                    context,
                    framework,
                    rule["category"],
                    rule["requirement"],
                    rule["check_prompt"]
                )
                
                # Only create an issue if it's not compliant and confidence is reasonable
                if level != ComplianceLevel.COMPLIANT and confidence >= 0.5:
                    issues.append(ComplianceIssue(
                        framework=framework,
                        level=level,
                        category=rule["category"],
                        description=rule["requirement"],
                        context=context,
                        ai_analysis=ai_analysis,
                        location=f"Characters {match.start()}-{match.end()}",
                        recommendation=self._get_recommendation(framework, rule["category"], level),
                        reference=self._get_regulatory_reference(framework, rule["category"]),
                        confidence=confidence
                    ))
                elif level == ComplianceLevel.COMPLIANT and confidence >= 0.7:
                    # Track areas of compliance for positive feedback
                    logger.info(f"Compliant area found: {framework.value} - {rule['category']}")
        
        return issues
    
    def _get_recommendation(
        self, 
        framework: RegulatoryFramework, 
        category: str, 
        level: ComplianceLevel
    ) -> str:
        """Get specific recommendations based on framework, category, and severity."""
        recommendations = {
            RegulatoryFramework.HIPAA: {
                "PHI Protection": {
                    ComplianceLevel.CRITICAL: "IMMEDIATELY implement HIPAA Safe Harbor de-identification or obtain Expert Determination",
                    ComplianceLevel.VIOLATION: "Remove all 18 HIPAA identifiers or implement Expert Determination method",
                    ComplianceLevel.WARNING: "Review de-identification procedures and document compliance"
                },
                "Data Security": {
                    ComplianceLevel.CRITICAL: "IMMEDIATELY implement AES-256 encryption and TLS 1.2+ for all PHI",
                    ComplianceLevel.VIOLATION: "Implement encryption for data at rest and in transit per HIPAA Security Rule",
                    ComplianceLevel.WARNING: "Strengthen security measures and document encryption protocols"
                },
                "Audit Controls": {
                    ComplianceLevel.CRITICAL: "IMMEDIATELY implement comprehensive audit logging for all PHI access",
                    ComplianceLevel.VIOLATION: "Implement audit logs with user, timestamp, and action tracking",
                    ComplianceLevel.WARNING: "Enhance audit logging and ensure regular review procedures"
                }
            },
            RegulatoryFramework.CFR_PART_11: {
                "Electronic Records": {
                    ComplianceLevel.CRITICAL: "System validation required before ANY data collection",
                    ComplianceLevel.VIOLATION: "Complete IQ/OQ/PQ validation and implement audit trails",
                    ComplianceLevel.WARNING: "Document validation procedures and ensure compliance"
                },
                "Electronic Signatures": {
                    ComplianceLevel.CRITICAL: "Electronic signatures MUST include name, date/time, and meaning",
                    ComplianceLevel.VIOLATION: "Implement compliant e-signature with all required components",
                    ComplianceLevel.WARNING: "Review e-signature implementation for full compliance"
                }
            }
        }
        
        # Get specific recommendation or provide generic one
        framework_recs = recommendations.get(framework, {})
        category_recs = framework_recs.get(category, {})
        
        return category_recs.get(
            level,
            f"Address {category} requirements for {framework.value} compliance"
        )
    
    def _get_regulatory_reference(self, framework: RegulatoryFramework, category: str) -> str:
        """Get specific regulatory reference for the framework and category."""
        references = {
            RegulatoryFramework.HIPAA: {
                "PHI Protection": "45 CFR §164.514 (De-identification)",
                "Data Security": "45 CFR §164.312 (Technical safeguards)",
                "Audit Controls": "45 CFR §164.312(b) (Audit controls)",
                "Authorization": "45 CFR §164.508 (Authorization)",
                "Breach Response": "45 CFR §164.400-414 (Breach Notification)",
                "Minimum Necessary": "45 CFR §164.502(b), §164.514(d)"
            },
            RegulatoryFramework.CFR_PART_11: {
                "Electronic Records": "21 CFR §11.10",
                "Audit Trail": "21 CFR §11.10(e)",
                "Electronic Signatures": "21 CFR §11.50, §11.70",
                "System Validation": "21 CFR §11.10(a)",
                "Access Controls": "21 CFR §11.10(d)",
                "Data Integrity": "21 CFR §11.10(b), (c)"
            },
            RegulatoryFramework.IRB: {
                "Informed Consent": "45 CFR §46.116",
                "Risk Assessment": "45 CFR §46.111(a)(2)",
                "Vulnerable Populations": "45 CFR §46 Subparts B-D",
                "Protocol Review": "45 CFR §46.109",
                "Safety Monitoring": "21 CFR §56.111",
                "Confidentiality": "45 CFR §46.111(a)(7)"
            },
            RegulatoryFramework.ONC_HTI_1: {
                "Data Transparency": "85 FR 25642",
                "Interoperability": "45 CFR §170.215",
                "Patient Access": "45 CFR §170.315(g)(10)",
                "API Standards": "45 CFR §170.404",
                "Information Blocking": "45 CFR Part 171"
            }
        }
        
        return references.get(framework, {}).get(category, "See applicable regulations")
    
    def _calculate_risk_score(self, issues: List[ComplianceIssue]) -> int:
        """Calculate overall risk score based on issues found."""
        if not issues:
            return 0
        
        # Weight by severity and confidence
        weights = {
            ComplianceLevel.WARNING: 5,
            ComplianceLevel.VIOLATION: 15,
            ComplianceLevel.CRITICAL: 30
        }
        
        total_score = 0
        for issue in issues:
            base_weight = weights.get(issue.level, 0)
            # Adjust by confidence
            adjusted_weight = base_weight * issue.confidence
            total_score += adjusted_weight
        
        # Cap at 100
        return min(100, int(total_score))
    
    def _generate_ai_insights(self, issues: List[ComplianceIssue]) -> List[str]:
        """Generate AI-powered insights from the analysis."""
        insights = []
        
        # Group issues by framework
        framework_issues = {}
        for issue in issues:
            if issue.framework not in framework_issues:
                framework_issues[issue.framework] = []
            framework_issues[issue.framework].append(issue)
        
        # Generate insights
        for framework, framework_issues_list in framework_issues.items():
            if len(framework_issues_list) > 3:
                insights.append(
                    f"🔍 {framework.value}: Multiple issues detected ({len(framework_issues_list)}). "
                    "Consider comprehensive review with compliance team."
                )
        
        # Check for high-confidence critical issues
        critical_issues = [i for i in issues if i.level == ComplianceLevel.CRITICAL and i.confidence > 0.8]
        if critical_issues:
            insights.append(
                "⚠️ HIGH CONFIDENCE CRITICAL ISSUES: Immediate action required. "
                "These issues would likely fail regulatory audit."
            )
        
        # Check for patterns
        security_issues = [i for i in issues if 'security' in i.category.lower() or 'encrypt' in i.category.lower()]
        if len(security_issues) > 2:
            insights.append(
                "🔒 Security Pattern Detected: Multiple security-related issues. "
                "Recommend comprehensive security assessment."
            )
        
        consent_issues = [i for i in issues if 'consent' in i.category.lower() or 'authorization' in i.category.lower()]
        if len(consent_issues) > 1:
            insights.append(
                "📝 Consent/Authorization Gaps: Review participant consent and data use authorization procedures."
            )
        
        return insights
    
    def _generate_recommendations(self, issues: List[ComplianceIssue]) -> List[str]:
        """Generate prioritized recommendations based on issues."""
        recommendations = []
        
        # Group by severity
        critical_issues = [i for i in issues if i.level == ComplianceLevel.CRITICAL]
        violation_issues = [i for i in issues if i.level == ComplianceLevel.VIOLATION]
        warning_issues = [i for i in issues if i.level == ComplianceLevel.WARNING]
        
        if critical_issues:
            recommendations.append("🚨 IMMEDIATE ACTION REQUIRED:")
            # Sort by confidence, highest first
            critical_issues.sort(key=lambda x: x.confidence, reverse=True)
            for issue in critical_issues[:3]:
                recommendations.append(
                    f"  • [{issue.framework.value}] {issue.recommendation} "
                    f"(Confidence: {issue.confidence:.0%})"
                )
        
        if violation_issues:
            recommendations.append("\n⚠️ HIGH PRIORITY:")
            violation_issues.sort(key=lambda x: x.confidence, reverse=True)
            for issue in violation_issues[:5]:
                recommendations.append(
                    f"  • [{issue.framework.value}] {issue.recommendation}"
                )
        
        if warning_issues and len(recommendations) < 10:
            recommendations.append("\n📋 RECOMMENDATIONS:")
            for issue in warning_issues[:3]:
                recommendations.append(f"  • {issue.recommendation}")
        
        # Add general recommendations
        recommendations.extend([
            "\n📊 NEXT STEPS:",
            "  1. Review all high-confidence findings with compliance team",
            "  2. Prioritize critical and violation-level issues",
            "  3. Document remediation plans with timelines",
            "  4. Schedule follow-up compliance assessment",
            "  5. Consider external audit for validation"
        ])
        
        return recommendations
    
    def _format_compliance_report(self, report: ComplianceReport) -> str:
        """Format the compliance report as readable text."""
        output = []
        output.append("=" * 70)
        output.append("AI-ENHANCED REGULATORY COMPLIANCE VALIDATION REPORT")
        output.append("=" * 70)
        output.append(f"Generated: {report.timestamp}")
        output.append(f"Analysis Type: AI-Powered Pattern Recognition + Context Analysis")
        output.append(f"Risk Score: {report.risk_score}/100 {'🟢' if report.risk_score < 30 else '🟡' if report.risk_score < 60 else '🔴'}")
        output.append("")
        
        # Executive Summary
        output.append("EXECUTIVE SUMMARY")
        output.append("-" * 40)
        output.append(f"Total Issues Found: {len(report.issues)}")
        
        # Count by level
        level_counts = {}
        high_confidence_count = 0
        for issue in report.issues:
            level_counts[issue.level] = level_counts.get(issue.level, 0) + 1
            if issue.confidence >= 0.8:
                high_confidence_count += 1
        
        for level in [ComplianceLevel.CRITICAL, ComplianceLevel.VIOLATION, ComplianceLevel.WARNING]:
            count = level_counts.get(level, 0)
            if count > 0:
                emoji = "🔴" if level == ComplianceLevel.CRITICAL else "🟡" if level == ComplianceLevel.VIOLATION else "⚪"
                output.append(f"  {emoji} {level.value.upper()}: {count}")
        
        output.append(f"\nHigh Confidence Issues (≥80%): {high_confidence_count}")
        
        # AI Insights
        if report.ai_insights:
            output.append("\n" + "=" * 70)
            output.append("AI INSIGHTS")
            output.append("=" * 70)
            for insight in report.ai_insights:
                output.append(insight)
        
        # Detailed Findings
        if report.issues:
            output.append("\n" + "=" * 70)
            output.append("DETAILED FINDINGS (Sorted by Confidence)")
            output.append("=" * 70)
            
            # Sort issues by confidence
            sorted_issues = sorted(report.issues, key=lambda x: x.confidence, reverse=True)
            
            for issue in sorted_issues[:20]:  # Top 20 issues
                level_emoji = "🔴" if issue.level == ComplianceLevel.CRITICAL else "🟡" if issue.level == ComplianceLevel.VIOLATION else "⚪"
                output.append(f"\n{level_emoji} [{issue.framework.value}] {issue.category}")
                output.append(f"   Confidence: {issue.confidence:.0%}")
                output.append(f"   Context: \"{issue.context[:150]}...\"" if len(issue.context) > 150 else f"   Context: \"{issue.context}\"")
                output.append(f"   AI Analysis: {issue.ai_analysis}")
                if issue.recommendation:
                    output.append(f"   → Action: {issue.recommendation}")
                if issue.reference:
                    output.append(f"   📖 Reference: {issue.reference}")
        
        # Recommendations
        if report.recommendations:
            output.append("\n" + "=" * 70)
            output.append("PRIORITIZED RECOMMENDATIONS")
            output.append("=" * 70)
            output.extend(report.recommendations)
        
        # Footer
        output.append("\n" + "=" * 70)
        output.append("END OF REPORT")
        output.append("=" * 70)
        output.append("\nNOTE: This AI-enhanced analysis provides more accurate detection")
        output.append("by analyzing context rather than just pattern matching.")
        output.append("High-confidence findings (≥80%) should be prioritized for review.")
        output.append("\nDISCLAIMER: Always consult with qualified regulatory professionals.")
        
        return "\n".join(output)
    
    async def process_message(self, message: str) -> str:
        """
        Process incoming protocol/documentation for AI-enhanced compliance validation.
        
        Args:
            message: Protocol text, SOPs, or regulatory documentation
            
        Returns:
            Formatted compliance report with AI analysis and risk assessment
        """
        try:
            logger.info("Starting AI-enhanced regulatory compliance validation")
            
            # Initialize report
            report = ComplianceReport()
            all_issues = []
            
            # Check each regulatory framework
            for framework in RegulatoryFramework:
                logger.info(f"Checking compliance with {framework.value} using AI analysis")
                issues = await self._analyze_text_for_compliance(message, framework)
                all_issues.extend(issues)
                logger.info(f"Found {len(issues)} issues for {framework.value}")
            
            # Store issues in report
            report.issues = all_issues
            
            # Calculate risk score
            report.risk_score = self._calculate_risk_score(all_issues)
            
            # Generate AI insights
            report.ai_insights = self._generate_ai_insights(all_issues)
            
            # Generate recommendations
            report.recommendations = self._generate_recommendations(all_issues)
            
            # Identify compliant areas
            frameworks_with_issues = set(issue.framework for issue in all_issues)
            for framework in RegulatoryFramework:
                if framework not in frameworks_with_issues:
                    report.compliant_areas.append(f"{framework.value} - No significant issues detected")
            
            # Create summary
            report.summary = {
                "total_issues": len(all_issues),
                "critical": len([i for i in all_issues if i.level == ComplianceLevel.CRITICAL]),
                "violations": len([i for i in all_issues if i.level == ComplianceLevel.VIOLATION]),
                "warnings": len([i for i in all_issues if i.level == ComplianceLevel.WARNING]),
                "average_confidence": sum(i.confidence for i in all_issues) / len(all_issues) if all_issues else 0,
                "risk_score": report.risk_score,
                "frameworks_checked": [f.value for f in RegulatoryFramework]
            }
            
            # Format and return report
            formatted_report = self._format_compliance_report(report)
            
            logger.info(f"AI compliance validation complete. Risk score: {report.risk_score}")
            
            return formatted_report
            
        except Exception as e:
            logger.error(f"Error during AI compliance validation: {str(e)}")
            return (
                f"Error performing AI compliance validation: {str(e)}\n\n"
                "Please ensure:\n"
                "1. LLM API key is configured (OPENAI_API_KEY, GOOGLE_API_KEY, or ANTHROPIC_API_KEY)\n"
                "2. The input contains protocol or regulatory documentation text\n"
                "3. Network connection is available for AI analysis"
            )


if __name__ == "__main__":
    # Run the agent
    agent = RegulatoryComplianceAIAgent()
    agent.run(port=8000)