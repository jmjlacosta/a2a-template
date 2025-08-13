"""
Regulatory compliance analysis tools for the LLM-based A2A agent.
These tools provide the agent with compliance checking capabilities for HIPAA, 21 CFR Part 11, etc.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ComplianceLevel(Enum):
    """Compliance severity levels"""
    CRITICAL = "CRITICAL"
    VIOLATION = "VIOLATION"
    WARNING = "WARNING"
    INFO = "INFO"
    COMPLIANT = "COMPLIANT"

class ComplianceFramework:
    """Base class for compliance frameworks"""
    
    def __init__(self, name: str, regulations: Dict[str, Dict[str, Any]]):
        self.name = name
        self.regulations = regulations
        self.issues = []
        
    def check_compliance(self, text: str) -> List[Dict[str, Any]]:
        """Check text for compliance issues"""
        self.issues = []
        
        for rule_name, rule_config in self.regulations.items():
            patterns = rule_config.get("patterns", [])
            level = rule_config.get("level", ComplianceLevel.WARNING)
            description = rule_config.get("description", "")
            reference = rule_config.get("reference", "")
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    context = self._extract_context(text, match.start(), match.end())
                    
                    # Skip if it's obviously medical context (not compliance-related)
                    if self._is_medical_context(context) and not self._has_compliance_keywords(context):
                        continue
                    
                    self.issues.append({
                        "framework": self.name,
                        "rule": rule_name,
                        "level": level.value if isinstance(level, ComplianceLevel) else level,
                        "description": description,
                        "reference": reference,
                        "context": context,
                        "confidence": 0.85  # Default confidence for pattern matching
                    })
        
        return self.issues
    
    def _extract_context(self, text: str, start: int, end: int, context_size: int = 250) -> str:
        """Extract context around a match"""
        context_start = max(0, start - context_size)
        context_end = min(len(text), end + context_size)
        return text[context_start:context_end].strip()
    
    def _is_medical_context(self, context: str) -> bool:
        """Check if context is purely medical (not compliance-related)"""
        medical_indicators = [
            'blood pressure', 'heart rate', 'temperature', 'vital signs',
            'clinical trial', 'patient care', 'medical record review',
            'dose', 'medication', 'treatment', 'therapy',
            'adverse event', 'diagnosis', 'symptom'
        ]
        
        context_lower = context.lower()
        for indicator in medical_indicators:
            if indicator in context_lower:
                return True
        return False
    
    def _has_compliance_keywords(self, context: str) -> bool:
        """Check if context has compliance-related keywords"""
        compliance_keywords = [
            'encrypt', 'password', 'authentication', 'audit', 'validation',
            'signature', 'access control', 'de-identification', 'PHI', 'PII',
            'retention', 'backup', 'disaster recovery', 'security'
        ]
        
        context_lower = context.lower()
        for keyword in compliance_keywords:
            if keyword in context_lower:
                return True
        return False

# Define HIPAA regulations
HIPAA_REGULATIONS = {
    "PHI De-identification": {
        "patterns": [
            r"(social.?security|SSN|social.?security.?number)",
            r"(patient.?names?|full.?names?|date.?of.?birth|DOB)(?=.*stored|.*collected|.*database)",
            r"de.?identification.?will.?occur.?after|identifiers?.?will.?be.?used.?for.?analysis"
        ],
        "level": ComplianceLevel.CRITICAL,
        "description": "PHI must be de-identified before use",
        "reference": "HIPAA Privacy Rule §164.514"
    },
    "Encryption Requirements": {
        "patterns": [
            r"(encryption.?is.?being.?evaluated|will.?use.?secure.?email|password.?protected.?attachments)",
            r"(no.?encryption|without.?encryption|plain.?text)(?=.*PHI|.*patient|.*medical)"
        ],
        "level": ComplianceLevel.VIOLATION,
        "description": "PHI must be encrypted at rest and in transit",
        "reference": "HIPAA Security Rule §164.312(a)(2)"
    },
    "Audit Controls": {
        "patterns": [
            r"audit.?logs?.?(?:are.?)?(?:only.?)?reviewed.?when.?issues",
            r"no.?audit.?trail|audit.?trail.?not.?(?:captured|maintained)"
        ],
        "level": ComplianceLevel.VIOLATION,
        "description": "Audit logs must be regularly reviewed",
        "reference": "HIPAA Security Rule §164.312(b)"
    }
}

# Define 21 CFR Part 11 regulations
CFR_PART_11_REGULATIONS = {
    "System Validation": {
        "patterns": [
            r"validation.?(?:has.?)?not.?been.?completed",
            r"retrospective.?validation",
            r"system.?(?:has.?been.?)?in.?use.?(?:for.?\d+.?years?.?)?but.?(?:formal.?)?validation"
        ],
        "level": ComplianceLevel.CRITICAL,
        "description": "Electronic systems must be validated",
        "reference": "21 CFR §11.10(a)"
    },
    "Audit Trail": {
        "patterns": [
            r"original.?values?.?(?:before.?changes?.?)?(?:are.?)?not.?captured",
            r"only.?(?:the.?)?new.?values?.?(?:are.?)?recorded",
            r"no.?audit.?trail|incomplete.?audit.?trail"
        ],
        "level": ComplianceLevel.CRITICAL,
        "description": "Complete audit trail required",
        "reference": "21 CFR §11.10(e)"
    },
    "Electronic Signatures": {
        "patterns": [
            r"does.?not.?(?:explicitly.?)?state.?(?:the.?)?meaning.?of.?(?:the.?)?signature",
            r"username.?and.?password(?!.*multi.?factor)",
            r"electronic.?signatures?.?(?:are.?)?not.?validated"
        ],
        "level": ComplianceLevel.VIOLATION,
        "description": "Electronic signatures must be validated",
        "reference": "21 CFR §11.50"
    }
}

# Define GCP regulations
GCP_REGULATIONS = {
    "Protocol Compliance": {
        "patterns": [
            r"(?:minor.?)?deviations?.?do.?not.?need.?to.?be.?reported.?immediately",
            r"deviations?.?(?:will.?be.?)?reported.?at.?(?:the.?)?next.?monitoring"
        ],
        "level": ComplianceLevel.VIOLATION,
        "description": "Protocol deviations must be documented immediately",
        "reference": "ICH E6 Section 4.5"
    },
    "Essential Documents": {
        "patterns": [
            r"retention.?period.?(?:has.?)?not.?been.?specified",
            r"document.?retention.?(?:period.?)?(?:not.?)?(?:specified|defined)"
        ],
        "level": ComplianceLevel.CRITICAL,
        "description": "Document retention period must be specified",
        "reference": "ICH E6 Section 8"
    }
}

# Create framework instances
hipaa_framework = ComplianceFramework("HIPAA", HIPAA_REGULATIONS)
cfr_framework = ComplianceFramework("21 CFR Part 11", CFR_PART_11_REGULATIONS)
gcp_framework = ComplianceFramework("Good Clinical Practice (ICH E6)", GCP_REGULATIONS)

async def analyze_compliance(
    document_text: str,
    frameworks: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Analyze document text for regulatory compliance issues.
    
    Args:
        document_text: The text to analyze for compliance
        frameworks: Optional list of frameworks to check (default: all)
        
    Returns:
        Dictionary containing compliance analysis results
    """
    logger.info(f"Analyzing document for compliance ({len(document_text)} characters)")
    
    if not frameworks:
        frameworks = ["HIPAA", "21 CFR Part 11", "Good Clinical Practice (ICH E6)"]
    
    all_issues = []
    framework_results = {}
    
    try:
        # Check each framework
        if "HIPAA" in frameworks:
            hipaa_issues = hipaa_framework.check_compliance(document_text)
            all_issues.extend(hipaa_issues)
            framework_results["HIPAA"] = len(hipaa_issues)
            
        if "21 CFR Part 11" in frameworks:
            cfr_issues = cfr_framework.check_compliance(document_text)
            all_issues.extend(cfr_issues)
            framework_results["21 CFR Part 11"] = len(cfr_issues)
            
        if "Good Clinical Practice (ICH E6)" in frameworks:
            gcp_issues = gcp_framework.check_compliance(document_text)
            all_issues.extend(gcp_issues)
            framework_results["Good Clinical Practice (ICH E6)"] = len(gcp_issues)
        
        # Calculate risk score
        risk_score = calculate_risk_score(all_issues)
        
        # Sort issues by severity
        all_issues.sort(key=lambda x: (
            0 if x["level"] == "CRITICAL" else
            1 if x["level"] == "VIOLATION" else
            2 if x["level"] == "WARNING" else 3
        ))
        
        return {
            "status": "success",
            "analysis_date": datetime.now().isoformat(),
            "risk_score": risk_score,
            "total_issues": len(all_issues),
            "issues_by_framework": framework_results,
            "issues": all_issues[:50],  # Limit to first 50 issues
            "summary": generate_summary(all_issues, risk_score)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing compliance: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to analyze compliance: {str(e)}"
        }

def calculate_risk_score(issues: List[Dict[str, Any]]) -> int:
    """Calculate overall risk score based on issues found"""
    if not issues:
        return 0
    
    score = 0
    for issue in issues:
        if issue["level"] == "CRITICAL":
            score += 25
        elif issue["level"] == "VIOLATION":
            score += 15
        elif issue["level"] == "WARNING":
            score += 5
    
    return min(100, score)

def generate_summary(issues: List[Dict[str, Any]], risk_score: int) -> Dict[str, Any]:
    """Generate executive summary of compliance findings"""
    critical_count = sum(1 for i in issues if i["level"] == "CRITICAL")
    violation_count = sum(1 for i in issues if i["level"] == "VIOLATION")
    warning_count = sum(1 for i in issues if i["level"] == "WARNING")
    
    if risk_score >= 75:
        risk_level = "HIGH"
        risk_color = "🔴"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
        risk_color = "🟡"
    else:
        risk_level = "LOW"
        risk_color = "🟢"
    
    return {
        "risk_level": risk_level,
        "risk_indicator": risk_color,
        "critical_issues": critical_count,
        "violations": violation_count,
        "warnings": warning_count,
        "key_findings": get_key_findings(issues),
        "recommendations": get_recommendations(issues)
    }

def get_key_findings(issues: List[Dict[str, Any]]) -> List[str]:
    """Extract key findings from issues"""
    findings = []
    seen = set()
    
    for issue in issues[:10]:  # Top 10 issues
        key = f"{issue['framework']}: {issue['rule']}"
        if key not in seen:
            findings.append(f"[{issue['level']}] {key} - {issue['description']}")
            seen.add(key)
    
    return findings

def get_recommendations(issues: List[Dict[str, Any]]) -> List[str]:
    """Generate recommendations based on issues found"""
    recommendations = []
    
    if any(i["rule"] == "PHI De-identification" for i in issues):
        recommendations.append("Implement immediate PHI de-identification procedures")
    
    if any(i["rule"] == "System Validation" for i in issues):
        recommendations.append("Complete formal system validation (IQ/OQ/PQ)")
    
    if any(i["rule"] == "Audit Trail" for i in issues):
        recommendations.append("Implement complete audit trail capturing all changes")
    
    if any(i["rule"] == "Encryption Requirements" for i in issues):
        recommendations.append("Deploy encryption for data at rest and in transit")
    
    if not recommendations:
        recommendations.append("Continue regular compliance monitoring")
    
    return recommendations

async def generate_compliance_report(
    document_text: str,
    output_format: Optional[str] = "text"
) -> str:
    """
    Generate a formatted compliance report.
    
    Args:
        document_text: The text to analyze
        output_format: Format for output ("text" or "json")
        
    Returns:
        Formatted compliance report as string
    """
    logger.info("Generating compliance report")
    
    try:
        # Analyze compliance
        results = await analyze_compliance(document_text)
        
        if output_format == "json":
            return json.dumps(results, indent=2)
        
        # Generate text report
        report = []
        report.append("=" * 70)
        report.append("AI-ENHANCED REGULATORY COMPLIANCE VALIDATION REPORT")
        report.append("=" * 70)
        report.append(f"Generated: {results['analysis_date']}")
        report.append(f"Risk Score: {results['risk_score']}/100 {results['summary']['risk_indicator']}")
        report.append("")
        report.append("EXECUTIVE SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Issues Found: {results['total_issues']}")
        
        summary = results['summary']
        if summary['critical_issues'] > 0:
            report.append(f"  🔴 CRITICAL: {summary['critical_issues']}")
        if summary['violations'] > 0:
            report.append(f"  🟡 VIOLATION: {summary['violations']}")
        if summary['warnings'] > 0:
            report.append(f"  🟠 WARNING: {summary['warnings']}")
        
        report.append("")
        report.append("KEY FINDINGS")
        report.append("-" * 40)
        for finding in summary['key_findings']:
            report.append(f"• {finding}")
        
        report.append("")
        report.append("DETAILED FINDINGS")
        report.append("-" * 40)
        
        for issue in results['issues'][:20]:  # Show first 20 issues
            level_icon = "🔴" if issue['level'] == "CRITICAL" else "🟡" if issue['level'] == "VIOLATION" else "🟠"
            report.append(f"\n{level_icon} [{issue['framework']}] {issue['rule']}")
            report.append(f"   Level: {issue['level']}")
            report.append(f"   Description: {issue['description']}")
            if issue['reference']:
                report.append(f"   Reference: {issue['reference']}")
            report.append(f"   Context: \"{issue['context'][:150]}...\"")
        
        report.append("")
        report.append("RECOMMENDATIONS")
        report.append("-" * 40)
        for rec in summary['recommendations']:
            report.append(f"• {rec}")
        
        report.append("")
        report.append("=" * 70)
        report.append("END OF REPORT")
        report.append("=" * 70)
        
        return "\n".join(report)
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return f"Error generating compliance report: {str(e)}"

async def check_specific_regulation(
    document_text: str,
    regulation: str,
    rule: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check compliance with a specific regulation or rule.
    
    Args:
        document_text: The text to analyze
        regulation: The regulation framework (e.g., "HIPAA")
        rule: Optional specific rule within the framework
        
    Returns:
        Dictionary with specific regulation check results
    """
    logger.info(f"Checking specific regulation: {regulation}")
    
    try:
        # Analyze for the specific framework
        results = await analyze_compliance(document_text, [regulation])
        
        # Filter for specific rule if provided
        if rule:
            filtered_issues = [i for i in results['issues'] if i['rule'] == rule]
            results['issues'] = filtered_issues
            results['total_issues'] = len(filtered_issues)
        
        return results
        
    except Exception as e:
        logger.error(f"Error checking regulation: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to check regulation: {str(e)}"
        }