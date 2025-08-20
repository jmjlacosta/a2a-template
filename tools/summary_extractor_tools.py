"""
Summary extraction tools with FIXED signatures for Google ADK compatibility.
GITHUB ISSUE: Google ADK Tool Signature Fix

Problem: Google ADK cannot parse List[Dict[str, Any]], Dict[str, Any], Optional types
Solution: Use JSON strings for all complex data structures

Changes from summary_extractor_tools.py:
1. All List/Dict parameters changed to str (JSON)
2. Optional parameters made required or converted to str
3. Added JSON parsing with error handling
4. Preserved all original logic
"""
import json
import re
from google.adk.tools import FunctionTool


def extract_from_reconciled_groups(
    reconciled_groups_json: str,  # Changed from List[Dict[str, Any]]
    page_to_chunk_mapping_json: str  # Changed from Optional[Dict[int, Dict[str, Any]]] with default
) -> str:
    """
    Extract facts from reconciled encounter groups.
    
    FIXED: Accept JSON strings instead of Python list/dict.
    
    Args:
        reconciled_groups_json: JSON string of reconciled encounter groups
        page_to_chunk_mapping_json: JSON string of page to chunk mapping or "null"
        
    Returns:
        JSON string with extraction request
    """
    # Parse JSON inputs
    try:
        reconciled_groups = json.loads(reconciled_groups_json)
        if not isinstance(reconciled_groups, list):
            reconciled_groups = [reconciled_groups] if reconciled_groups else []
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for reconciled_groups"})
    
    # Parse optional mapping
    page_to_chunk_mapping = None
    if page_to_chunk_mapping_json and page_to_chunk_mapping_json.lower() != "null":
        try:
            page_to_chunk_mapping = json.loads(page_to_chunk_mapping_json)
        except (json.JSONDecodeError, TypeError):
            page_to_chunk_mapping = None
    
    # Original logic from here...
    # Process reconciled groups for extraction
    extraction_requests = []
    
    for group in reconciled_groups:
        encounter_date = group.get("encounter_date", "")
        reconciled_facts = group.get("reconciled_facts", [])
        
        # Filter out carry-forward facts
        unique_facts = []
        for fact in reconciled_facts:
            # Skip carry-forward facts to avoid duplicates
            if fact.get("is_carry_forward") and fact.get("provenance") == "Previously Reported":
                continue
            
            unique_facts.append({
                "content": fact.get("content", ""),
                "status": fact.get("status", ""),
                "provenance": fact.get("provenance", ""),
                "confidence": fact.get("confidence", 0.9),
                "source_pages": fact.get("source_pages", []),
                "source_documents": fact.get("source_documents", [])
            })
        
        if unique_facts:
            extraction_requests.append({
                "encounter_date": encounter_date,
                "encounter_type": group.get("encounter_type", "unknown"),
                "facts": unique_facts,
                "fact_count": len(unique_facts)
            })
    
    request = {
        "action": "extract_from_reconciled",
        "total_groups": len(reconciled_groups),
        "extraction_requests": extraction_requests,
        "instructions": """Process these reconciled facts for final extraction.

For each fact:
1. Preserve the exact clinical content
2. Maintain the encounter date
3. Determine medical specialty based on content
4. Include status and provenance metadata
5. Skip any previously reported (carry-forward) facts

Return extracted facts organized by encounter with appropriate metadata."""
    }
    
    return json.dumps(request)


def extract_events_by_date(
    chunk_content: str,
    page_number: str,  # Changed from int to str
    source_document: str
) -> str:
    """
    Extract all dated clinical events from a document chunk.
    
    FIXED: Accept page_number as string.
    
    Args:
        chunk_content: The text content of the chunk
        page_number: String page number of the chunk
        source_document: Source document name
        
    Returns:
        JSON string with extraction request
    """
    # Parse page number
    try:
        page_num = int(page_number)
    except (ValueError, TypeError):
        page_num = 0
    
    # Original logic from here...
    # Clean content
    clean_content = re.sub(r'Case #\d+.*?To Top.*?\n', '', chunk_content, flags=re.IGNORECASE)
    
    request = {
        "action": "extract_events_by_date",
        "page_number": page_num,
        "source_document": source_document,
        "content": clean_content,
        "instructions": f"""You are an expert clinical data extractor. Your task is to scan the provided page of a medical record and extract all dated clinical events that would be relevant for medical decision-making and patient care.

        **Text from Page {page_num} of document '{source_document}':**
        ---
        {clean_content}
        ---

        **CRITICAL RULES FOR EXTRACTION:**

        1.  **IGNORE DEMOGRAPHIC DATES:** Ignore dates labeled 'Date of Birth' or 'DOB'.
        2.  **USE EVENT DATES:** Use dates labeled 'Exam Date', 'Report Date', 'Date of Service', 'Collection Date', or dates next to a procedure.
        3.  **BE COMPREHENSIVE:** Extract EVERY distinct finding or result, even if they seem similar. Create separate events for each distinct piece of information.
        4.  **EXHAUSTIVE EXTRACTION:** Extract ALL medically relevant events including:
                - EVERY diagnostic test result and finding
                - EVERY measurement, value, or quantitative result
                - ALL test interpretations and conclusions
                - ALL treatment decisions and interventions
                - ALL clinical assessments and evaluations
                - ALL disease status evaluations
                - ALL consultant recommendations and referrals
                - ALL significant clinical changes or developments
                - ALL therapeutic procedures and their outcomes
                - ALL laboratory results with clinical significance
                - ALL care coordination and planning
                - ALL biomarker or molecular testing results
                - ALL staging or classification information
                - ALL follow-up recommendations and care plans
                - ALL confirmation or repeat testing results
                - ALL diagnostic clarifications or updates

        **CLINICAL RELEVANCE CRITERIA:**
        - Information that affects diagnosis, staging, or treatment decisions
        - ALL test results showing disease characteristics or extent
        - ALL interventions that impact patient care
        - ALL findings that require follow-up or monitoring
        - ALL recommendations from healthcare providers
        - ALL significant changes in patient condition
        - ALL biomarker or molecular testing results
        - ALL receptor status or genetic testing information
        - ALL staging or disease extent assessments
        - ANY information that would influence clinical management

        **EXTRACTION PRINCIPLES:**
        - Extract EVERY piece of medically relevant information - be exhaustive, not selective
        - If a single report contains multiple findings, create separate events for EACH distinct finding
        - Include ALL test results, even if they confirm previous findings
        - Capture ALL diagnostic details, including measurements, grades, staging components, receptor status
        - Do not consolidate or combine findings - extract each separately for maximum granularity
        - Extract complete pathology findings including ALL markers tested and ALL results
        - Include ALL treatment recommendations, even preliminary discussions
        - Capture ALL clinical observations and assessments, including repeat evaluations
        - Extract ALL imaging findings, including measurements and specific anatomical details
        - Include follow-up results that confirm, modify, or add to previous findings
        - Do not assume anything is redundant - extract everything for completeness

        **Output Format (CRITICAL):**
        Respond with a JSON list of objects. Each object represents a SINGLE DATE found on the page and must contain:
        - `date_str`: The date you found, normalized to `YYYY-MM-DD`.
        - `events`: A list of strings, where each string is a **brief, one-sentence summary** of a single clinically relevant event from that day.
        - `specialty`: The single most relevant medical specialty for the events of that day (e.g., "Radiology", "Pathology", "Medical Oncology", "Surgery", "Internal Medicine", "Cardiology").

        **Example Response:**
        [
          {{
            "date_str": "2024-09-12",
            "events": [
              "Primary diagnostic procedure performed on target tissue.",
              "Tissue measurements and dimensions documented.",
              "First biomarker test result reported.",
              "Second biomarker test result reported.", 
              "Third biomarker test result reported.",
              "Proliferation marker level determined.",
              "Regional tissue sampling showed specific findings.",
              "Diagnostic classification assigned.",
              "Clinical assessment recommendation provided."
            ],
            "specialty": "Pathology"
          }},
          {{
            "date_str": "2024-09-15",
            "events": [
              "Imaging showed primary lesion with specific measurements.",
              "Second area of concern identified with measurements.",
              "Regional tissue shows abnormal characteristics.",
              "Assessment of local extension completed.",
              "Additional diagnostic procedures recommended."
            ],
            "specialty": "Radiology"
          }}
        ]"""
    }
    
    return json.dumps(request)


def determine_specialty(content: str) -> str:
    """
    Determine medical specialty based on content analysis.
    
    Args:
        content: Clinical content to analyze
        
    Returns:
        JSON string with specialty determination
    """
    # Original logic unchanged - no complex types in signature
    content_lower = content.lower()
    
    # Specialty keywords mapping
    specialty_keywords = {
        "Radiology": ["ct", "mri", "scan", "imaging", "contrast", "enhancement", "lesion", "mass"],
        "Pathology": ["biopsy", "specimen", "histology", "grade", "differentiated", "necrosis", "margins"],
        "Medical Oncology": ["chemotherapy", "folfox", "cisplatin", "carboplatin", "cycles", "regimen"],
        "Surgery": ["resection", "surgery", "operative", "incision", "dissection", "anastomosis"],
        "Radiation Oncology": ["radiation", "radiotherapy", "gray", "fractions", "boost", "imrt"],
        "Laboratory": ["lab", "blood", "wbc", "hemoglobin", "platelet", "creatinine", "liver"],
        "Cardiology": ["ecg", "echo", "ejection fraction", "cardiac", "heart", "coronary"],
        "Internal Medicine": ["admission", "discharge", "consultation", "physical exam", "review"]
    }
    
    # Score each specialty
    specialty_scores = {}
    for specialty, keywords in specialty_keywords.items():
        score = sum(1 for keyword in keywords if keyword in content_lower)
        if score > 0:
            specialty_scores[specialty] = score
    
    # Determine the best match
    if specialty_scores:
        best_specialty = max(specialty_scores.items(), key=lambda x: x[1])[0]
        confidence = specialty_scores[best_specialty] / len(specialty_keywords[best_specialty])
    else:
        best_specialty = "Internal Medicine"
        confidence = 0.5
    
    result = {
        "action": "determine_specialty",
        "content_preview": content[:200],
        "specialty_scores": specialty_scores,
        "selected_specialty": best_specialty,
        "confidence": confidence
    }
    
    return json.dumps(result)


def process_extraction_batch(
    chunks_json: str,  # Changed from List[Dict[str, Any]]
    batch_size: str  # Changed from int with default to str
) -> str:
    """
    Process multiple chunks in a batch for efficient extraction.
    
    FIXED: Accept JSON string for chunks, batch_size as string.
    
    Args:
        chunks_json: JSON string of document chunks to process
        batch_size: String number of chunks to process together
        
    Returns:
        JSON string with batch processing request
    """
    # Parse JSON inputs
    try:
        chunks = json.loads(chunks_json)
        if not isinstance(chunks, list):
            chunks = [chunks] if chunks else []
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for chunks"})
    
    # Parse batch_size
    try:
        batch_size_int = int(batch_size)
    except (ValueError, TypeError):
        batch_size_int = 5  # Default
    
    # Original logic from here...
    # Prepare chunks for batch processing
    chunk_summaries = []
    for i, chunk in enumerate(chunks[:batch_size_int]):
        chunk_summaries.append({
            "index": i,
            "page_number": chunk.get("page_number", 0),
            "source_document": chunk.get("source_document", "Unknown"),
            "content_length": len(chunk.get("content", "")),
            "content_preview": chunk.get("content", "")[:500]
        })
    
    request = {
        "action": "process_batch",
        "batch_size": len(chunk_summaries),
        "total_chunks": len(chunks),
        "chunk_summaries": chunk_summaries,
        "instructions": """Process this batch of document chunks for fact extraction.

For each chunk:
1. Extract all dated clinical events
2. Categorize by medical specialty
3. Be exhaustive and granular
4. Create separate events for each finding

Return a consolidated list of all extracted facts from the batch."""
    }
    
    return json.dumps(request)


def validate_extracted_facts(extracted_facts_json: str) -> str:  # Changed from List[Dict[str, Any]]
    """
    Validate the quality and completeness of extracted facts.
    
    FIXED: Accept JSON string instead of Python list.
    
    Args:
        extracted_facts_json: JSON string of extracted facts to validate
        
    Returns:
        JSON string with validation results
    """
    # Parse JSON input
    try:
        extracted_facts = json.loads(extracted_facts_json)
        if not isinstance(extracted_facts, list):
            extracted_facts = [extracted_facts] if extracted_facts else []
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input for extracted_facts"})
    
    # Original logic from here...
    # Analyze extracted facts
    total_facts = len(extracted_facts)
    facts_by_date = {}
    facts_by_specialty = {}
    
    for fact in extracted_facts:
        # Group by date
        date_str = fact.get("date_str", "Unknown")
        if date_str not in facts_by_date:
            facts_by_date[date_str] = 0
        facts_by_date[date_str] += 1
        
        # Group by specialty
        specialty = fact.get("specialty", "Unknown")
        if specialty not in facts_by_specialty:
            facts_by_specialty[specialty] = 0
        facts_by_specialty[specialty] += 1
    
    # Check for potential issues
    issues = []
    
    # Check for facts without dates
    if "Unknown" in facts_by_date:
        issues.append({
            "type": "missing_dates",
            "severity": "warning",
            "details": f"{facts_by_date['Unknown']} facts have unknown dates"
        })
    
    # Check for unbalanced specialty distribution
    if facts_by_specialty and total_facts > 0:
        max_specialty_count = max(facts_by_specialty.values())
        if max_specialty_count / total_facts > 0.8:
            dominant_specialty = max(facts_by_specialty.items(), key=lambda x: x[1])[0]
            issues.append({
                "type": "specialty_imbalance",
                "severity": "info",
                "details": f"{dominant_specialty} accounts for >80% of facts"
            })
    
    validation = {
        "action": "validation_results",
        "total_facts": total_facts,
        "unique_dates": len(facts_by_date),
        "facts_by_date": facts_by_date,
        "facts_by_specialty": facts_by_specialty,
        "issues": issues,
        "validation_passed": len([i for i in issues if i["severity"] == "error"]) == 0
    }
    
    return json.dumps(validation)


# Create FunctionTool instances for Google ADK
# All functions now have simple signatures
extract_reconciled_tool = FunctionTool(func=extract_from_reconciled_groups)
extract_events_tool = FunctionTool(func=extract_events_by_date)
determine_specialty_tool = FunctionTool(func=determine_specialty)
batch_process_tool = FunctionTool(func=process_extraction_batch)
validate_facts_tool = FunctionTool(func=validate_extracted_facts)

# Export all tools with fixed signatures
SUMMARY_EXTRACTOR_TOOLS_FIXED = [
    extract_reconciled_tool,
    extract_events_tool,
    determine_specialty_tool,
    batch_process_tool,
    validate_facts_tool
]