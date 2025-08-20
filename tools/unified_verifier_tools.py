"""
Unified verification tools with FIXED signatures for Google ADK compatibility.
GITHUB ISSUE: Google ADK Tool Signature Fix

Problem: Google ADK cannot parse Dict[str, Any], List[Dict[str, Any]], etc.
Solution: Use JSON strings for all complex data structures

Changes from unified_verifier_tools.py:
1. All Dict/List parameters changed to str (JSON)
2. Optional parameters made required or converted to str
3. Added JSON parsing with error handling
4. Preserved all original logic
"""
import json
from datetime import datetime, timedelta
from google.adk.tools import FunctionTool


def ensure_json_string(data):
    """
    Helper function to ensure data is a JSON string.
    
    Handles various input types:
    - If already a string, try to validate it's valid JSON
    - If a dict/list, convert to JSON string
    - If None or empty, return empty JSON object/array
    """
    if data is None:
        return "{}"
    
    if isinstance(data, str):
        # Validate it's valid JSON
        try:
            json.loads(data)
            return data
        except json.JSONDecodeError:
            # Not valid JSON, wrap as string
            return json.dumps(data)
    
    # Convert Python objects to JSON
    try:
        return json.dumps(data)
    except (TypeError, ValueError):
        return "{}"


def verify_diagnoses(
    diagnosis_data_json: str,  # Changed from Dict[str, Any]
    timeline_events_json: str  # Changed from List[Dict[str, Any]]
) -> str:
    """
    Verify diagnoses with special attention to cancer staging.
    
    FIXED: Accept JSON strings instead of Python dict/list.
    
    Args:
        diagnosis_data_json: JSON string of diagnosis data to verify
        timeline_events_json: JSON string of timeline events
        
    Returns:
        JSON string with verification request
    """
    # Ensure inputs are valid JSON strings
    diagnosis_data_json = ensure_json_string(diagnosis_data_json)
    timeline_events_json = ensure_json_string(timeline_events_json)
    
    # Parse JSON inputs
    try:
        diagnosis_data = json.loads(diagnosis_data_json)
    except (json.JSONDecodeError, TypeError):
        diagnosis_data = {}
    
    try:
        timeline_events = json.loads(timeline_events_json)
        if not isinstance(timeline_events, list):
            timeline_events = [timeline_events] if timeline_events else []
    except (json.JSONDecodeError, TypeError):
        timeline_events = []
    
    # Original logic from here...
    # Create timeline lookup
    timeline_lookup = create_timeline_lookup_internal(timeline_events)
    
    # Prepare verification requests
    verification_requests = []
    for diagnosis in diagnosis_data.get("diagnoses", []):
        date_str = diagnosis.get("date", "")
        matching_events = find_matching_events_internal(date_str, timeline_lookup, search_nearby=False)
        
        if matching_events:
            combined_source, actual_sources, actual_pages = get_source_info_internal(matching_events)
            
            # Check if this appears to be a cancer diagnosis
            cancer_keywords = ["cancer", "carcinoma", "adenocarcinoma", "squamous cell", "lymphoma",
                              "leukemia", "melanoma", "sarcoma", "tumor", "neoplasm", "malignancy"]
            summary_lower = diagnosis.get("summary", "").lower()
            is_cancer = any(keyword in summary_lower or keyword in combined_source.lower()
                           for keyword in cancer_keywords)
            
            verification_requests.append({
                "diagnosis": diagnosis,
                "source_text": combined_source,
                "actual_sources": list(actual_sources),
                "actual_pages": list(actual_pages),
                "is_cancer": is_cancer,
                "has_matching_events": True
            })
        else:
            verification_requests.append({
                "diagnosis": diagnosis,
                "source_text": "",
                "actual_sources": [],
                "actual_pages": [],
                "is_cancer": False,
                "has_matching_events": False
            })
    
    request = {
        "action": "verify_diagnoses",
        "total_diagnoses": len(diagnosis_data.get("diagnoses", [])),
        "verification_requests": verification_requests,
        "instructions": """Verify each diagnosis extraction against the source timeline events.
        
        For each diagnosis:
        1. Is the diagnosis accurately extracted from the timeline events?
        2. Is the summary factually correct based on the source?
        3. Are the source documents and pages correct?
        4. FOR CANCER DIAGNOSES: Is staging information included if available?
           - Look for: Stage I-IV, TNM classification (e.g., T2N1M0), descriptors like "locally advanced"
           - If staging is mentioned in source but missing from extraction, ADD IT
        5. Is the diagnosis type correctly categorized?
        
        CRITICAL: If this is a cancer diagnosis and staging information exists in the source,
        it MUST be included in the verified diagnosis.
        
        Return verified diagnoses with corrections where needed."""
    }
    
    return json.dumps(request)


def verify_treatments(
    treatment_data_json: str,  # Changed from Dict[str, Any]
    timeline_events_json: str  # Changed from List[Dict[str, Any]]
) -> str:
    """
    Verify treatments against source timeline events.
    
    FIXED: Accept JSON strings instead of Python dict/list.
    
    Args:
        treatment_data_json: JSON string of treatment data to verify
        timeline_events_json: JSON string of timeline events
        
    Returns:
        JSON string with verification request
    """
    # Parse JSON inputs
    try:
        treatment_data = json.loads(treatment_data_json)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for treatment_data"})
    
    try:
        timeline_events = json.loads(timeline_events_json)
        if not isinstance(timeline_events, list):
            timeline_events = [timeline_events]
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for timeline_events"})
    
    # Original logic from here...
    # Create timeline lookup
    timeline_lookup = create_timeline_lookup_internal(timeline_events)
    
    # Prepare verification requests
    verification_requests = []
    for treatment in treatment_data.get("treatments", []):
        date_str = treatment.get("date", "")
        # Handle date ranges
        lookup_date = date_str.split(" - ")[0] if " - " in date_str else date_str
        
        matching_events = find_matching_events_internal(lookup_date, timeline_lookup, search_nearby=False)
        
        if matching_events:
            combined_source, actual_sources, actual_pages = get_source_info_internal(matching_events)
            verification_requests.append({
                "treatment": treatment,
                "source_text": combined_source,
                "actual_sources": list(actual_sources),
                "actual_pages": list(actual_pages),
                "has_matching_events": True
            })
        else:
            verification_requests.append({
                "treatment": treatment,
                "source_text": "",
                "actual_sources": [],
                "actual_pages": [],
                "has_matching_events": False
            })
    
    request = {
        "action": "verify_treatments",
        "total_treatments": len(treatment_data.get("treatments", [])),
        "verification_requests": verification_requests,
        "instructions": """Verify each treatment extraction against the source timeline events.
        
        For each treatment:
        1. Is the treatment accurately extracted from the timeline events?
        2. Is the summary factually correct with all important details?
        3. Are the source documents and pages correct?
        4. For treatments: Is the date range accurate if provided?
        5. Is the category correctly assigned?
        6. Are specific regimens/protocols correctly identified?
        7. Are cycle numbers accurate for chemotherapy?
        
        IMPORTANT DETAILS TO VERIFY:
        - Drug names and combinations (e.g., FOLFOX, carboplatin/paclitaxel)
        - Dosing if mentioned
        - Duration of treatment
        - Number of cycles for chemotherapy
        - Surgical procedure names
        - Radiation dose and fractions
        
        Return verified treatments with corrections where needed."""
    }
    
    return json.dumps(request)


def verify_complications(
    complications_data_json: str,  # Changed from Dict[str, Any]
    timeline_events_json: str  # Changed from List[Dict[str, Any]]
) -> str:
    """
    Verify complications against source timeline events.
    
    FIXED: Accept JSON strings instead of Python dict/list.
    
    Args:
        complications_data_json: JSON string of complications data to verify
        timeline_events_json: JSON string of timeline events
        
    Returns:
        JSON string with verification request
    """
    # Parse JSON inputs
    try:
        complications_data = json.loads(complications_data_json)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for complications_data"})
    
    try:
        timeline_events = json.loads(timeline_events_json)
        if not isinstance(timeline_events, list):
            timeline_events = [timeline_events]
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for timeline_events"})
    
    # Original logic from here...
    # Create timeline lookup
    timeline_lookup = create_timeline_lookup_internal(timeline_events)
    
    # Prepare verification requests
    verification_requests = []
    for complication in complications_data.get("complications", []):
        date_str = complication.get("date", "")
        matching_events = find_matching_events_internal(date_str, timeline_lookup, search_nearby=True)
        
        if matching_events:
            combined_source, actual_sources, actual_pages = get_source_info_internal(matching_events)
            verification_requests.append({
                "complication": complication,
                "source_text": combined_source,
                "actual_sources": list(actual_sources),
                "actual_pages": list(actual_pages),
                "has_matching_events": True
            })
        else:
            verification_requests.append({
                "complication": complication,
                "source_text": "",
                "actual_sources": [],
                "actual_pages": [],
                "has_matching_events": False
            })
    
    request = {
        "action": "verify_complications",
        "total_complications": len(complications_data.get("complications", [])),
        "verification_requests": verification_requests,
        "instructions": """Verify each complication extraction against the source timeline events.
        
        For each complication:
        1. Is this truly a complication (adverse effect or unexpected issue from disease/treatment)?
        2. Is the summary factually correct based on the source?
        3. Are the source documents and pages correct?
        4. Is the date accurate?
        5. Does it include severity/grade information if available in the source?
        
        WHAT QUALIFIES AS A COMPLICATION:
        - Treatment side effects, toxicities, or adverse reactions
        - Infections or secondary conditions
        - Hospitalizations due to adverse events
        - Disease-related complications
        - Any unexpected negative outcome
        
        Return verified complications, filtering out any non-complications."""
    }
    
    return json.dumps(request)


def verify_response_metrics(
    response_metrics_data_json: str,  # Changed from Dict[str, Any]
    timeline_events_json: str  # Changed from List[Dict[str, Any]]
) -> str:
    """
    Verify response metrics against source timeline events.
    
    FIXED: Accept JSON strings instead of Python dict/list.
    
    Args:
        response_metrics_data_json: JSON string of response metrics to verify
        timeline_events_json: JSON string of timeline events
        
    Returns:
        JSON string with verification request
    """
    # Parse JSON inputs
    try:
        response_metrics_data = json.loads(response_metrics_data_json)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for response_metrics_data"})
    
    try:
        timeline_events = json.loads(timeline_events_json)
        if not isinstance(timeline_events, list):
            timeline_events = [timeline_events]
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for timeline_events"})
    
    # Original logic from here...
    # Create timeline lookup
    timeline_lookup = create_timeline_lookup_internal(timeline_events)
    
    # Prepare verification requests
    verification_requests = []
    for metric in response_metrics_data.get("response_metrics", []):
        date_str = metric.get("date", "")
        matching_events = find_matching_events_internal(date_str, timeline_lookup, search_nearby=True)
        
        if matching_events:
            combined_source, actual_sources, actual_pages = get_source_info_internal(matching_events)
            verification_requests.append({
                "metric": metric,
                "source_text": combined_source,
                "actual_sources": list(actual_sources),
                "actual_pages": list(actual_pages),
                "has_matching_events": True
            })
        else:
            verification_requests.append({
                "metric": metric,
                "source_text": "",
                "actual_sources": [],
                "actual_pages": [],
                "has_matching_events": False
            })
    
    request = {
        "action": "verify_response_metrics",
        "total_metrics": len(response_metrics_data.get("response_metrics", [])),
        "verification_requests": verification_requests,
        "instructions": """Verify each response metric extraction against the source timeline events.
        
        For each metric:
        1. Is this truly a response metric (measurement of treatment response)?
        2. Does it include specific criteria (RECIST, pathologic, percentage change)?
        3. Are the measurements/values accurate based on the source?
        4. Are the source documents and pages correct?
        5. Is the date accurate?
        
        WHAT QUALIFIES AS A RESPONSE METRIC:
        - RECIST criteria assessments (CR, PR, SD, PD)
        - Tumor size percentage changes
        - Pathologic response assessments (pCR, etc.)
        - Biomarker level changes indicating response
        - Specific response evaluations after treatment
        
        Return verified response metrics, filtering out baseline measurements."""
    }
    
    return json.dumps(request)


def verify_demographics(
    demographics_data_json: str,  # Changed from Dict[str, Any]
    timeline_events_json: str  # Changed from List[Dict[str, Any]]
) -> str:
    """
    Verify demographics against source timeline events.
    
    FIXED: Accept JSON strings instead of Python dict/list.
    
    Args:
        demographics_data_json: JSON string of demographics to verify
        timeline_events_json: JSON string of timeline events
        
    Returns:
        JSON string with verification request
    """
    # Parse JSON inputs
    try:
        demographics_data = json.loads(demographics_data_json)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for demographics_data"})
    
    try:
        timeline_events = json.loads(timeline_events_json)
        if not isinstance(timeline_events, list):
            timeline_events = [timeline_events]
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for timeline_events"})
    
    # Original logic from here...
    # Combine all timeline text for verification
    all_timeline_text = []
    for event in timeline_events:
        all_timeline_text.append(f"Date: {event.get('date', '')}\nSummary: {event.get('summary', '')}")
    
    combined_text = "\n\n".join(all_timeline_text)
    
    # Extract data to verify
    age = demographics_data.get("age")
    gender = demographics_data.get("gender")
    dob = demographics_data.get("date_of_birth")
    sources = demographics_data.get("sources", {})
    
    request = {
        "action": "verify_demographics",
        "demographics": {
            "age": age,
            "gender": gender,
            "date_of_birth": dob
        },
        "sources": sources,
        "combined_timeline_text": combined_text[:3000],  # Limit for context
        "instructions": """Verify the extracted demographic information against the source medical records.
        
        For each demographic item:
        1. Is the information accurately extracted from the source?
        2. Is the value correctly interpreted and formatted?
        3. Are there any errors or inconsistencies?
        4. If missing, can it be found in the source text?
        
        VERIFICATION RULES:
        - Only accept demographics explicitly stated in the records
        - For age: prefer explicit age statements over calculated ages
        - For gender: use terms as stated in medical records
        - For DOB: ensure proper MM/DD/YYYY format
        - Flag any inconsistencies or unclear references
        
        If any demographic was not initially found, search for it in the source text.
        
        Return verified demographics with corrections or additions where needed."""
    }
    
    return json.dumps(request)


def verify_patient_headline(
    headline: str,
    timeline_events_json: str,  # Changed from List[Dict[str, Any]]
    verified_diagnoses_json: str,  # Changed from List[Dict[str, Any]]
    demographics_data_json: str  # Changed from Optional[Dict[str, Any]] with default
) -> str:
    """
    Verify patient headline against source records and verified demographics.
    
    FIXED: Accept JSON strings instead of Python dict/list, removed optional with default.
    
    Args:
        headline: Generated headline to verify
        timeline_events_json: JSON string of timeline events
        verified_diagnoses_json: JSON string of verified diagnoses
        demographics_data_json: JSON string of demographics or "null"
        
    Returns:
        JSON string with verification request
    """
    # Parse JSON inputs
    try:
        timeline_events = json.loads(timeline_events_json)
        if not isinstance(timeline_events, list):
            timeline_events = [timeline_events]
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for timeline_events"})
    
    try:
        verified_diagnoses = json.loads(verified_diagnoses_json)
        if not isinstance(verified_diagnoses, list):
            verified_diagnoses = [verified_diagnoses]
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for verified_diagnoses"})
    
    # Handle demographics which can be null
    demographics_data = None
    if demographics_data_json and demographics_data_json.lower() != "null":
        try:
            demographics_data = json.loads(demographics_data_json)
        except (json.JSONDecodeError, TypeError):
            demographics_data = None
    
    # Original logic from here...
    # Gather timeline summaries
    all_summaries = []
    for event in timeline_events[:20]:
        all_summaries.append(f"{event.get('date', '')}: {event.get('summary', '')}")
    
    timeline_text = "\n".join(all_summaries)
    
    # Include verified diagnoses
    diagnosis_text = "\n".join([
        f"{d.get('date', '')}: {d.get('summary', '')}"
        for d in verified_diagnoses[:5]
    ])
    
    # Add demographics information if available
    demographics_text = ""
    if demographics_data:
        age = demographics_data.get("age")
        gender = demographics_data.get("gender")
        dob = demographics_data.get("date_of_birth")
        
        demographics_text = "\nVERIFIED DEMOGRAPHICS:\n"
        if age:
            demographics_text += f"Age: {age}\n"
        if gender:
            demographics_text += f"Gender: {gender}\n"
        if dob:
            demographics_text += f"DOB: {dob}\n"
    
    request = {
        "action": "verify_patient_headline",
        "headline": headline,
        "timeline_text": timeline_text,
        "diagnosis_text": diagnosis_text,
        "demographics_text": demographics_text,
        "has_demographics": demographics_data is not None,
        "instructions": """Verify this patient headline for accuracy against the source medical records and verified demographics.
        
        VERIFICATION RULES:
        1. Age and gender can come from verified demographics data (preferred) OR timeline events
        2. If demographics data provides age/gender, those should be considered verified
        3. Primary condition must match the verified diagnoses
        4. No information should be inferred beyond verified demographics and timeline events
        5. Maximum 2 lines
        6. Demographic accuracy should prioritize verified demographics data
        
        DEMOGRAPHIC VERIFICATION:
        - If demographics data shows age/gender, headline should use those values
        - Only flag demographic errors if they contradict verified demographics
        - Accept demographics from verified extraction even if not visible in timeline snippets
        
        COMMON ERRORS TO CHECK:
        - Incorrect primary diagnosis
        - Missing verified demographics when available
        - Added information not in records or verified data
        - Inconsistency with verified demographics
        
        If the headline contains any unverified information or misses verified demographics, provide a corrected version."""
    }
    
    return json.dumps(request)


def create_timeline_lookup(timeline_events_json: str) -> str:  # Changed from List[Dict[str, Any]]
    """
    Create a lookup dictionary of timeline events by date.
    
    FIXED: Accept JSON string instead of Python list.
    
    Args:
        timeline_events_json: JSON string of timeline events
        
    Returns:
        JSON string with timeline lookup
    """
    # Parse JSON input
    try:
        timeline_events = json.loads(timeline_events_json)
        if not isinstance(timeline_events, list):
            timeline_events = [timeline_events]
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for timeline_events"})
    
    # Original logic from here...
    timeline_lookup = {}
    for event in timeline_events:
        date = event.get("date", "")
        if date not in timeline_lookup:
            timeline_lookup[date] = []
        timeline_lookup[date].append(event)
    
    return json.dumps({
        "timeline_lookup": timeline_lookup,
        "total_dates": len(timeline_lookup),
        "total_events": len(timeline_events)
    })


def find_matching_events(
    date_str: str,
    timeline_lookup_json: str,  # Changed from Dict[str, List[Dict[str, Any]]]
    search_nearby: str  # Changed from bool with default to str
) -> str:
    """
    Find timeline events matching a date, optionally searching nearby dates.
    
    FIXED: Accept JSON string for lookup, bool as string.
    
    Args:
        date_str: Date to search for
        timeline_lookup_json: JSON string of timeline lookup dictionary
        search_nearby: String "true" or "false" for searching nearby dates
        
    Returns:
        JSON string with matching events
    """
    # Parse JSON inputs
    try:
        timeline_lookup = json.loads(timeline_lookup_json)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for timeline_lookup"})
    
    # Parse search_nearby
    search_nearby_bool = search_nearby.lower() == "true"
    
    # Original logic from here...
    matching_events = []
    
    # Try exact date match first
    if date_str in timeline_lookup:
        matching_events.extend(timeline_lookup[date_str])
    
    # Check Background Information for undated items
    if "Background Information" in timeline_lookup:
        matching_events.extend(timeline_lookup["Background Information"])
    
    # Search nearby dates if requested
    if search_nearby_bool and not matching_events:
        try:
            target_date = datetime.strptime(date_str, "%m/%d/%Y")
            for days_offset in [-1, 1, -2, 2, -3, 3]:
                nearby_date = target_date + timedelta(days=days_offset)
                nearby_date_str = nearby_date.strftime("%m/%d/%Y")
                if nearby_date_str in timeline_lookup:
                    matching_events.extend(timeline_lookup[nearby_date_str])
        except:
            pass
    
    return json.dumps({
        "matching_events": matching_events,
        "total_matches": len(matching_events),
        "searched_nearby": search_nearby_bool
    })


def get_source_info(events_json: str) -> str:  # Changed from List[Dict[str, Any]]
    """
    Extract combined source text and metadata from events.
    
    FIXED: Accept JSON string instead of Python list.
    
    Args:
        events_json: JSON string of timeline events
        
    Returns:
        JSON string with source information
    """
    # Parse JSON input
    try:
        events = json.loads(events_json)
        if not isinstance(events, list):
            events = [events]
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for events"})
    
    # Original logic from here...
    source_texts = []
    actual_sources = set()
    actual_pages = set()
    
    for event in events:
        source_texts.append(event.get("summary", ""))
        actual_sources.update(event.get("source_documents", []))
        actual_pages.update(event.get("source_pages", []))
    
    combined_source = " ".join(source_texts)
    
    return json.dumps({
        "combined_source": combined_source,
        "source_documents": list(actual_sources),
        "source_pages": list(actual_pages)
    })


def search_for_missing_demographic(
    demo_type: str,
    source_text: str
) -> str:
    """
    Search for a demographic that wasn't initially found.
    
    Args:
        demo_type: Type of demographic to search for (age, gender, date_of_birth)
        source_text: Text to search in
        
    Returns:
        JSON string with search request
    """
    search_patterns = {
        "age": "- Age: '58 year old', 'age 45', '58yo', 'patient is 67'",
        "gender": "- Gender: 'male', 'female', 'man', 'woman', 'he/him', 'she/her'",
        "date_of_birth": "- DOB: 'DOB:', 'Date of birth:', 'Born:', birth date"
    }
    
    pattern = search_patterns.get(demo_type, "")
    
    request = {
        "action": "search_missing_demographic",
        "demo_type": demo_type,
        "source_text": source_text[:3000],  # Limit for context
        "search_pattern": pattern,
        "instructions": f"""Search for {demo_type} information that may have been missed in this medical record.
        
        SEARCH FOR {demo_type.upper()}:
        - Look for explicit mentions of patient {demo_type}
        - Check consultation notes and patient presentations
        - Find information in provider assessments
        - Look for demographic information in any clinical context
        
        SEARCH PATTERNS:
        {pattern}
        
        Return found value if present, otherwise null."""
    }
    
    return json.dumps(request)


def create_verification_summary(verification_results_json: str) -> str:  # Changed from Dict[str, Any]
    """
    Create a summary of all verification results.
    
    FIXED: Accept JSON string instead of Python dict.
    
    Args:
        verification_results_json: JSON string of all verification results
        
    Returns:
        JSON string with verification summary
    """
    # Parse JSON input
    try:
        verification_results = json.loads(verification_results_json)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for verification_results"})
    
    # Original logic from here...
    summary = {
        "action": "create_summary",
        "total_items_verified": 0,
        "total_corrections": 0,
        "verification_breakdown": {}
    }
    
    # Count diagnoses
    if "diagnoses" in verification_results:
        diag_stats = verification_results.get("diagnosis_stats", {})
        summary["verification_breakdown"]["diagnoses"] = {
            "total": diag_stats.get("total_diagnoses", 0),
            "corrected": diag_stats.get("diagnosis_corrections", 0),
            "staging_added": diag_stats.get("staging_corrections", 0)
        }
        summary["total_items_verified"] += diag_stats.get("total_diagnoses", 0)
        summary["total_corrections"] += diag_stats.get("diagnosis_corrections", 0)
    
    # Count treatments
    if "treatments" in verification_results:
        treat_stats = verification_results.get("treatment_stats", {})
        summary["verification_breakdown"]["treatments"] = {
            "total": treat_stats.get("total_treatments", 0),
            "corrected": treat_stats.get("treatment_corrections", 0)
        }
        summary["total_items_verified"] += treat_stats.get("total_treatments", 0)
        summary["total_corrections"] += treat_stats.get("treatment_corrections", 0)
    
    # Count complications
    if "complications" in verification_results:
        comp_stats = verification_results.get("complication_stats", {})
        summary["verification_breakdown"]["complications"] = {
            "total": comp_stats.get("total_complications", 0),
            "corrected": comp_stats.get("complications_corrections", 0)
        }
        summary["total_items_verified"] += comp_stats.get("total_complications", 0)
        summary["total_corrections"] += comp_stats.get("complications_corrections", 0)
    
    # Count response metrics
    if "response_metrics" in verification_results:
        resp_stats = verification_results.get("response_metrics_stats", {})
        summary["verification_breakdown"]["response_metrics"] = {
            "total": resp_stats.get("total_response_metrics", 0),
            "corrected": resp_stats.get("response_metrics_corrections", 0)
        }
        summary["total_items_verified"] += resp_stats.get("total_response_metrics", 0)
        summary["total_corrections"] += resp_stats.get("response_metrics_corrections", 0)
    
    # Count demographics
    if "demographics" in verification_results:
        demo_stats = verification_results.get("demographics_stats", {})
        summary["verification_breakdown"]["demographics"] = {
            "found": demo_stats.get("demographics_found", 0),
            "corrected": demo_stats.get("demographics_corrected", 0)
        }
        summary["total_items_verified"] += 3  # age, gender, dob
        summary["total_corrections"] += demo_stats.get("demographics_corrected", 0)
    
    # Headline verification
    if "headline_corrected" in verification_results:
        summary["verification_breakdown"]["headline"] = {
            "corrected": verification_results["headline_corrected"]
        }
        summary["total_items_verified"] += 1
        if verification_results["headline_corrected"]:
            summary["total_corrections"] += 1
    
    return json.dumps(summary)


# Internal helper functions (not exposed as tools) - unchanged from original
def create_timeline_lookup_internal(timeline_events):
    """Internal version for use within functions."""
    timeline_lookup = {}
    for event in timeline_events:
        date = event.get("date", "")
        if date not in timeline_lookup:
            timeline_lookup[date] = []
        timeline_lookup[date].append(event)
    return timeline_lookup


def find_matching_events_internal(date_str, timeline_lookup, search_nearby=True):
    """Internal version for use within functions."""
    matching_events = []
    
    # Try exact date match first
    if date_str in timeline_lookup:
        matching_events.extend(timeline_lookup[date_str])
    
    # Check Background Information for undated items
    if "Background Information" in timeline_lookup:
        matching_events.extend(timeline_lookup["Background Information"])
    
    # Search nearby dates if requested
    if search_nearby and not matching_events:
        try:
            target_date = datetime.strptime(date_str, "%m/%d/%Y")
            for days_offset in [-1, 1, -2, 2, -3, 3]:
                nearby_date = target_date + timedelta(days=days_offset)
                nearby_date_str = nearby_date.strftime("%m/%d/%Y")
                if nearby_date_str in timeline_lookup:
                    matching_events.extend(timeline_lookup[nearby_date_str])
        except:
            pass
    
    return matching_events


def get_source_info_internal(events):
    """Internal version for use within functions."""
    source_texts = []
    actual_sources = set()
    actual_pages = set()
    
    for event in events:
        source_texts.append(event.get("summary", ""))
        actual_sources.update(event.get("source_documents", []))
        actual_pages.update(event.get("source_pages", []))
    
    combined_source = " ".join(source_texts)
    return combined_source, actual_sources, actual_pages


# Create FunctionTool instances for Google ADK
# All functions now have simple signatures
verify_diagnoses_tool = FunctionTool(func=verify_diagnoses)
verify_treatments_tool = FunctionTool(func=verify_treatments)
verify_complications_tool = FunctionTool(func=verify_complications)
verify_response_metrics_tool = FunctionTool(func=verify_response_metrics)
verify_demographics_tool = FunctionTool(func=verify_demographics)
verify_headline_tool = FunctionTool(func=verify_patient_headline)
create_timeline_lookup_tool = FunctionTool(func=create_timeline_lookup)
find_matching_events_tool = FunctionTool(func=find_matching_events)
get_source_info_tool = FunctionTool(func=get_source_info)
search_demographic_tool = FunctionTool(func=search_for_missing_demographic)
create_summary_tool = FunctionTool(func=create_verification_summary)

# Export all tools with fixed signatures
UNIFIED_VERIFIER_TOOLS_FIXED = [
    verify_diagnoses_tool,
    verify_treatments_tool,
    verify_complications_tool,
    verify_response_metrics_tool,
    verify_demographics_tool,
    verify_headline_tool,
    create_timeline_lookup_tool,
    find_matching_events_tool,
    get_source_info_tool,
    search_demographic_tool,
    create_summary_tool
]