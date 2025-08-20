"""
Grep tools for pattern searching with LLM error handling.
Compatible with Google ADK - all parameters are required.
All functions now require all parameters to be explicitly provided.
"""
import json
import re
import os
from typing import Dict, List, Any, Optional
from google.adk.tools import FunctionTool
import logging

logger = logging.getLogger(__name__)


def search_medical_patterns(
    file_path: str,
    patterns_json: str,  # Changed from List[str] to JSON string
    case_sensitive: str,  # Changed to string and removed default
    max_matches: str,  # Changed to string and removed default
    context_lines: str,  # Changed to string and removed default
    file_content: str  # Removed Optional and default
) -> str:
    """
    Search for multiple regex patterns in a medical document.
    
    Args:
        file_path: Path to the document to search
        patterns_json: JSON string containing list of regex patterns to search for
        case_sensitive: Whether search is case sensitive as string ("true"/"false")
        max_matches: Maximum matches per pattern as string (use "50" for standard)
        context_lines: Lines of context before/after match as string (use "3" for standard)
        file_content: Document content as string (use empty string to read from file_path)
        
    Returns:
        JSON string with search results and any errors
    """
    # Parse JSON and handle defaults
    try:
        patterns = json.loads(patterns_json) if patterns_json else []
        if not isinstance(patterns, list):
            patterns = []
    except (json.JSONDecodeError, TypeError):
        patterns = []
    
    # Convert string parameters to appropriate types
    try:
        case_sensitive = case_sensitive.lower() == "true"
    except (AttributeError, TypeError):
        case_sensitive = False
    
    try:
        max_matches = int(max_matches)
    except (ValueError, TypeError):
        max_matches = 50
    
    try:
        context_lines = int(context_lines)
    except (ValueError, TypeError):
        context_lines = 3
    
    # Handle file_content parameter
    use_file_content = file_content and file_content.strip()
    
    results = {
        "file_path": file_path,
        "search_results": [],
        "errors": [],
        "summary": {
            "total_patterns": len(patterns),
            "successful_searches": 0,
            "total_matches": 0
        }
    }
    
    # Get content either from parameter or file
    full_content = None
    if use_file_content:
        # Use provided content directly
        full_content = file_content
        lines = file_content.splitlines(keepends=True)
    else:
        # Read from file system
        if not os.path.exists(file_path):
            results["errors"].append({
                "type": "file_not_found",
                "message": f"File not found: {file_path}",
                "severity": "critical"
            })
            return json.dumps(results)
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                full_content = f.read()
                lines = full_content.splitlines(keepends=True)
        except Exception as e:
            results["errors"].append({
                "type": "file_read_error",
                "message": f"Error reading file: {str(e)}",
                "severity": "critical"
            })
            return json.dumps(results)
    
    # Check if this is a single-line document
    is_single_line = len(lines) <= 3 and any(len(line) > 1000 for line in lines)
    
    # Search each pattern
    for pattern in patterns:
        pattern_result = {
            "pattern": pattern,
            "matches": [],
            "error": None
        }
        
        try:
            # Handle case sensitivity and (?i) prefix
            flags = 0 if case_sensitive else re.IGNORECASE
            clean_pattern = pattern
            
            if pattern.startswith("(?i)"):
                clean_pattern = pattern[4:]
                flags = re.IGNORECASE
            
            # Compile regex
            regex = re.compile(clean_pattern, flags)
            
            # Search through lines
            match_count = 0
            for i, line in enumerate(lines):
                if match_count >= max_matches:
                    break
                    
                matches = list(regex.finditer(line))
                for match in matches:
                    if match_count >= max_matches:
                        break
                        
                    # Get context
                    context_start = max(0, i - context_lines)
                    context_end = min(len(lines), i + context_lines + 1)
                    context = lines[context_start:context_end]
                    
                    match_info = {
                        "line_number": i + 1,
                        "line_text": line.strip(),
                        "match_text": match.group(),
                        "match_start": match.start(),
                        "match_end": match.end(),
                        "context": [l.strip() for l in context],
                        "context_start_line": context_start + 1
                    }
                    
                    # Add character position for single-line documents
                    if is_single_line and full_content:
                        # Calculate absolute character position in document
                        char_pos = sum(len(lines[j]) for j in range(i)) + match.start()
                        match_info["match_position"] = char_pos
                        match_info["single_line_doc"] = True
                    
                    pattern_result["matches"].append(match_info)
                    match_count += 1
            
            results["summary"]["successful_searches"] += 1
            results["summary"]["total_matches"] += len(pattern_result["matches"])
            
        except re.error as e:
            pattern_result["error"] = {
                "type": "regex_error",
                "message": f"Invalid regex pattern: {str(e)}",
                "pattern": pattern
            }
            results["errors"].append(pattern_result["error"])
        except Exception as e:
            pattern_result["error"] = {
                "type": "search_error",
                "message": f"Error searching pattern: {str(e)}",
                "pattern": pattern
            }
            results["errors"].append(pattern_result["error"])
        
        results["search_results"].append(pattern_result)
    
    return json.dumps(results)


def validate_and_fix_patterns(patterns_json: str) -> str:  # Changed from List[str] to JSON string
    """
    Validate regex patterns and suggest fixes using LLM guidance.
    
    Args:
        patterns_json: JSON string containing list of patterns to validate
        
    Returns:
        JSON string with validation results and fix suggestions
    """
    # Parse JSON string
    try:
        patterns = json.loads(patterns_json) if patterns_json else []
        if not isinstance(patterns, list):
            patterns = []
    except (json.JSONDecodeError, TypeError):
        patterns = []
    
    validation_results = {
        "patterns": [],
        "summary": {
            "total": len(patterns),
            "valid": 0,
            "invalid": 0,
            "fixed": 0
        }
    }
    
    for pattern in patterns:
        result = {
            "original": pattern,
            "valid": False,
            "error": None,
            "suggested_fix": None,
            "fix_explanation": None
        }
        
        try:
            # Try to compile the pattern
            re.compile(pattern)
            result["valid"] = True
            validation_results["summary"]["valid"] += 1
        except re.error as e:
            result["error"] = str(e)
            validation_results["summary"]["invalid"] += 1
            
            # Suggest common fixes
            if "unbalanced parenthesis" in str(e).lower():
                result["suggested_fix"] = pattern.replace("(", r"\(").replace(")", r"\)")
                result["fix_explanation"] = "Escaped parentheses that should be literal"
            elif "bad escape" in str(e).lower():
                result["suggested_fix"] = pattern.replace("\\", "\\\\")
                result["fix_explanation"] = "Fixed escape sequences"
            elif "nothing to repeat" in str(e).lower():
                result["suggested_fix"] = re.escape(pattern)
                result["fix_explanation"] = "Escaped special characters"
            
            # Verify the fix works
            if result["suggested_fix"]:
                try:
                    re.compile(result["suggested_fix"])
                    validation_results["summary"]["fixed"] += 1
                except:
                    result["suggested_fix"] = None
                    result["fix_explanation"] = "Could not automatically fix pattern"
        
        validation_results["patterns"].append(result)
    
    return json.dumps(validation_results)


def search_with_error_recovery(
    file_path: str,
    pattern: str,
    fallback_patterns_json: str,  # Changed to required JSON string parameter
    file_content: str  # Removed Optional and default
) -> str:
    """
    Search with automatic error recovery and fallback patterns.
    
    Args:
        file_path: Document to search
        pattern: Primary pattern to search
        fallback_patterns_json: JSON string with alternative patterns if primary fails (use "[]" for none)
        file_content: Document content as string (use empty string to read from file_path)
        
    Returns:
        JSON string with search results
    """
    # Parse JSON and handle defaults
    try:
        fallback_patterns = json.loads(fallback_patterns_json) if fallback_patterns_json else []
        if not isinstance(fallback_patterns, list):
            fallback_patterns = []
    except (json.JSONDecodeError, TypeError):
        fallback_patterns = []
    
    # Handle file_content parameter
    use_file_content = file_content and file_content.strip()
    
    all_patterns = [pattern] + fallback_patterns
    
    for i, current_pattern in enumerate(all_patterns):
        try:
            # Try searching with current pattern
            results = json.loads(search_medical_patterns(
                file_path=file_path,
                patterns_json=json.dumps([current_pattern]),
                case_sensitive="false",
                max_matches="100",
                context_lines="3",
                file_content=file_content if use_file_content else ""
            ))
            
            # Check if search was successful
            if results["summary"]["successful_searches"] > 0:
                results["recovery_info"] = {
                    "pattern_used": current_pattern,
                    "attempt_number": i + 1,
                    "total_attempts": len(all_patterns)
                }
                return json.dumps(results)
                
        except Exception as e:
            logger.error(f"Error with pattern {current_pattern}: {str(e)}")
            continue
    
    # All patterns failed
    return json.dumps({
        "error": "All patterns failed",
        "attempted_patterns": all_patterns,
        "file_path": file_path
    })


def analyze_search_performance(search_results_json: str) -> str:  # Changed from Dict to JSON string
    """
    Analyze search results to identify performance issues and suggest improvements.
    
    Args:
        search_results_json: JSON string containing results from previous search
        
    Returns:
        JSON string with performance analysis
    """
    # Parse JSON string
    try:
        search_results = json.loads(search_results_json) if search_results_json else {}
        if not isinstance(search_results, dict):
            search_results = {}
    except (json.JSONDecodeError, TypeError):
        search_results = {}
    
    analysis = {
        "performance_metrics": {},
        "issues_found": [],
        "recommendations": []
    }
    
    # Analyze results
    total_patterns = search_results.get("summary", {}).get("total_patterns", 0)
    successful = search_results.get("summary", {}).get("successful_searches", 0)
    total_matches = search_results.get("summary", {}).get("total_matches", 0)
    errors = search_results.get("errors", [])
    
    # Calculate metrics
    analysis["performance_metrics"] = {
        "success_rate": (successful / total_patterns * 100) if total_patterns > 0 else 0,
        "average_matches_per_pattern": total_matches / successful if successful > 0 else 0,
        "error_count": len(errors)
    }
    
    # Identify issues
    if len(errors) > 0:
        analysis["issues_found"].append({
            "type": "pattern_errors",
            "count": len(errors),
            "severity": "high"
        })
        analysis["recommendations"].append(
            "Review and fix regex patterns with errors"
        )
    
    if total_matches == 0 and successful > 0:
        analysis["issues_found"].append({
            "type": "no_matches",
            "severity": "medium"
        })
        analysis["recommendations"].append(
            "Consider broadening search patterns or checking document content"
        )
    
    if total_matches > 1000:
        analysis["issues_found"].append({
            "type": "too_many_matches",
            "count": total_matches,
            "severity": "low"
        })
        analysis["recommendations"].append(
            "Consider more specific patterns to reduce match count"
        )
    
    # Pattern-specific analysis
    for result in search_results.get("search_results", []):
        pattern = result.get("pattern", "")
        matches = result.get("matches", [])
        
        if len(matches) > 100:
            analysis["recommendations"].append(
                f"Pattern '{pattern}' has {len(matches)} matches - consider making it more specific"
            )
    
    return json.dumps(analysis)


# Create FunctionTool instances for Google ADK
search_patterns_tool = FunctionTool(func=search_medical_patterns)
validate_patterns_tool = FunctionTool(func=validate_and_fix_patterns)
search_with_recovery_tool = FunctionTool(func=search_with_error_recovery)
analyze_performance_tool = FunctionTool(func=analyze_search_performance)

# Export all tools
GREP_TOOLS = [
    search_patterns_tool,
    validate_patterns_tool,
    search_with_recovery_tool,
    analyze_performance_tool
]