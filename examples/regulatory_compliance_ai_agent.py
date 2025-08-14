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
import asyncio
import uvicorn
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent))

from base import A2AAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

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
    GCP = "Good Clinical Practice (ICH E6)"
    FDA_IND = "FDA IND Requirements"
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


class RegulatoryComplianceAIAgent(A2AAgent):
    """
    AI-Enhanced agent that validates clinical trial documentation for regulatory compliance.
    Uses pattern detection followed by LLM analysis for accurate violation assessment.
    """
    
    def __init__(self):
        super().__init__()
        self.compliance_rules = self._initialize_compliance_rules()
        self._llm = None
        
        # Session management for LLM context
        self.session_id = "compliance_session"
        self.user_id = "compliance_user"
        
        # Rate limiting settings
        self.llm_call_delay = 0.5  # Delay between LLM calls in seconds
        self.max_concurrent_llm_calls = 3  # Maximum concurrent LLM calls
        self.llm_semaphore = asyncio.Semaphore(self.max_concurrent_llm_calls)
        
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
        """Return system instruction for compliance analysis."""
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
    
    def _initialize_compliance_rules(self) -> Dict[RegulatoryFramework, List[Dict[str, Any]]]:
        """Initialize comprehensive compliance rules for each framework."""
        return {
            RegulatoryFramework.HIPAA: [
                {
                    "category": "PHI De-identification",
                    "pattern": r"(patient|participant|subject)\s+(identif|name|SSN|social security|date of birth|DOB|address|phone|email|medical record|MRN|IP address|device identifier|biometric)",
                    "requirement": "HIPAA requires de-identification using Safe Harbor (removing 18 identifiers) or Expert Determination per 45 CFR 164.514(b)",
                    "check_prompt": "Does this text indicate proper de-identification of PHI? Look for: 1) Safe Harbor method removing all 18 identifiers, 2) Expert Determination with statistician certification, or 3) Improper handling of identifiers."
                },
                {
                    "category": "Business Associate Agreement",
                    "pattern": r"(business associate|BAA|third.?party|vendor|contractor|service provider|cloud|SaaS|data processor)",
                    "requirement": "HIPAA requires Business Associate Agreements (BAAs) with all third parties handling PHI per 45 CFR 164.504(e)",
                    "check_prompt": "Does this text properly address Business Associate Agreement requirements for third parties handling PHI?"
                },
                {
                    "category": "Research Authorization",
                    "pattern": r"(research authorization|waiver of authorization|IRB.?approved waiver|limited data set|data use agreement|DUA)",
                    "requirement": "Research use of PHI requires either: 1) Individual authorization per 45 CFR 164.508, 2) IRB-approved waiver per 164.512(i), or 3) Limited data set with DUA per 164.514(e)",
                    "check_prompt": "Does this text properly describe research authorization methods (individual authorization, IRB waiver, or limited data set with DUA)?"
                },
                {
                    "category": "Data Security",
                    "pattern": r"(encrypt(?:ion|ed|ing)|AES.?256|TLS.?1\.[2-3]|SSL|data.?at.?rest|data.?in.?transit|password.?(?:protect|encrypt|policy)|multi.?factor.?auth|role.?based.?access.?control|RBAC)",
                    "requirement": "HIPAA Security Rule requires encryption for PHI at rest (AES-256) and in transit (TLS 1.2+), plus access controls per 45 CFR 164.312",
                    "check_prompt": "Does this text demonstrate HIPAA-compliant encryption (AES-256 at rest, TLS 1.2+ in transit) and access controls?"
                },
                {
                    "category": "Audit Controls",
                    "pattern": r"(audit.?(?:trail|log|control)|access.?log(?:ging)?|activity.?(?:monitoring|logging)|security.?audit|log.?review.?(?:procedure|process)|unauthorized.?access.?detection|security.?incident.?(?:log|response))",
                    "requirement": "HIPAA requires audit logs per 45 CFR 164.312(b) tracking: user ID, date/time, action performed, patient ID affected",
                    "check_prompt": "Does this text show HIPAA-compliant audit logging with user ID, timestamp, action, and affected records?"
                },
                {
                    "category": "Breach Notification",
                    "pattern": r"(breach|data breach|unauthorized disclosure|breach notification|60.?day|500.?affected|HHS notification|media notification)",
                    "requirement": "HIPAA Breach Notification Rule requires: individual notice within 60 days, HHS notice within 60 days, media notice if >500 affected per 45 CFR 164.404-410",
                    "check_prompt": "Does this text properly address HIPAA breach notification timelines (60 days individual/HHS, immediate if >500)?"
                },
                {
                    "category": "Minimum Necessary",
                    "pattern": r"(minimum necessary|role.?based access|need.?to.?know|data minimization|limited data set|restrict)",
                    "requirement": "HIPAA Minimum Necessary standard per 45 CFR 164.502(b) requires limiting PHI access/use/disclosure to minimum needed",
                    "check_prompt": "Does this text demonstrate the Minimum Necessary principle with role-based access and data minimization?"
                },
                {
                    "category": "Training Requirements",
                    "pattern": r"(HIPAA training|privacy training|security training|workforce training|annual training|onboarding)",
                    "requirement": "HIPAA requires training all workforce members on privacy/security policies per 45 CFR 164.530(b)",
                    "check_prompt": "Does this text address HIPAA training requirements for all workforce members?"
                }
            ],
            
            RegulatoryFramework.CFR_PART_11: [
                {
                    "category": "System Validation",
                    "pattern": r"((?:computer.?)?system.?validation|CSV.?(?:protocol|documentation)|IQ[/\s]OQ[/\s]PQ|installation.?qualification|operational.?qualification|performance.?qualification|validation.?protocol|21.?CFR.?Part.?11)",
                    "requirement": "21 CFR Part 11.10(a) requires system validation including documented IQ (Installation Qualification), OQ (Operational Qualification), and PQ (Performance Qualification)",
                    "check_prompt": "Does this text show proper system validation with IQ/OQ/PQ documentation? Look for validation protocols, test scripts, and qualification reports."
                },
                {
                    "category": "Audit Trail",
                    "pattern": r"(audit.?trail|electronic.?audit|change.?history|version.?control.?system|modification.?tracking|who.?what.?when.?where|time.?stamp(?:ed|ing)|computer.?generated.?(?:audit|log)|secure.?(?:electronic.?)?record)",
                    "requirement": "21 CFR Part 11.10(e) requires secure, computer-generated, time-stamped audit trails that capture: user ID, date/time, old value, new value, reason for change. Must be retained for record lifetime + 2 years",
                    "check_prompt": "Does this text describe Part 11 compliant audit trails? Check for: computer-generated, time-stamped, user identification, change tracking, and proper retention."
                },
                {
                    "category": "Electronic Signatures",
                    "pattern": r"(electronic signature|e.?signature|digital signature|signature manifestation|signed electronically|signature meaning|non.?repudiation)",
                    "requirement": "21 CFR Part 11.50 requires e-signatures to include: printed name of signer, date/time of signature, meaning of signature (review, approval, responsibility)",
                    "check_prompt": "Does this text show compliant electronic signatures with name, date/time, and meaning? Check for signature manifestation requirements."
                },
                {
                    "category": "Access Controls",
                    "pattern": r"((?:system.?)?access.?control|user.?authentication|unique.?user.?(?:ID|identification)|password.?(?:policy|requirement|complexity)|biometric.?(?:authentication|access)|two.?factor.?auth|session.?(?:lock|timeout)|automatic.?logoff|authority.?check)",
                    "requirement": "21 CFR Part 11.10(d) requires limiting system access to authorized individuals with unique user ID/password combinations, automatic logoff, and authority checks",
                    "check_prompt": "Does this text demonstrate Part 11 access controls? Look for unique user IDs, authentication methods, and authority checks."
                },
                {
                    "category": "Data Integrity ALCOA+",
                    "pattern": r"(data.?integrity.?(?:principle|requirement|ALCOA)|ALCOA\+?|(?:data.?is.?)?attributable|(?:data.?is.?)?legible|(?:data.?is.?)?contemporaneous|(?:data.?is.?)?original|(?:data.?is.?)?accurate|(?:data.?is.?)?complete|(?:data.?is.?)?consistent|(?:data.?is.?)?enduring)",
                    "requirement": "21 CFR Part 11 requires data integrity following ALCOA+ principles: Attributable, Legible, Contemporaneous, Original, Accurate, Complete, Consistent, Enduring, Available",
                    "check_prompt": "Does this text address ALCOA+ data integrity principles? Check each principle is properly implemented."
                },
                {
                    "category": "Backup and Recovery",
                    "pattern": r"(backup|disaster recovery|business continuity|data recovery|archive|retention period|record retention|restore procedure)",
                    "requirement": "21 CFR Part 11.10(c) requires protection of records with backup and accurate/ready retrieval throughout retention period",
                    "check_prompt": "Does this text describe adequate backup, recovery, and retention procedures for electronic records?"
                },
                {
                    "category": "Training Records",
                    "pattern": r"(training record|user training|system training|Part 11 training|qualification|competency|training documentation)",
                    "requirement": "21 CFR Part 11.10(i) requires documented training of personnel using the system including developers, users, and IT support",
                    "check_prompt": "Does this text show proper training documentation for all system users as required by Part 11?"
                },
                {
                    "category": "Change Control",
                    "pattern": r"(change control|change management|version control|configuration management|change request|impact assessment|regression testing)",
                    "requirement": "21 CFR Part 11.10(k) requires formal change control procedures with documentation of changes, testing, and approval",
                    "check_prompt": "Does this text describe Part 11 compliant change control procedures with proper documentation and testing?"
                }
            ],
            
            RegulatoryFramework.IRB: [
                {
                    "category": "Informed Consent Elements",
                    "pattern": r"(informed consent|consent form|voluntary participation|withdrawal|consent process|consent documentation|eConsent|electronic consent)",
                    "requirement": "45 CFR 46.116 requires 8 basic elements: (1) research statement, (2) risks, (3) benefits, (4) alternatives, (5) confidentiality, (6) compensation/injury treatment, (7) contacts, (8) voluntary participation/withdrawal rights",
                    "check_prompt": "Does this text properly address all 8 required informed consent elements including voluntary participation and withdrawal rights?"
                },
                {
                    "category": "Risk-Benefit Assessment",
                    "pattern": r"(risk.?benefit|risk assessment|minimal risk|greater than minimal|adverse event|serious adverse event|SAE|risk mitigation|safety assessment)",
                    "requirement": "45 CFR 46.111(a)(2) requires risks be minimized and reasonable in relation to anticipated benefits. Greater-than-minimal-risk studies need enhanced monitoring",
                    "check_prompt": "Does this text show proper risk categorization (minimal vs greater-than-minimal) and benefit justification?"
                },
                {
                    "category": "Vulnerable Populations Protections",
                    "pattern": r"(children|pediatric|minor|pregnant women|fetus|prisoner|incarcerated|cognitive impairment|diminished capacity|economically disadvantaged|educationally disadvantaged|vulnerable)",
                    "requirement": "45 CFR 46 Subparts B (pregnant women/fetuses), C (prisoners), D (children) require additional safeguards, assent procedures, and special consent considerations",
                    "check_prompt": "Does this text demonstrate appropriate additional protections for vulnerable populations per Subparts B, C, or D?"
                },
                {
                    "category": "IRB Review Types",
                    "pattern": r"(IRB review|full board|expedited review|exempt|continuing review|annual review|protocol amendment|modification|deviation|violation)",
                    "requirement": "45 CFR 46.109 specifies review types: Exempt (46.104), Expedited (46.110), or Full Board. Continuing review required annually unless exempt",
                    "check_prompt": "Does this text correctly identify the IRB review type and continuing review requirements?"
                },
                {
                    "category": "Data Safety Monitoring",
                    "pattern": r"(DSMB|DSMC|Data Safety Monitoring|safety monitoring plan|stopping rules|interim analysis|futility|efficacy boundary|safety boundary|unblinding)",
                    "requirement": "FDA and NIH require DSMBs for Phase III trials and high-risk studies. Must define stopping rules for safety, efficacy, and futility with unblinding procedures",
                    "check_prompt": "Does this text describe adequate DSMB charter, stopping rules, and unblinding procedures for safety monitoring?"
                },
                {
                    "category": "Confidentiality and Privacy",
                    "pattern": r"(confidentiality|privacy protection|de.?identification|coded data|anonymous|Certificate of Confidentiality|CoC|data breach|re.?identification risk)",
                    "requirement": "45 CFR 46.111(a)(7) requires adequate privacy/confidentiality provisions. NIH-funded studies may require Certificate of Confidentiality per 21st Century Cures Act",
                    "check_prompt": "Does this text show proper confidentiality measures including de-identification methods and Certificate of Confidentiality if applicable?"
                },
                {
                    "category": "Adverse Event Reporting",
                    "pattern": r"(adverse event|AE|serious adverse event|SAE|unanticipated problem|reportable event|FDA reporting|sponsor notification|IRB reporting)",
                    "requirement": "45 CFR 46.103(b)(5) requires prompt reporting of unanticipated problems. SAEs require reporting within 24-72 hours to IRB, FDA (if IND), and sponsor",
                    "check_prompt": "Does this text specify proper AE/SAE reporting timelines to IRB (immediate for deaths, 24-72h for SAEs)?"
                },
                {
                    "category": "Protocol Compliance",
                    "pattern": r"(protocol deviation|protocol violation|non.?compliance|corrective action|preventive action|CAPA|root cause analysis)",
                    "requirement": "IRB requires reporting of major deviations within 10 days, minor deviations at continuing review. Repeated deviations require CAPA plan",
                    "check_prompt": "Does this text properly distinguish major vs minor deviations and describe corrective action plans?"
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
            ],
            
            RegulatoryFramework.GCP: [
                {
                    "category": "Protocol Compliance",
                    "pattern": r"(protocol adherence|protocol compliance|GCP compliance|ICH.?E6|good clinical practice|protocol training|investigator responsibilities)",
                    "requirement": "ICH E6 Section 4.5 requires investigators to comply with the protocol, only make changes to eliminate immediate hazards, and document/report all deviations",
                    "check_prompt": "Does this text demonstrate GCP protocol compliance including deviation documentation and investigator responsibilities?"
                },
                {
                    "category": "Source Documentation",
                    "pattern": r"(source document|source data|primary record|medical record|case report form|CRF|eCRF|source data verification|SDV)",
                    "requirement": "ICH E6 Section 4.9.0 requires source documents be accurate, complete, and verifiable. All CRF entries must be traceable to source",
                    "check_prompt": "Does this text show proper source documentation practices with traceability between source docs and CRFs?"
                },
                {
                    "category": "Essential Documents",
                    "pattern": r"(essential document|regulatory binder|trial master file|TMF|investigator site file|ISF|document retention|archival)",
                    "requirement": "ICH E6 Section 8 lists essential documents for TMF/ISF. Must be retained for 2 years after marketing approval or trial discontinuation",
                    "check_prompt": "Does this text properly address essential document management and retention requirements per ICH E6 Section 8?"
                },
                {
                    "category": "Investigational Product Management",
                    "pattern": r"(investigational product|study drug|drug accountability|dispensing log|temperature log|chain of custody|storage condition|expiry|randomization)",
                    "requirement": "ICH E6 Section 4.6 requires documented receipt, storage, dispensing, return, and destruction of investigational products with temperature monitoring",
                    "check_prompt": "Does this text show proper investigational product accountability including storage conditions and chain of custody?"
                },
                {
                    "category": "Clinical Trial Monitoring",
                    "pattern": r"(monitoring visit|site visit|monitoring plan|monitoring report|100% SDV|risk.?based monitoring|RBM|central monitoring|on.?site monitoring)",
                    "requirement": "ICH E6 Section 5.18 requires monitoring per written plan. FDA supports risk-based monitoring per 2013 guidance. Must verify source data, protocol compliance, and GCP adherence",
                    "check_prompt": "Does this text describe adequate monitoring procedures including frequency, scope, and risk-based approach?"
                },
                {
                    "category": "Sponsor Responsibilities",
                    "pattern": r"(sponsor responsibility|sponsor oversight|clinical trial agreement|CTA|delegation log|supervision|medical monitor|safety reporting to sites)",
                    "requirement": "ICH E6 Section 5 defines sponsor responsibilities including trial oversight, safety reporting to sites within 24h for SUSARs, and maintaining quality management system",
                    "check_prompt": "Does this text properly address sponsor oversight responsibilities including safety reporting and quality management?"
                },
                {
                    "category": "Investigator Qualifications",
                    "pattern": r"(investigator qualification|CV|curriculum vitae|medical license|GCP training|financial disclosure|FDA 1572|delegation of authority)",
                    "requirement": "ICH E6 Section 4.1 requires investigators be qualified by education, training, and experience. Must maintain current CV, licenses, GCP training certificates, and FDA 1572",
                    "check_prompt": "Does this text demonstrate proper investigator qualifications including CV, training, and regulatory documents?"
                },
                {
                    "category": "Quality Management System",
                    "pattern": r"(quality management|QMS|quality assurance|quality control|audit trail|CAPA|corrective action|preventive action|risk assessment|critical process)",
                    "requirement": "ICH E6(R2) Section 5.0 requires sponsors implement quality management system with risk-based approach focusing on critical processes and data",
                    "check_prompt": "Does this text show implementation of quality management system with risk-based approach per ICH E6(R2)?"
                }
            ],
            
            RegulatoryFramework.FDA_IND: [
                {
                    "category": "IND Submission Requirements",
                    "pattern": r"(IND application|investigational new drug|Form FDA 1571|IND submission|pre.?IND meeting|Type [A-D] meeting|initial IND|IND amendment)",
                    "requirement": "21 CFR 312.23 requires IND contain: FDA 1571, protocol, investigator's brochure, chemistry/manufacturing info, pharmacology/toxicology data, and prior human experience",
                    "check_prompt": "Does this text properly address IND submission requirements including all required components per 21 CFR 312.23?"
                },
                {
                    "category": "IND Safety Reporting",
                    "pattern": r"(IND safety report|7.?day report|15.?day report|SUSAR|suspected unexpected serious adverse reaction|expedited report|annual report|DSUR)",
                    "requirement": "21 CFR 312.32 requires: 7-day reports for fatal/life-threatening SUSARs, 15-day reports for other serious unexpected AEs, annual reports with safety summary",
                    "check_prompt": "Does this text correctly specify IND safety reporting timelines (7-day, 15-day, annual) per 21 CFR 312.32?"
                },
                {
                    "category": "Protocol Amendments",
                    "pattern": r"(protocol amendment|substantial amendment|IND amendment|protocol change|new investigator|new site|protocol modification|30.?day safety)",
                    "requirement": "21 CFR 312.30 requires protocol amendments be submitted before implementation except for immediate safety changes. New protocols have 30-day FDA review period",
                    "check_prompt": "Does this text properly describe protocol amendment procedures including 30-day review period for new protocols?"
                },
                {
                    "category": "Clinical Hold",
                    "pattern": r"(clinical hold|partial hold|full hold|FDA hold|study suspension|enrollment suspension|hold letter|hold response|hold removal)",
                    "requirement": "21 CFR 312.42 allows FDA to impose clinical hold for safety or compliance issues. Sponsor must respond within 30 days with corrective action plan",
                    "check_prompt": "Does this text address clinical hold procedures including 30-day response requirement and corrective actions?"
                },
                {
                    "category": "Investigator Responsibilities",
                    "pattern": r"(FDA Form 1572|investigator statement|investigator agreement|investigator commitment|site qualification|investigator IND|investigator.?initiated)",
                    "requirement": "21 CFR 312.60 requires investigators sign FDA 1572 committing to: conduct per protocol, personally supervise, ensure informed consent, report AEs, maintain records",
                    "check_prompt": "Does this text show proper investigator commitments per FDA 1572 including supervision and reporting requirements?"
                },
                {
                    "category": "Record Retention",
                    "pattern": r"(record retention|document retention|2.?year|retention period|FDA inspection|record availability|archived records)",
                    "requirement": "21 CFR 312.57 requires retention of records for 2 years after marketing application approval or 2 years after discontinuation and FDA notification",
                    "check_prompt": "Does this text specify proper IND record retention periods (2 years) per 21 CFR 312.57?"
                },
                {
                    "category": "Drug Manufacturing",
                    "pattern": r"(drug manufacturing|GMP|CMC|chemistry manufacturing controls|stability|impurities|specifications|batch record|Certificate of Analysis|CoA)",
                    "requirement": "21 CFR 312.23(a)(7) requires CMC information including manufacturing, stability data, and controls. Must follow GMP per 21 CFR 210/211 for Phase 3",
                    "check_prompt": "Does this text address drug manufacturing requirements including GMP compliance and CMC documentation?"
                },
                {
                    "category": "FDA Inspections",
                    "pattern": r"(FDA inspection|BIMO|bioresearch monitoring|Form FDA 483|inspection readiness|FDA audit|regulatory inspection|establishment inspection report|EIR)",
                    "requirement": "21 CFR 312.58 requires immediate access to records during FDA inspection. Form 483 observations require written response within 15 business days",
                    "check_prompt": "Does this text demonstrate FDA inspection readiness including immediate record access and 483 response procedures?"
                }
            ]
        }
    
    def _is_medical_context(self, context: str) -> bool:
        """Check if the context is clearly medical/clinical rather than IT/compliance."""
        medical_indicators = [
            'blood pressure', 'heart rate', 'temperature', 'vital signs',
            'clinical trial', 'patient care', 'medical record review',
            'dose', 'medication', 'treatment', 'therapy',
            'adverse event', 'diagnosis', 'symptom',
            'quality control assurance', 'clinical monitoring',
            'participant', 'enrollment', 'randomized'
        ]
        
        context_lower = context.lower()
        
        # Check for medical context indicators
        for indicator in medical_indicators:
            if indicator in context_lower:
                # But still process if it mentions specific compliance terms
                compliance_terms = ['encrypt', 'audit trail', 'electronic signature', 
                                  '21 cfr', 'hipaa', 'validation protocol']
                if any(term in context_lower for term in compliance_terms):
                    return False  # It's compliance-related despite medical context
                return True  # It's medical context
        
        return False  # Not obviously medical
    
    def _extract_context(self, text: str, match_start: int, match_end: int, context_chars: int = 500) -> str:
        """Extract meaningful context around a pattern match - full paragraphs when possible."""
        # Try to find paragraph boundaries first
        paragraphs = text.split('\n\n')
        
        # Find which paragraph(s) contain the match
        current_pos = 0
        relevant_content = []
        
        for para in paragraphs:
            para_end = current_pos + len(para) + 2  # +2 for the \n\n
            
            # Check if this paragraph contains or overlaps with the match
            if (current_pos <= match_start <= para_end) or \
               (current_pos <= match_end <= para_end) or \
               (match_start <= current_pos and para_end <= match_end):
                # Include the whole paragraph
                relevant_content.append(para.strip())
            
            current_pos = para_end
        
        # If we found relevant paragraphs, use them
        if relevant_content:
            context = ' '.join(relevant_content)
        else:
            # Fallback to sentence extraction
            sentences = re.split(r'[.!?]\s+', text)
            current_pos = 0
            relevant_sentences = []
            
            for i, sentence in enumerate(sentences):
                sentence_end = current_pos + len(sentence) + 1
                
                # Check if this sentence overlaps with the match
                if (current_pos <= match_start <= sentence_end) or \
                   (current_pos <= match_end <= sentence_end) or \
                   (match_start <= current_pos and sentence_end <= match_end):
                    # Add previous sentence for context if available
                    if i > 0 and sentences[i-1] not in relevant_sentences:
                        relevant_sentences.append(sentences[i-1].strip())
                    # Add current sentence
                    relevant_sentences.append(sentence.strip())
                    # Add next sentence for context if available
                    if i < len(sentences) - 1:
                        relevant_sentences.append(sentences[i+1].strip())
                
                current_pos = sentence_end
            
            if relevant_sentences:
                context = '. '.join(relevant_sentences)
            else:
                # Final fallback to character-based extraction with larger window
                start = max(0, match_start - context_chars)
                end = min(len(text), match_end + context_chars)
                context = text[start:end].strip()
        
        # Look for section headers before the match
        header_pattern = r'^(?:\d+\.?\d*\s+)?[A-Z][A-Za-z\s]+:?\s*$'
        lines_before = text[:match_start].split('\n')[-5:]  # Check last 5 lines before match
        for line in lines_before:
            if re.match(header_pattern, line.strip()) and len(line.strip()) < 100:
                context = f"[Section: {line.strip()}] {context}"
                break
        
        # Clean up the context
        context = ' '.join(context.split())  # Normalize whitespace
        
        # Ensure we don't exceed reasonable length
        if len(context) > 1500:
            # Truncate but keep the matched portion in the middle
            context = context[:750] + " [...] " + context[-750:]
        
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
        # Add small delay to prevent overwhelming the API
        await asyncio.sleep(0.1)
        
        prompt = f"""You are a regulatory compliance expert analyzing clinical trial documentation for regulatory adherence.

TASK: Analyze the provided text excerpt for compliance with {framework.value} requirements.

REGULATORY CONTEXT:
- Framework: {framework.value}
- Category: {category}
- Specific Requirement: {requirement}

TEXT UNDER REVIEW:
"{context}"

ANALYSIS QUESTION:
{check_prompt}

EVALUATION CRITERIA:
1. COMPLIANT - Text demonstrates full compliance with requirements
2. WARNING - Minor issues or unclear compliance status
3. VIOLATION - Clear non-compliance that needs correction
4. CRITICAL - Severe violation requiring immediate action

IMPORTANT CONSIDERATIONS:
- Distinguish between mentioning a concept vs. implementing it
- Look for specific safeguards, procedures, or controls described
- Consider if this would satisfy an FDA/regulatory audit
- Assess completeness of the implementation described

EXAMPLES OF ANALYSIS:

Example 1 - COMPLIANT:
Text: "All patient data is encrypted using AES-256 at rest and TLS 1.3 in transit. Access logs are automatically generated capturing user ID, timestamp, action performed, and patient records accessed."
Analysis: Specific encryption standards meet HIPAA requirements, audit logging captures all required elements.

Example 2 - VIOLATION:
Text: "We plan to implement encryption for sensitive data in the next phase."
Analysis: Current state lacks required encryption, future plans don't satisfy current compliance needs.

Example 3 - WARNING:
Text: "Data security measures are in place following industry standards."
Analysis: Vague statement without specific details about encryption methods or standards used.

RESPOND WITH THIS EXACT JSON STRUCTURE:
{{
    "level": "COMPLIANT" or "WARNING" or "VIOLATION" or "CRITICAL",
    "explanation": "Clear, specific explanation referencing the requirement and what was found or missing",
    "confidence": 0.0 to 1.0 (use 0.9+ only when very clear, 0.7-0.8 for typical cases, 0.5-0.6 when uncertain),
    "specific_concern": "The exact compliance gap if any, or null if compliant",
    "passes_audit": true or false
}}

Provide ONLY the JSON response, no additional text."""
        
        try:
            # Get or initialize LLM
            if self._llm is None:
                self._llm = self.get_llm_client()
                
                if self._llm is None:
                    return ComplianceLevel.WARNING, "LLM not available - pattern-based analysis only", 0.5
            
            # Generate response from LLM
            response_text = self._llm.generate_text(prompt)
            
            if not response_text:
                logger.warning("LLM returned empty response")
                return ComplianceLevel.WARNING, "LLM returned empty response - skipping", 0.2
            
            # Parse the JSON response with improved debugging
            logger.debug(f"LLM response length: {len(response_text)} chars")
            logger.debug(f"Framework: {framework.value}, Category: {category}")
            
            if not response_text:
                logger.error("LLM returned empty response")
                logger.debug(f"Prompt was: {prompt[:500]}...")
                logger.debug(f"Context being analyzed: {context[:200]}...")
                # Return low confidence so it gets filtered out
                return ComplianceLevel.WARNING, "LLM returned empty response - skipping", 0.2
            
            # Log first 500 chars for debugging
            logger.debug(f"LLM raw response: {response_text[:500]}{'...' if len(response_text) > 500 else ''}")
            
            # Try to extract JSON from the response
            # First try to find a complete JSON object
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            
            if not json_match:
                # Try more aggressive JSON extraction
                logger.warning("No JSON object found with initial regex, trying broader search")
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group()
                logger.debug(f"Extracted JSON string: {json_str[:300]}{'...' if len(json_str) > 300 else ''}")
                
                try:
                    result = json.loads(json_str)
                    logger.info(f"Successfully parsed LLM response - Level: {result.get('level', 'N/A')}, Confidence: {result.get('confidence', 'N/A')}")
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    logger.error(f"Failed to parse: {json_str[:500]}")
                    logger.debug(f"JSON error position: {e.pos if hasattr(e, 'pos') else 'unknown'}")
                    
                    # Try to clean common issues
                    cleaned = json_str.replace('\n', ' ').replace('  ', ' ')
                    try:
                        result = json.loads(cleaned)
                        logger.info("Successfully parsed after cleaning whitespace")
                    except:
                        return ComplianceLevel.WARNING, f"JSON parsing failed: {str(e)}", 0.5
            else:
                # Log the full response for debugging when JSON extraction fails
                logger.error(f"No JSON found in LLM response")
                logger.error(f"Full response (first 1000 chars): {response_text[:1000]}")
                logger.debug(f"Prompt that generated this response: {prompt[:500]}...")
                return ComplianceLevel.WARNING, "Unable to extract structured response - manual review recommended", 0.5
            
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
        logger.info(f"Starting compliance analysis for {framework.value}")
        logger.debug(f"Text length: {len(text)} characters")
        
        issues = []
        rules = self.compliance_rules[framework]
        logger.info(f"Checking {len(rules)} rules for {framework.value}")
        
        # Track what we've already analyzed to avoid duplicates
        analyzed_contexts = set()
        
        for rule in rules:
            pattern = rule["pattern"]
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            if matches:
                logger.debug(f"Found {len(matches)} matches for {rule['category']} pattern")
            
            for match in matches:
                # Extract context
                context = self._extract_context(text, match.start(), match.end())
                
                # Skip if we've already analyzed this context
                context_hash = hash(context)
                if context_hash in analyzed_contexts:
                    continue
                analyzed_contexts.add(context_hash)
                
                # Skip obvious medical contexts that aren't compliance-related
                if self._is_medical_context(context):
                    logger.debug(f"Skipping medical context for {rule['category']}: {context[:100]}...")
                    continue
                
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


# Module-level app creation for HealthUniverse deployment
agent = RegulatoryComplianceAIAgent()
agent_card = agent.create_agent_card()
task_store = InMemoryTaskStore()
request_handler = DefaultRequestHandler(
    agent_executor=agent,
    task_store=task_store
)

# Create the app - for HealthUniverse deployment
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler
).build()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting {agent.get_agent_name()}")
    print(f"📍 Server: http://localhost:{port}")
    print(f"📋 Agent Card: http://localhost:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host="0.0.0.0", port=port)