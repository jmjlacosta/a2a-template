"""
Unified extraction tools for comprehensive clinical data extraction.
GITHUB ISSUE FIX: Simplified signatures for Google ADK compatibility.
All List[Dict[str, Any]] converted to JSON strings.
"""
import json
from typing import Dict, List, Any, Optional
from google.adk.tools import FunctionTool


def extract_diagnoses(timeline_events_json: str) -> str:
    """
    Extract diagnosis information with special emphasis on cancer staging.
    
    FIXED: Accept JSON string instead of List[Dict[str, Any]].
    
    Args:
        timeline_events_json: JSON string of timeline events to extract from
        
    Returns:
        JSON string with diagnosis extraction request
    """
    # Parse JSON string
    try:
        timeline_events = json.loads(timeline_events_json)
        if not isinstance(timeline_events, list):
            timeline_events = []
    except (json.JSONDecodeError, TypeError):
        timeline_events = []
    
    if not timeline_events:
        return json.dumps({"action": "extract_diagnoses", "diagnoses": []})
    
    # Format events for processing
    formatted_events = []
    for event in timeline_events:
        event_str = f"Date: {event.get('date', '')}\nSummary: {event.get('summary', '')}\nSources: {', '.join(event.get('source_documents', []))} (Pages: {', '.join(str(p) for p in event.get('source_pages', []))})"
        formatted_events.append(event_str)
    
    events_text = "\n\n".join(formatted_events)
    
    request = {
        "action": "extract_diagnoses",
        "timeline_events_count": len(timeline_events),
        "events_text": events_text,
        "instructions": """Extract all DIAGNOSIS events with comprehensive cancer information:
        
        DIAGNOSIS CATEGORIES TO IDENTIFY:
        1. ANY pathology or biopsy result establishing or confirming diagnosis
        2. Initial cancer diagnosis with complete pathologic information
        3. ALL staging information (any staging system used) - initial and restaging
        4. Histologic classification and grade/differentiation from ANY source
        5. ALL molecular and biomarker results relevant to the cancer type
        6. Disease recurrence, progression, or new primary cancers
        7. Metastatic disease identification and sites
        8. ALL restaging events showing disease status changes
        9. ALL pathologic findings that establish or modify diagnosis
        10. Secondary malignancies or treatment-related cancers
        11. Imaging findings that contribute to staging or diagnosis
        12. ANY diagnostic confirmation or clarification
        
        CLINICAL INFORMATION TO CAPTURE:
        - ALL pathologic diagnoses with histologic type (from any biopsy)
        - ALL staging information (regardless of staging system) - initial and updates
        - ALL grade or differentiation level when available
        - ALL molecular markers, mutations, or biomarkers mentioned
        - Anatomical location and extent of disease
        - ALL lymph node involvement status
        - ALL metastatic sites if present
        - ANY prognostic or predictive factors
        - ALL imaging findings that establish or modify diagnosis
        - ALL confirmatory testing results
        
        RULES:
        - Include ALL events that provide diagnostic information
        - Extract EVERY pathology result, even repeat biopsies of same lesion
        - Include ALL staging information whenever mentioned  
        - Capture ALL diagnostic imaging findings that affect diagnosis or staging
        - Include molecular/biomarker information from ANY source
        - Extract ALL restaging or confirmatory diagnostic events
        - Include diagnostic information from consultation notes
        - Extract ALL grading information (histologic, nuclear, etc.)
        - Include ALL receptor status results from any test
        - Focus on COMPLETENESS - do not filter out diagnostic information
        - Include initial biopsies, repeat biopsies, confirmatory tests
        - Extract imaging findings that establish metastases or staging
        - Include ALL diagnostic details that would influence treatment decisions
        
        OUTPUT FORMAT (JSON):
        {
            "diagnoses": [
                {
                    "date": "MM/DD/YYYY",
                    "summary": "complete diagnostic information including how diagnosed, staging, and molecular features",
                    "type": "primary|staging|recurrence|progression|secondary|metastasis|restaging",
                    "staging_info": "specific staging details if available",
                    "molecular_info": "biomarkers or molecular characteristics if available",
                    "diagnostic_method": "how diagnosis was established (biopsy, imaging, pathology, etc.)",
                    "sources": "document name",
                    "pages": "page numbers"
                }
            ]
        }
        
        SUMMARY FORMAT REQUIREMENTS:
        Each diagnosis summary should include:
        1. The diagnosis itself (cancer type, histology, grade)
        2. How it was diagnosed (e.g., "confirmed by biopsy", "diagnosed via CT imaging", "established by pathology")
        3. Any staging information (e.g., "Stage IIIB", "T4N2M0")
        4. Molecular features if available (e.g., "ER/PR positive", "HER2 negative", "BRAF V600E mutation")"""
    }
    
    return json.dumps(request)


def extract_treatments(timeline_events_json: str) -> str:
    """
    Extract treatment information from timeline events.
    
    FIXED: Accept JSON string instead of List[Dict[str, Any]].
    
    Args:
        timeline_events_json: JSON string of timeline events to extract from
        
    Returns:
        JSON string with treatment extraction request
    """
    # Parse JSON string
    try:
        timeline_events = json.loads(timeline_events_json)
        if not isinstance(timeline_events, list):
            timeline_events = []
    except (json.JSONDecodeError, TypeError):
        timeline_events = []
    
    if not timeline_events:
        return json.dumps({"action": "extract_treatments", "treatments": []})
    
    # Format events for processing
    formatted_events = []
    for event in timeline_events:
        event_str = f"Date: {event.get('date', '')}\nSummary: {event.get('summary', '')}\nSources: {', '.join(event.get('source_documents', []))} (Pages: {', '.join(str(p) for p in event.get('source_pages', []))})"
        formatted_events.append(event_str)
    
    events_text = "\n\n".join(formatted_events)
    
    request = {
        "action": "extract_treatments",
        "timeline_events_count": len(timeline_events),
        "events_text": events_text,
        "instructions": """Extract all TREATMENT events:
        
        TREATMENT CATEGORIES TO IDENTIFY:
        1. ALL surgeries and surgical procedures (including biopsies)
        2. ALL chemotherapy (neoadjuvant, adjuvant, palliative)
        3. ALL radiation therapy (any type or site)
        4. ALL immunotherapy and targeted therapy
        5. ALL hormonal/endocrine therapy
        6. Clinical trial enrollments and experimental treatments
        7. ALL supportive care medications related to cancer care
        8. ALL procedures (diagnostic or therapeutic)
        9. Treatment planning discussions and decisions
        10. Treatment changes, modifications, or discontinuations
        
        OUTPUT FORMAT (JSON):
        {
            "treatments": [
                {
                    "date": "MM/DD/YYYY",
                    "summary": "treatment description with details",
                    "type": "surgery|chemotherapy|radiation|immunotherapy|targeted|hormonal|procedure|supportive|trial",
                    "intent": "curative|palliative|neoadjuvant|adjuvant if mentioned",
                    "details": "specific drugs, doses, locations, techniques if available",
                    "sources": "document name",
                    "pages": "page numbers"
                }
            ]
        }"""
    }
    
    return json.dumps(request)


def extract_complications(timeline_events_json: str) -> str:
    """
    Extract complications and adverse events from timeline events.
    
    FIXED: Accept JSON string instead of List[Dict[str, Any]].
    
    Args:
        timeline_events_json: JSON string of timeline events to extract from
        
    Returns:
        JSON string with complications extraction request
    """
    # Parse JSON string
    try:
        timeline_events = json.loads(timeline_events_json)
        if not isinstance(timeline_events, list):
            timeline_events = []
    except (json.JSONDecodeError, TypeError):
        timeline_events = []
    
    if not timeline_events:
        return json.dumps({"action": "extract_complications", "complications": []})
    
    # Format events for processing
    formatted_events = []
    for event in timeline_events:
        event_str = f"Date: {event.get('date', '')}\nSummary: {event.get('summary', '')}\nSources: {', '.join(event.get('source_documents', []))} (Pages: {', '.join(str(p) for p in event.get('source_pages', []))})"
        formatted_events.append(event_str)
    
    events_text = "\n\n".join(formatted_events)
    
    request = {
        "action": "extract_complications",
        "timeline_events_count": len(timeline_events),
        "events_text": events_text,
        "instructions": """Extract all COMPLICATIONS and adverse events:
        
        COMPLICATION CATEGORIES TO IDENTIFY:
        1. Treatment-related toxicities and side effects
        2. Surgical complications
        3. Chemotherapy adverse events
        4. Radiation toxicity
        5. Immunotherapy-related adverse events
        6. Disease-related complications
        7. Hospitalizations and emergency visits
        8. Infections
        9. Secondary conditions
        10. Dose modifications or treatment delays due to toxicity
        
        OUTPUT FORMAT (JSON):
        {
            "complications": [
                {
                    "date": "MM/DD/YYYY",
                    "summary": "complication description",
                    "type": "treatment-related|disease-related|surgical|medical",
                    "severity": "grade or severity if mentioned",
                    "management": "how it was managed if mentioned",
                    "sources": "document name",
                    "pages": "page numbers"
                }
            ]
        }"""
    }
    
    return json.dumps(request)


def extract_response_metrics(timeline_events_json: str) -> str:
    """
    Extract treatment response metrics and disease status from timeline events.
    
    FIXED: Accept JSON string instead of List[Dict[str, Any]].
    
    Args:
        timeline_events_json: JSON string of timeline events to extract from
        
    Returns:
        JSON string with response metrics extraction request
    """
    # Parse JSON string
    try:
        timeline_events = json.loads(timeline_events_json)
        if not isinstance(timeline_events, list):
            timeline_events = []
    except (json.JSONDecodeError, TypeError):
        timeline_events = []
    
    if not timeline_events:
        return json.dumps({"action": "extract_response_metrics", "response_metrics": []})
    
    # Format events for processing
    formatted_events = []
    for event in timeline_events:
        event_str = f"Date: {event.get('date', '')}\nSummary: {event.get('summary', '')}\nSources: {', '.join(event.get('source_documents', []))} (Pages: {', '.join(str(p) for p in event.get('source_pages', []))})"
        formatted_events.append(event_str)
    
    events_text = "\n\n".join(formatted_events)
    
    request = {
        "action": "extract_response_metrics",
        "timeline_events_count": len(timeline_events),
        "events_text": events_text,
        "instructions": """Extract all RESPONSE METRICS and disease status assessments:
        
        RESPONSE CATEGORIES TO IDENTIFY:
        1. RECIST response assessments (CR, PR, SD, PD)
        2. Pathologic response (pCR, major response, etc.)
        3. Imaging findings showing response
        4. Tumor marker changes
        5. Disease status updates
        6. Progression events
        7. Recurrence detection
        8. Remission status
        9. Follow-up findings
        10. Surveillance results
        
        OUTPUT FORMAT (JSON):
        {
            "response_metrics": [
                {
                    "date": "MM/DD/YYYY",
                    "summary": "response assessment description",
                    "type": "imaging|pathologic|clinical|biomarker",
                    "response": "CR|PR|SD|PD|NED|recurrence|progression if applicable",
                    "details": "specific measurements or findings if available",
                    "sources": "document name",
                    "pages": "page numbers"
                }
            ]
        }"""
    }
    
    return json.dumps(request)


def extract_demographics(timeline_events_json: str) -> str:
    """
    Extract patient demographic information from timeline events.
    
    FIXED: Accept JSON string instead of List[Dict[str, Any]].
    
    Args:
        timeline_events_json: JSON string of timeline events to extract from
        
    Returns:
        JSON string with demographics extraction request
    """
    # Parse JSON string
    try:
        timeline_events = json.loads(timeline_events_json)
        if not isinstance(timeline_events, list):
            timeline_events = []
    except (json.JSONDecodeError, TypeError):
        timeline_events = []
    
    # Format events for processing
    all_text = []
    source_docs = set()
    
    for event in timeline_events:
        all_text.append(event.get('summary', ''))
        source_docs.update(event.get('source_documents', []))
    
    combined_text = " ".join(all_text)
    
    request = {
        "action": "extract_demographics",
        "timeline_events_count": len(timeline_events),
        "combined_text": combined_text[:2000],  # Limit for context
        "source_documents": list(source_docs),
        "instructions": """Extract patient demographic information:
        
        INFORMATION TO EXTRACT:
        1. Patient age or date of birth
        2. Gender/Sex
        3. Race/Ethnicity if mentioned
        4. Relevant medical history
        5. Family history if mentioned
        6. Social history if relevant
        7. Performance status if mentioned
        
        OUTPUT FORMAT (JSON):
        {
            "demographics": {
                "age": "age or null",
                "gender": "gender or null",
                "date_of_birth": "DOB if available or null",
                "race_ethnicity": "if mentioned or null",
                "medical_history": "relevant past medical history",
                "family_history": "if mentioned or null",
                "social_history": "if relevant or null",
                "performance_status": "if mentioned or null",
                "sources": ["list of source documents"]
            }
        }"""
    }
    
    return json.dumps(request)


def generate_patient_headline(
    diagnoses_json: str,  # Changed from List[Dict[str, Any]]
    treatments_json: str,  # Changed from List[Dict[str, Any]]
    demographics_json: str,  # Changed from Optional[Dict[str, Any]]
    complications_json: str,  # Changed from Optional[List[Dict[str, Any]]]
    response_metrics_json: str  # Changed from Optional[List[Dict[str, Any]]]
) -> str:
    """
    Generate a patient headline based on extracted information.
    
    FIXED: Accept JSON strings instead of Python objects.
    
    Args:
        diagnoses_json: JSON string of diagnosis information
        treatments_json: JSON string of treatment information
        demographics_json: JSON string of demographic information (use "{}" for none)
        complications_json: JSON string of complications (use "[]" for none)
        response_metrics_json: JSON string of response metrics (use "[]" for none)
        
    Returns:
        JSON string with patient headline generation request
    """
    # Parse all JSON strings
    try:
        diagnoses = json.loads(diagnoses_json)
        if not isinstance(diagnoses, list):
            diagnoses = []
    except (json.JSONDecodeError, TypeError):
        diagnoses = []
    
    try:
        treatments = json.loads(treatments_json)
        if not isinstance(treatments, list):
            treatments = []
    except (json.JSONDecodeError, TypeError):
        treatments = []
    
    try:
        demographics = json.loads(demographics_json)
        if not isinstance(demographics, dict):
            demographics = {}
    except (json.JSONDecodeError, TypeError):
        demographics = {}
    
    try:
        complications = json.loads(complications_json)
        if not isinstance(complications, list):
            complications = []
    except (json.JSONDecodeError, TypeError):
        complications = []
    
    try:
        response_metrics = json.loads(response_metrics_json)
        if not isinstance(response_metrics, list):
            response_metrics = []
    except (json.JSONDecodeError, TypeError):
        response_metrics = []
    
    # Build key information summary
    key_info = []
    
    # Demographics
    if demographics:
        age = demographics.get('age')
        gender = demographics.get('gender')
        if age and gender:
            key_info.append(f"{age}-year-old {gender}")
        elif age:
            key_info.append(f"{age}-year-old patient")
        elif gender:
            key_info.append(f"{gender} patient")
    
    # Primary diagnosis
    if diagnoses:
        primary_dx = diagnoses[0]
        key_info.append(primary_dx.get('summary', 'cancer diagnosis'))
    
    # Key treatments
    treatment_types = set()
    for tx in treatments[:3]:  # First 3 treatments
        tx_type = tx.get('type', '')
        if tx_type:
            treatment_types.add(tx_type)
    
    if treatment_types:
        key_info.append(f"treated with {', '.join(list(treatment_types)[:2])}")
    
    # Current status
    if response_metrics:
        latest_response = response_metrics[-1]
        response_status = latest_response.get('response', '')
        if response_status:
            key_info.append(f"current status: {response_status}")
    
    # Major complications
    if complications:
        key_info.append(f"{len(complications)} complications noted")
    
    request = {
        "action": "generate_patient_headline",
        "key_information": key_info,
        "diagnosis_count": len(diagnoses),
        "treatment_count": len(treatments),
        "has_demographics": bool(demographics),
        "has_complications": bool(complications),
        "has_response_data": bool(response_metrics),
        "instructions": f"""Generate a concise patient headline (1-2 sentences) that captures:
        
        KEY INFORMATION:
        {' | '.join(key_info)}
        
        The headline should:
        1. Start with demographics if available (age, gender)
        2. Include primary diagnosis with key features
        3. Mention main treatment modalities
        4. Include current status if known
        5. Be medically accurate and professional
        
        Example format:
        "[Age]-year-old [gender] with [diagnosis including stage/key features] treated with [main treatments], [current status if known]."
        
        Keep it under 30 words if possible."""
    }
    
    return json.dumps(request)


def format_timeline_events(timeline_events_json: str) -> str:
    """
    Format timeline events for display.
    
    FIXED: Accept JSON string instead of List[Any].
    
    Args:
        timeline_events_json: JSON string of timeline events to format
        
    Returns:
        JSON string with formatted timeline
    """
    # Parse JSON string
    try:
        timeline_events = json.loads(timeline_events_json)
        if not isinstance(timeline_events, list):
            timeline_events = []
    except (json.JSONDecodeError, TypeError):
        timeline_events = []
    
    if not timeline_events:
        return json.dumps({"formatted_timeline": "No timeline events available"})
    
    formatted_sections = []
    
    # Group by date
    events_by_date = {}
    for event in timeline_events:
        date = event.get('date', 'Unknown Date')
        if date not in events_by_date:
            events_by_date[date] = []
        events_by_date[date].append(event)
    
    # Sort dates (handling "Unknown Date" specially)
    dates = sorted([d for d in events_by_date.keys() if d != 'Unknown Date'])
    if 'Unknown Date' in events_by_date:
        dates.append('Unknown Date')
    
    # Format each date's events
    for date in dates:
        date_events = events_by_date[date]
        
        if date == 'Unknown Date':
            formatted_sections.append("\n## Background Information (Date Unknown)")
        else:
            formatted_sections.append(f"\n## {date}")
        
        for event in date_events:
            summary = event.get('summary', '')
            sources = event.get('source_documents', [])
            pages = event.get('source_pages', [])
            verified = event.get('verified', False)
            
            # Format the event
            event_text = f"- {summary}"
            
            # Add source info
            if sources:
                source_str = f" (Source: {', '.join(sources)}"
                if pages:
                    source_str += f", Pages: {', '.join(str(p) for p in pages)}"
                source_str += ")"
                event_text += source_str
            
            # Add verification status
            if verified:
                event_text += " ✓"
            
            formatted_sections.append(event_text)
    
    formatted_timeline = "\n".join(formatted_sections)
    
    return json.dumps({
        "formatted_timeline": formatted_timeline,
        "total_events": len(timeline_events),
        "date_count": len(events_by_date)
    })


# Create FunctionTool instances for Google ADK
extract_diagnoses_tool = FunctionTool(func=extract_diagnoses)
extract_treatments_tool = FunctionTool(func=extract_treatments)
extract_complications_tool = FunctionTool(func=extract_complications)
extract_response_metrics_tool = FunctionTool(func=extract_response_metrics)
extract_demographics_tool = FunctionTool(func=extract_demographics)
generate_headline_tool = FunctionTool(func=generate_patient_headline)
format_timeline_tool = FunctionTool(func=format_timeline_events)

# Export all tools
UNIFIED_EXTRACTOR_TOOLS = [
    extract_diagnoses_tool,
    extract_treatments_tool,
    extract_complications_tool,
    extract_response_metrics_tool,
    extract_demographics_tool,
    generate_headline_tool,
    format_timeline_tool
]