#!/usr/bin/env python3
"""
Regulatory Compliance Validator Agent

This agent validates clinical trial protocols and documentation against:
- HIPAA Privacy and Security Rules
- 21 CFR Part 11 (Electronic Records/Signatures)
- IRB (Institutional Review Board) requirements
- ONC HTI-1 (Health Data, Technology, and Interoperability) transparency requirements

Input: Protocol documents, SOPs, regulatory requirements as text
Output: Compliance report with flagged risks and recommendations
"""

import sys
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent))

from base import BaseAgentExecutor

logger = logging.getLogger(__name__)


class ComplianceLevel(Enum):
    """Compliance severity levels."""
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"


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
    location: Optional[str] = None
    recommendation: Optional[str] = None
    reference: Optional[str] = None


@dataclass
class ComplianceReport:
    """Complete compliance validation report."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    summary: Dict[str, Any] = field(default_factory=dict)
    issues: List[ComplianceIssue] = field(default_factory=list)
    compliant_areas: List[str] = field(default_factory=list)
    risk_score: int = 0  # 0-100, higher = more risk
    recommendations: List[str] = field(default_factory=list)


class RegulatoryComplianceAgent(BaseAgentExecutor):
    """
    Agent that validates clinical trial documentation for regulatory compliance.
    """
    
    def __init__(self):
        super().__init__()
        self.compliance_rules = self._initialize_compliance_rules()
        
    def get_agent_name(self) -> str:
        return "Regulatory Compliance Validator"
    
    def get_agent_description(self) -> str:
        return (
            "Validates clinical trial protocols and documentation against "
            "HIPAA, 21 CFR Part 11, IRB requirements, and ONC HTI-1 transparency rules. "
            "Provides detailed compliance reports with risk assessments and recommendations."
        )
    
    def _initialize_compliance_rules(self) -> Dict[RegulatoryFramework, List[Dict[str, Any]]]:
        """Initialize comprehensive compliance rules for each framework."""
        return {
            RegulatoryFramework.HIPAA: [
                # Privacy Rules
                {
                    "category": "Privacy",
                    "pattern": r"patient\s+identif|PHI|protected\s+health|personal\s+information",
                    "check": "de-identification",
                    "description": "Check for proper PHI de-identification methods",
                    "recommendation": "Ensure all 18 HIPAA identifiers are removed or use Expert Determination method"
                },
                {
                    "category": "Privacy",
                    "pattern": r"consent|authorization|waiver",
                    "check": "authorization",
                    "description": "Verify patient authorization for PHI use",
                    "recommendation": "Include HIPAA-compliant authorization forms with required elements"
                },
                {
                    "category": "Privacy",
                    "pattern": r"minimum\s+necessary|data\s+minimization",
                    "check": "minimum_necessary",
                    "description": "Validate minimum necessary standard",
                    "recommendation": "Document why each data element is necessary for the research"
                },
                # Security Rules
                {
                    "category": "Security",
                    "pattern": r"encrypt|cryptograph|secure\s+transmission",
                    "check": "encryption",
                    "description": "Check for encryption requirements",
                    "recommendation": "Implement AES-256 encryption for data at rest and TLS 1.2+ for transmission"
                },
                {
                    "category": "Security",
                    "pattern": r"access\s+control|authentication|authorization",
                    "check": "access_control",
                    "description": "Verify access control measures",
                    "recommendation": "Implement role-based access control with unique user identification"
                },
                {
                    "category": "Security",
                    "pattern": r"audit\s+log|audit\s+trail|logging",
                    "check": "audit_logs",
                    "description": "Validate audit logging requirements",
                    "recommendation": "Log all PHI access with user, timestamp, and action performed"
                },
                {
                    "category": "Security",
                    "pattern": r"breach|incident\s+response|security\s+incident",
                    "check": "breach_notification",
                    "description": "Check breach notification procedures",
                    "recommendation": "Document breach notification process within 60 days requirement"
                }
            ],
            
            RegulatoryFramework.CFR_PART_11: [
                # Electronic Records
                {
                    "category": "Electronic Records",
                    "pattern": r"electronic\s+record|e-record|digital\s+document",
                    "check": "record_controls",
                    "description": "Validate electronic record controls",
                    "recommendation": "Implement validation, audit trails, and record retention procedures"
                },
                {
                    "category": "Electronic Records",
                    "pattern": r"audit\s+trail|system\s+log|change\s+history",
                    "check": "audit_trail",
                    "description": "Check computer-generated audit trails",
                    "recommendation": "Ensure audit trails are secure, time-stamped, and independently verifiable"
                },
                {
                    "category": "Electronic Records",
                    "pattern": r"backup|recovery|archive|retention",
                    "check": "record_retention",
                    "description": "Verify record retention and retrieval",
                    "recommendation": "Define retention periods and ensure accurate record reproduction"
                },
                # Electronic Signatures
                {
                    "category": "Electronic Signatures",
                    "pattern": r"electronic\s+signature|e-signature|digital\s+signature",
                    "check": "signature_components",
                    "description": "Validate electronic signature components",
                    "recommendation": "Include printed name, date/time, and meaning of signature"
                },
                {
                    "category": "Electronic Signatures",
                    "pattern": r"signature\s+manifest|signature\s+meaning",
                    "check": "signature_manifestation",
                    "description": "Check signature manifestation requirements",
                    "recommendation": "Display all signature information in human-readable format"
                },
                {
                    "category": "System Validation",
                    "pattern": r"validation|qualification|21\s+CFR|Part\s+11",
                    "check": "system_validation",
                    "description": "Verify system validation documentation",
                    "recommendation": "Document IQ/OQ/PQ validation with defined acceptance criteria"
                }
            ],
            
            RegulatoryFramework.IRB: [
                # Protocol Requirements
                {
                    "category": "Protocol",
                    "pattern": r"protocol|study\s+design|research\s+plan",
                    "check": "protocol_elements",
                    "description": "Check required protocol elements",
                    "recommendation": "Include objectives, methods, statistics, and organization per ICH-GCP"
                },
                {
                    "category": "Informed Consent",
                    "pattern": r"informed\s+consent|consent\s+form|participant\s+consent",
                    "check": "consent_elements",
                    "description": "Validate informed consent requirements",
                    "recommendation": "Include all 8 required elements and 6 additional elements when appropriate"
                },
                {
                    "category": "Risk Assessment",
                    "pattern": r"risk|benefit|adverse\s+event|safety",
                    "check": "risk_benefit",
                    "description": "Verify risk-benefit assessment",
                    "recommendation": "Clearly describe risks, benefits, and risk minimization strategies"
                },
                {
                    "category": "Vulnerable Populations",
                    "pattern": r"children|minor|pregnant|prisoner|vulnerable",
                    "check": "vulnerable_populations",
                    "description": "Check protections for vulnerable populations",
                    "recommendation": "Include additional safeguards per 45 CFR 46 Subparts B, C, and D"
                },
                {
                    "category": "Data Safety",
                    "pattern": r"DSMB|data\s+safety|monitoring\s+committee",
                    "check": "safety_monitoring",
                    "description": "Validate data safety monitoring plan",
                    "recommendation": "Establish independent DSMB for high-risk studies"
                }
            ],
            
            RegulatoryFramework.ONC_HTI_1: [
                # Transparency Requirements
                {
                    "category": "Transparency",
                    "pattern": r"data\s+sharing|transparency|open\s+access",
                    "check": "data_transparency",
                    "description": "Check data transparency requirements",
                    "recommendation": "Define data sharing timeline and repository per NIH requirements"
                },
                {
                    "category": "Interoperability",
                    "pattern": r"FHIR|HL7|interoperab|standard\s+format",
                    "check": "interoperability",
                    "description": "Validate interoperability standards",
                    "recommendation": "Use FHIR R4 for clinical data exchange and USCDI v3 data elements"
                },
                {
                    "category": "Patient Access",
                    "pattern": r"patient\s+access|participant\s+portal|data\s+request",
                    "check": "patient_access",
                    "description": "Verify patient data access provisions",
                    "recommendation": "Provide electronic access to data within 24 hours of request"
                },
                {
                    "category": "API Requirements",
                    "pattern": r"API|application\s+programming|SMART\s+on\s+FHIR",
                    "check": "api_standards",
                    "description": "Check API implementation requirements",
                    "recommendation": "Implement SMART on FHIR for third-party app access"
                },
                {
                    "category": "Information Blocking",
                    "pattern": r"information\s+blocking|data\s+withhold|access\s+restriction",
                    "check": "no_blocking",
                    "description": "Ensure no information blocking",
                    "recommendation": "Document any access restrictions under allowed exceptions only"
                }
            ]
        }
    
    def _analyze_text_for_compliance(self, text: str, framework: RegulatoryFramework) -> List[ComplianceIssue]:
        """Analyze text for compliance issues in a specific framework."""
        issues = []
        rules = self.compliance_rules[framework]
        
        # Convert text to lowercase for pattern matching
        text_lower = text.lower()
        
        for rule in rules:
            pattern = rule["pattern"]
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            
            for match in matches:
                # Extract context around the match
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                # Determine compliance level based on context
                level = self._assess_compliance_level(context, rule)
                
                if level != ComplianceLevel.COMPLIANT:
                    issues.append(ComplianceIssue(
                        framework=framework,
                        level=level,
                        category=rule["category"],
                        description=rule["description"],
                        location=f"Characters {match.start()}-{match.end()}",
                        recommendation=rule["recommendation"],
                        reference=self._get_regulatory_reference(framework, rule["category"])
                    ))
        
        return issues
    
    def _assess_compliance_level(self, context: str, rule: Dict[str, Any]) -> ComplianceLevel:
        """Assess the compliance level based on context."""
        context_lower = context.lower()
        
        # Check for positive compliance indicators
        positive_indicators = [
            "compliant", "accordance", "follows", "adheres", "implements",
            "documented", "established", "validated", "approved"
        ]
        
        # Check for negative indicators
        negative_indicators = [
            "not", "no", "missing", "lacks", "without", "absent",
            "undefined", "unclear", "insufficient", "inadequate"
        ]
        
        has_positive = any(indicator in context_lower for indicator in positive_indicators)
        has_negative = any(indicator in context_lower for indicator in negative_indicators)
        
        if has_negative and not has_positive:
            # Check for critical violations
            if any(critical in context_lower for critical in ["violation", "breach", "unauthorized"]):
                return ComplianceLevel.CRITICAL
            return ComplianceLevel.VIOLATION
        elif has_positive and not has_negative:
            return ComplianceLevel.COMPLIANT
        else:
            return ComplianceLevel.WARNING
    
    def _get_regulatory_reference(self, framework: RegulatoryFramework, category: str) -> str:
        """Get specific regulatory reference for the framework and category."""
        references = {
            RegulatoryFramework.HIPAA: {
                "Privacy": "45 CFR §164.514 (De-identification), §164.508 (Authorization)",
                "Security": "45 CFR §164.312 (Technical safeguards), §164.308 (Administrative safeguards)"
            },
            RegulatoryFramework.CFR_PART_11: {
                "Electronic Records": "21 CFR §11.10",
                "Electronic Signatures": "21 CFR §11.50, §11.70",
                "System Validation": "21 CFR §11.10(a)"
            },
            RegulatoryFramework.IRB: {
                "Protocol": "45 CFR §46.111",
                "Informed Consent": "45 CFR §46.116",
                "Risk Assessment": "45 CFR §46.111(a)(2)",
                "Vulnerable Populations": "45 CFR §46 Subparts B-D",
                "Data Safety": "21 CFR §56.111"
            },
            RegulatoryFramework.ONC_HTI_1: {
                "Transparency": "85 FR 25642",
                "Interoperability": "45 CFR §170.215",
                "Patient Access": "45 CFR §170.315(g)(10)",
                "API Requirements": "45 CFR §170.315(g)(10)",
                "Information Blocking": "45 CFR Part 171"
            }
        }
        
        return references.get(framework, {}).get(category, "See applicable regulations")
    
    def _calculate_risk_score(self, issues: List[ComplianceIssue]) -> int:
        """Calculate overall risk score based on issues found."""
        if not issues:
            return 0
        
        # Weight by severity
        weights = {
            ComplianceLevel.WARNING: 5,
            ComplianceLevel.VIOLATION: 15,
            ComplianceLevel.CRITICAL: 30
        }
        
        total_score = sum(weights.get(issue.level, 0) for issue in issues)
        
        # Cap at 100
        return min(100, total_score)
    
    def _generate_recommendations(self, issues: List[ComplianceIssue]) -> List[str]:
        """Generate prioritized recommendations based on issues."""
        recommendations = []
        
        # Group issues by framework and level
        critical_issues = [i for i in issues if i.level == ComplianceLevel.CRITICAL]
        violation_issues = [i for i in issues if i.level == ComplianceLevel.VIOLATION]
        
        if critical_issues:
            recommendations.append("🚨 IMMEDIATE ACTION REQUIRED:")
            for issue in critical_issues[:3]:  # Top 3 critical
                recommendations.append(f"  • {issue.recommendation}")
        
        if violation_issues:
            recommendations.append("\n⚠️ HIGH PRIORITY:")
            for issue in violation_issues[:5]:  # Top 5 violations
                recommendations.append(f"  • {issue.recommendation}")
        
        # Add general recommendations
        recommendations.extend([
            "\n📋 GENERAL RECOMMENDATIONS:",
            "  • Conduct comprehensive regulatory review with legal/compliance team",
            "  • Implement standard operating procedures (SOPs) for all identified gaps",
            "  • Schedule regular compliance audits and monitoring",
            "  • Provide training to all study personnel on regulatory requirements"
        ])
        
        return recommendations
    
    def _format_compliance_report(self, report: ComplianceReport) -> str:
        """Format the compliance report as readable text."""
        output = []
        output.append("=" * 70)
        output.append("REGULATORY COMPLIANCE VALIDATION REPORT")
        output.append("=" * 70)
        output.append(f"Generated: {report.timestamp}")
        output.append(f"Risk Score: {report.risk_score}/100 {'🟢' if report.risk_score < 30 else '🟡' if report.risk_score < 60 else '🔴'}")
        output.append("")
        
        # Summary
        output.append("EXECUTIVE SUMMARY")
        output.append("-" * 40)
        output.append(f"Total Issues Found: {len(report.issues)}")
        
        # Count by level
        level_counts = {}
        for issue in report.issues:
            level_counts[issue.level] = level_counts.get(issue.level, 0) + 1
        
        for level in [ComplianceLevel.CRITICAL, ComplianceLevel.VIOLATION, ComplianceLevel.WARNING]:
            count = level_counts.get(level, 0)
            if count > 0:
                emoji = "🔴" if level == ComplianceLevel.CRITICAL else "🟡" if level == ComplianceLevel.VIOLATION else "⚪"
                output.append(f"  {emoji} {level.value.upper()}: {count}")
        
        # Framework summary
        output.append("\nBY REGULATORY FRAMEWORK:")
        framework_counts = {}
        for issue in report.issues:
            framework_counts[issue.framework] = framework_counts.get(issue.framework, 0) + 1
        
        for framework in RegulatoryFramework:
            count = framework_counts.get(framework, 0)
            status = "✅" if count == 0 else "⚠️"
            output.append(f"  {status} {framework.value}: {count} issues")
        
        # Detailed issues
        if report.issues:
            output.append("\n" + "=" * 70)
            output.append("DETAILED FINDINGS")
            output.append("=" * 70)
            
            # Group by framework
            for framework in RegulatoryFramework:
                framework_issues = [i for i in report.issues if i.framework == framework]
                if framework_issues:
                    output.append(f"\n{framework.value}")
                    output.append("-" * len(framework.value))
                    
                    for issue in framework_issues:
                        level_emoji = "🔴" if issue.level == ComplianceLevel.CRITICAL else "🟡" if issue.level == ComplianceLevel.VIOLATION else "⚪"
                        output.append(f"\n{level_emoji} [{issue.category}] {issue.description}")
                        if issue.location:
                            output.append(f"   Location: {issue.location}")
                        if issue.recommendation:
                            output.append(f"   → Recommendation: {issue.recommendation}")
                        if issue.reference:
                            output.append(f"   📖 Reference: {issue.reference}")
        
        # Compliant areas
        if report.compliant_areas:
            output.append("\n" + "=" * 70)
            output.append("COMPLIANT AREAS")
            output.append("=" * 70)
            for area in report.compliant_areas:
                output.append(f"✅ {area}")
        
        # Recommendations
        if report.recommendations:
            output.append("\n" + "=" * 70)
            output.append("RECOMMENDATIONS")
            output.append("=" * 70)
            output.extend(report.recommendations)
        
        # Footer
        output.append("\n" + "=" * 70)
        output.append("END OF REPORT")
        output.append("=" * 70)
        output.append("\nDISCLAIMER: This automated compliance check is for guidance only.")
        output.append("Always consult with qualified regulatory and legal professionals.")
        
        return "\n".join(output)
    
    async def process_message(self, message: str) -> str:
        """
        Process incoming protocol/documentation for compliance validation.
        
        Args:
            message: Protocol text, SOPs, or regulatory documentation
            
        Returns:
            Formatted compliance report with risk assessment
        """
        try:
            logger.info("Starting regulatory compliance validation")
            
            # Initialize report
            report = ComplianceReport()
            all_issues = []
            
            # Check each regulatory framework
            for framework in RegulatoryFramework:
                logger.info(f"Checking compliance with {framework.value}")
                issues = self._analyze_text_for_compliance(message, framework)
                all_issues.extend(issues)
            
            # Store issues in report
            report.issues = all_issues
            
            # Calculate risk score
            report.risk_score = self._calculate_risk_score(all_issues)
            
            # Generate recommendations
            report.recommendations = self._generate_recommendations(all_issues)
            
            # Identify compliant areas (frameworks with no issues)
            for framework in RegulatoryFramework:
                framework_issues = [i for i in all_issues if i.framework == framework]
                if not framework_issues:
                    report.compliant_areas.append(f"{framework.value} - No issues detected")
            
            # Create summary
            report.summary = {
                "total_issues": len(all_issues),
                "critical": len([i for i in all_issues if i.level == ComplianceLevel.CRITICAL]),
                "violations": len([i for i in all_issues if i.level == ComplianceLevel.VIOLATION]),
                "warnings": len([i for i in all_issues if i.level == ComplianceLevel.WARNING]),
                "risk_score": report.risk_score,
                "frameworks_checked": [f.value for f in RegulatoryFramework]
            }
            
            # Format and return report
            formatted_report = self._format_compliance_report(report)
            
            logger.info(f"Compliance validation complete. Risk score: {report.risk_score}")
            
            return formatted_report
            
        except Exception as e:
            logger.error(f"Error during compliance validation: {str(e)}")
            return (
                f"Error performing compliance validation: {str(e)}\n\n"
                "Please ensure the input contains protocol or regulatory documentation text."
            )


if __name__ == "__main__":
    # Run the agent
    agent = RegulatoryComplianceAgent()
    agent.run(port=8000)